#!/usr/bin/env python3
from __future__ import division, print_function

import threading
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import copy

from api_service.db import metricdb
from config import get_config
from logger import get_logger

from .bayesian_optimizer import get_candidate
from .util import (compute_cost, decode_nodetype, encode_nodetype,
                   get_all_nodetypes, get_budget, get_feature_bounds,
                   get_app_info, get_price, get_slo_type, get_slo_value)

config = get_config()
min_samples = int(config.get("BAYESIAN_OPTIMIZER_POOL", "MIN_SAMPLES"))
max_samples = int(config.get("BAYESIAN_OPTIMIZER_POOL", "MAX_SAMPLES"))
min_improvement = float(config.get("BAYESIAN_OPTIMIZER_POOL", "MIN_IMPROVEMENT"))
sizing_collection = config.get("ANALYZER", "SIZING_COLLECTION")

pd.set_option('display.width', 1000)  # widen the display
np.set_printoptions(precision=3)
logger = get_logger(__name__, log_level=(
    "BAYESIAN_OPTIMIZER_POOL", "LOGLEVEL"))


class BayesianOptimizerPool():
    """ This class manages the training samples for each sizing session,
        dispatches jobs to the worker pool, and tracks the status of each job.
    """
    __singleton_lock = threading.Lock()
    __singleton_instance = None

    @classmethod
    def instance(cls):
        """ The singleton instance of BayesianOptimizerPool """
        if not cls.__singleton_instance:
            with cls.__singleton_lock:
                if not cls.__singleton_instance:
                    cls.__singleton_instance = cls()
        return cls.__singleton_instance

    def __init__(self):
        # Map for sharing data samples throughout each sizing session with session_id
        self.sample_map = {}
        # Map for storing the future objects for python concurrent tasks
        self.future_map = {}
        # Pool of worker processes for handling jobs
        self.worker_pool = ProcessPoolExecutor(max_workers=16)
        # Map for optimal perf_over_cost value from all samples evaluted
        self.optimal_poc = {}
        # Map for storing all the avaialbe nodetypes
        self.available_nodetype_map = {}

    def get_candidates(self, session_id, request_body, **kwargs):
        """ The public method to asychronously start the jobs for generating candidates.
        Args:
            session_id(str): unique key to identify each sizing session
            request_body(dict): the request body sent from the client of the analyzer service
        """

        # Generate initial samples if the data field of request_body is empty (special case)
        if not request_body.get('data'):
            assert self.available_nodetype_map.get(session_id) is None,\
                "The data field of the request_body can only be empty at the beginning of a session"

            # create initial sizing document in the database
            app_name = request_body['appName']
            try:
                BayesianOptimizerPool.initialize_sizing_doc(session_id, app_name)
                logger.info(f"Initial sizing document created for session {session_id}")
            except Exception as e:
                return {"status": "server_error",
                        "message": "Failed to create initial sizing document: " + str(e)}

            # initialize with all available nodetype
            self.available_nodetype_map[session_id] = copy.deepcopy(
                get_all_nodetypes())  # defensive copy here
            # draw inital samples
            init_samples = BayesianOptimizerPool.generate_initial_samples()
            self.future_map[session_id] = [self.worker_pool.submit(
                encode_nodetype, i) for i in init_samples]
            return {"status": "success"}

        # Pre-process request body and remove unavailable nodetypes
        logger.debug(f"[{session_id}]Received non-empty request_body; preprocessing...")
        unavailable_nodetypes = [i['instanceType'] for i in
                                 filter(lambda d: d['qosValue'] == 0., request_body['data'])]
        self.update_available_nodetype_map(session_id, unavailable_nodetypes)

        request_body['data'] = list(
            filter(lambda d: d['qosValue'] != 0., request_body['data']))
        if not request_body['data']:
            logger.debug(f"[{session_id}]All nodetypes suggested last time are unavailable; regenerating...")
            random_samples = BayesianOptimizerPool.generate_initial_samples()
            self.future_map[session_id] = [self.worker_pool.submit(
                encode_nodetype, i) for i in random_samples]
            return {"status": "success"}

        # Update sample map and check termination
        new_samples = BayesianOptimizerPool.create_sample_dataframe(session_id, request_body)
        self.update_available_nodetype_map(session_id, new_samples['nodetype'])
        self.update_sample_map(session_id, new_samples)
        all_samples = self.sample_map.get(session_id)
        assert all_samples is not None, "sample map should not be empty"
        logger.debug(f"[{session_id}]All training samples evaluted:\n{all_samples}")

        if self.check_termination(session_id):
            recommendations = BayesianOptimizerPool.compute_recommendations(all_samples)
            logger.info(f"[{session_id}]Sizing analysis is done; final recommendations:\n{recommendations}")
            self.future_map[session_id] = [self.worker_pool.submit(
                BayesianOptimizerPool.store_final_result, session_id, recommendations)]
            return {"status": "success"}

        # Dispatch the optimizers
        training_data_list = [BayesianOptimizerPool.make_optimizer_training_data(
            self.sample_map[session_id], objective_type=o) for o in ['perf_over_cost',
                                                                     'cost_given_perf_limit',
                                                                     'perf_given_cost_limit']]
        self.future_map[session_id] = []
        for training_data in training_data_list:
            logger.debug(
                f"[{session_id}]Dispatching optimizer with training data:\n{training_data}")
            future = self.worker_pool.submit(
                get_candidate,
                training_data.feature_mat,
                training_data.objective_arr,
                get_feature_bounds(normalized=True),
                acq='cei' if training_data.has_constraint() else 'ei',
                constraint_arr=training_data.constraint_arr,
                constraint_upper=training_data.constraint_upper,
                **kwargs
            )
            self.future_map[session_id].append(future)

        return {"status": "success"}

    def get_status(self, session_id):
        """ The public method to get the state of current optimization jobs of a session.
        """
        future_list = self.future_map.get(session_id)
        if not future_list:
            return {"status": "bad_request",
                    "data": f"session_id {session_id} is not found"}

        if all([future.done() for future in future_list]):
            candidates = [future.result() for future in future_list]
            if not candidates:
                logger.info(f"[{session_id}]No more candidate suggested.")
                return {"status": "done", "data": []}
            else:
                logger.info(f"[{session_id}]New candidates suggested:\n{candidates}")
                return {"status": "done",
                        "data": self.filter_candidates(session_id, [
                            decode_nodetype(
                                c, list(self.available_nodetype_map[session_id].keys()))
                            for c in candidates if c is not None]
                        )}
        elif any([future.cancelled() for future in future_list]):
            return {"status": "server_error", "error": "task cancelled"}
        else:
            # Running or pending
            return {"status": "running"}

    def update_available_nodetype_map(self, session_id, exclude_keys):
        with self.__singleton_lock:
            assert self.available_nodetype_map.get(session_id) is not None,\
                "This method should only be called after the a session was initialized"

            for k in exclude_keys:
                self.available_nodetype_map[session_id].pop(k, None)

    def update_sample_map(self, session_id, df):
        with self.__singleton_lock:
            if self.sample_map.get(session_id) is not None:
                # check if incoming df contains duplicated nodetypes with existing sample_map
                intersection = set(df['nodetype']).intersection(
                    set(self.sample_map[session_id]['nodetype']))
                if intersection:
                    logger.warning(f"Duplicated samples were sent from the client")
                    logger.warning(f"input:\n{df}\nsample_map:\n{self.sample_map.get(session_id)}")
                    logger.warning(f"intersection: {intersection}")

            self.sample_map[session_id] = pd.concat(
                [self.sample_map.get(session_id), df])

    def check_termination(self, session_id):
        """ This method determines if the optimization process for a given session_id can terminate.
        Termination conditions:
            1. if total number of samples evaluated exceeds max_samples, or
            2. if total number of samples evaluated exceeds min_samples && incremental improvement 
                in the objective over previous runs is within min_improvement, or
            3. if available nodetype map is empty
        """
        all_samples = self.sample_map.get(session_id)
        if (all_samples is not None) and (len(all_samples) > max_samples):
            logger.info(f"[session_id]:Termination condition is met due to enough number of samples = {len(df)}")
            return True

        if not self.available_nodetype_map.get(session_id):
            logger.info(f"[session_id]:Termination condition is met due running out of available nodetypes")
            return True

        new_opt_poc = BayesianOptimizerPool.compute_optimum(all_samples)
        optimal_poc = self.optimal_poc.get(session_id)
        if (optimal_poc is None) or (len(all_samples) < min_samples) or\
                (new_opt_poc - optimal_poc >= min_improvement * optimal_poc):
            self.optimal_poc[session_id] = new_opt_poc
            return False
        else:
            logger.info(f"[session_id]:Termination condition is met due to small incremental improvement.\n\
                old_opt_poc = {optimal_poc}, new_opt_poc = {new_opt_poc}")
            return True

    def filter_candidates(self, session_id, candidate_rank_list):
        """ This method filters the recommended candidates before returning to the client
            and avoid returning duplicate result by greedily select the closest solutions as possible
        Args:
            candidate_rank_list: list of rank-ordered candidates
        Return:
            result (list): list of suggested nodetypes
        """
        # double check the candidate_rank_list does not consist of any nodetype in sample_map
        # if the samplei_map is None, BO is in initialization state
        if self.sample_map.get(session_id) is not None:
            for l in candidate_rank_list:
                for row in l:
                    nodetype = row[1]
                    assert nodetype not in self.sample_map.get(session_id)['nodetype'].values, \
                        f"{nodetype} shouldn't exist in sample map at this point"

        # Get the closest candidate greedily
        result = []
        for l in candidate_rank_list:
            for row in l:
                nodetype = row[1]
                if nodetype not in result:
                    result.append(nodetype)
                    break

        logger.debug(f"filtered candidates: {result}")
        assert len(set(result)) == len(result)
        return result

    @staticmethod
    def generate_initial_samples(init_samples=3):
        """ This method randomly select a 'instanceFamily',
            and randomly select a 'nodetype' from that family repeatly
        """
        dataframe = pd.DataFrame.from_dict(list(get_all_nodetypes().values()))
        instance_families = list(set(dataframe['instanceFamily']))
        available = list(instance_families)
        # check if there is any instance's instanceFamily field is empty string
        assert '' not in instance_families, "instanceFamily shouldn't be empty"
        result = []

        logger.debug("Generating random initial samples")
        while init_samples > 0:
            family = np.random.choice(instance_families, 1)[0]
            if family in available:
                nodetype = np.random.choice(
                    dataframe[dataframe['instanceFamily'] == family]['name'], 1)[0]
                result.append(nodetype)
                init_samples -= 1
                available.remove(family)

            # reset available when all families are visited
            if not available:
                available = list(instance_families)

        logger.debug(f"initial samples:\n{result}")
        return result

    @staticmethod
    def psudo_random_generator(all_nodetypes, sample_map, unavailable_nodetypes, num=1):
        """ Randomly draw a nodetype that does not exist in the sample_map or unavailable_nodetypes
        """
        if sample_map.get('nodetype') is not None:
            for i in sample_map.get('nodetype'):
                if i in all_nodetypes:
                    all_nodetypes.remove(i)

        for i in unavailable_nodetypes:
            if i in all_nodetypes:
                all_nodetypes.remove(i)

        return np.random.choice(all_nodetypes, num, replace=False) if all_nodetypes else None

    # @staticmethod
    # def generate_initial_samples(init_samples=3):
    #     dataframe = pd.DataFrame.from_dict(get_all_nodetypes()['data'])
    #     result = np.random.choice(dataframe['name'], init_samples)
    #     return result

    @staticmethod
    def make_optimizer_training_data(df, objective_type=None):
        """ Convert the objective and constraints such the optimizer can always:
            1. maximize objective function such that 2. constraints function < constraint
        """
        class BOTrainingData():
            """ Training data for bayesian optimizer
            """

            def __init__(self, objective_type, feature_mat, objective_arr,
                         constraint_arr=None, constraint_upper=None):
                self.objective_type = objective_type
                self.feature_mat = feature_mat
                self.objective_arr = objective_arr
                self.constraint_arr = constraint_arr
                self.constraint_upper = constraint_upper

            def __str__(self):
                result = ""
                result += f'Feature_mat:\n{self.feature_mat}\n'
                result += f'Objective_type: {self.objective_type}\n'
                result += f'Objective_arr: {self.objective_arr.values}\n'
                if self.constraint_arr is not None:
                    result += f'Constraint_arr: {self.constraint_arr.values}\n'
                if self.constraint_upper is not None:
                    result += f'Constraint_upper: {self.constraint_upper}\n'
                return result

            def has_constraint(self):
                """ See if this trainning data has constraint """
                return self.constraint_upper is not None

        implmentation = ['perf_over_cost',
                         'cost_given_perf_limit', 'perf_given_cost_limit']
        if objective_type not in implmentation:
            raise NotImplementedError(f'objective_type: {objective_type} is not implemented.')

        feature_mat = np.array(df['feature'].tolist())
        slo_type = df['slo_type'].iloc[0]
        budget = df['budget'].iloc[0]
        perf_constraint = df['slo_value'].iloc[0]
        perf_arr = df['qos_value']

        # Convert metric so we always try to maximize performance
        if slo_type == 'latency':
            perf_arr = 1. / df['qos_value']
            perf_constraint = 1. / perf_constraint
        elif slo_type == 'throughput':
            pass
        else:
            raise AssertionError(f'invalid slo type: {slo_type}')

        # Compute objectives
        perf_over_cost = (perf_arr / df['cost']
                          ).rename("performance over cost")

        if objective_type == 'perf_over_cost':
            return BOTrainingData(objective_type, feature_mat, perf_over_cost)
        elif objective_type == 'cost_given_perf_limit':
            return BOTrainingData(objective_type, feature_mat, -df['cost'], -perf_arr, -perf_constraint)
        elif objective_type == 'perf_given_cost_limit':
            return BOTrainingData(objective_type, feature_mat, perf_arr, df['cost'], budget)
        else:
            raise UserWarning("Unexpected error")

    @staticmethod
    def create_sample_dataframe(session_id, request_body):
        """ Convert request_body to dataframe of training samples.
        Args:
                request_body(dict): request body sent from workload profiler
        Returns:
                dfs(dataframe): sample data organized in dataframe
        """
        app_name = request_body['appName']
        slo_type = get_slo_type(app_name)
        assert slo_type in ['throughput', 'latency'], \
            f'slo type should be either throughput or latency, but got {slo_type}'

        dfs = []
        for data in request_body['data']:
            nodetype = data['instanceType']
            qos_value = data['qosValue']
            df = pd.DataFrame({'app_name': [app_name],
                               'qos_value': [qos_value],
                               'slo_type': [slo_type],
                               'nodetype': [nodetype],
                               'feature': [encode_nodetype(nodetype)],
                               'cost': [compute_cost(get_price(nodetype), slo_type, qos_value)],
                               'slo_value': [get_slo_value(app_name)],
                               'budget': [get_budget(app_name)]
                               })
            dfs.append(df)
        assert dfs, f'dataframe is not created\nrequest_body:\n{request_body}'

        # Store the sizing run data in the dataframes to the database
        BayesianOptimizerPool.store_sizing_run(session_id, dfs)

        return pd.concat(dfs)

    @staticmethod
    def compute_optimum(dfs):
        """ Compute the optimal perf_over_cost value among all given samples
        """
        assert dfs is not None and len(dfs) > 0

        slo_type = dfs['slo_type'].iloc[0]
        if slo_type == 'latency':
            perf_arr = 1. / dfs['qos_value']
        else:
            perf_arr = dfs['qos_value']

        perf_over_cost = perf_arr / dfs['cost']
        return np.max(perf_over_cost)

    # TODO: handle the case where no feasible solution is found for each constraint
    @staticmethod
    def compute_recommendations(dfs):
        """ Compute the final recommendations from the optimizer -
            optimal node types among all samples based on three different objective functions:
            1. MaxPerfOverCost
            2. MinCostWithPerfLimit
            3. MaxPerfWithCostLimit
            This method is called only after the analysis is completed.
        """

        recommendations = []

        perf_arr = dfs['qos_value'].values
        cost_arr = dfs['cost'].values
        nodetype_arr = dfs['nodetype'].values
        slo_type = dfs['slo_type'].iloc[0]
        budget = dfs['budget'].iloc[0]
        perf_constraint = dfs['slo_value'].iloc[0]

        # Convert qos value so we always maximize performance
        if slo_type == 'latency':
            perf_arr = 1. / perf_arr
            perf_constraint = 1. / perf_constraint
        perf_over_cost_arr = list(perf_arr / cost_arr)
        if perf_over_cost_arr:
            nodetype_best_ratio = {"nodetype": nodetype_arr[np.argmax(perf_over_cost_arr)],
                                   "objective": "MaxPerfOverCost"}
            recommendations.append(nodetype_best_ratio)

        nodetype_subset = [nodetype for nodetype, perf in zip(
            nodetype_arr, perf_arr) if perf >= perf_constraint]
        cost_subset = [cost for cost, perf in zip(
            cost_arr, perf_arr) if perf >= perf_constraint]
        if nodetype_subset and cost_subset:
            assert len(nodetype_subset) == len(cost_subset)
            nodetype_min_cost = {"nodetype": nodetype_subset[np.argmin(cost_subset)],
                                 "objective": "MinCostWithPerfLimit"}
            recommendations.append(nodetype_min_cost)

        nodetype_subset = [nodetype for nodetype, cost in zip(
            nodetype_arr, cost_arr) if cost <= budget]
        perf_subset = [perf for perf, cost in zip(
            perf_arr, cost_arr) if cost <= budget]
        if nodetype_subset and perf_subset:
            assert len(nodetype_subset) == len(perf_subset)
            nodetype_max_perf = {"nodetype": nodetype_subset[np.argmax(perf_subset)],
                                 "objective": "MaxPerfWithCostLimit"}
            recommendations.append(nodetype_max_perf)

        return recommendations

    @staticmethod
    def initialize_sizing_doc(session_id, app_name):
        """ This method creates the initial sizing document and stores it to the database.
            This method is called only when a sizing session is initiated
        """

        app = get_app_info(app_name)
        sizing_doc = {'sessionId': session_id, 'appName': app['name'], 'sloType': app['slo']['type'],
                      'sloValue': app['slo']['value'], 'budget': app['budget']['value'],
                      'sizingRuns': [], 'status': "started"}

        session_filter = {"sessionId": session_id}
        result = metricdb[sizing_collection].replace_one(session_filter, sizing_doc, True)
        if result.matched_count > 0:
            logger.warning(f"Sizing document for session {session_id} already exists; overwritten")

    @staticmethod
    def store_sizing_run(session_id, samples):
        """ This method stores the sample test results from each sizing run to the database.
        """

        session_filter = {'sessionId': session_id}
        sizing_doc = metricdb[sizing_collection].find_one(session_filter)
        if sizing_doc is None:
            logger.error(f"[{session_id}]Target sizing document cannot be found")
            raise KeyError(
                'Cannot find sizing document: filter={}'.format(session_filter))

        results = []
        for sample in samples:
            assert sample['cost'].values[0] > 0, "Non-positive cost value encountered."
            result = {'nodetype': sample['nodetype'].values[0],
                      'status': "done",
                      'qosValue': sample['qos_value'].values[0],
                      'cost': sample['cost'].values[0],
                      'perfOverCost': sample['qos_value'].values[0] / sample['cost'].values[0]
                     }
            results.append(result)

        sizing_runs = sizing_doc['sizingRuns']
        sizing_run = {'run': len(sizing_runs) + 1,
                      'samples': len(samples),
                      'results': results
                     }
        sizing_runs.append(sizing_run)
        metricdb[sizing_collection].find_one_and_update(
            session_filter, {'$set': {'sizingRuns': sizing_runs, 'status': "running"}})
        logger.info(f"[{session_id}]New sizing run results have been stored in the database\n{sizing_run}")

    @staticmethod
    def store_final_result(session_id, recommendations):
        """ This method stores the final recommendations from the sizing session to the database.
            This method is called only after the analysis is completed
        """

        # TODO: check if mongodb is thread safe?
        session_filter = {'sessionId': session_id}
        sizing_doc = metricdb[sizing_collection].find_one_and_update(
            session_filter, {'$set': {"status": "complete", 'recommendations': recommendations}})

        if sizing_doc is None:
            logger.error(f"[{session_id}]Target sizing document cannot be found")
            raise KeyError(
                'Cannot find sizing document: filter={}'.format(session_filter))
        logger.info(f"[{session_id}]Final recommendations have been stored in the database")

        return None
