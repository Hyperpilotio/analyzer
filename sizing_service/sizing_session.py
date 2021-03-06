from __future__ import division, print_function

import threading

import numpy as np
import pandas as pd
import copy

from api_service.db import metricdb
from config import get_config
from logger import get_logger

from .bayesian_optimizer import get_candidate
from .session_worker_pool import FuncArgs, Status, SessionStatus, SessionWorkerPool
from state.apps import (get_app_by_name, get_slo_type, get_slo_value, get_budget)
from api_service.util import (get_all_nodetypes, compute_cost, decode_nodetype, encode_nodetype,
                              get_price, get_raw_features, get_feature_bounds, get_resource_requests)

config = get_config()
sizing_collection = config.get("ANALYZER", "SIZING_COLLECTION")
num_init_samples = config.getint("BAYESIAN_OPTIMIZER_SESSION", "INIT_SAMPLES")
min_samples = config.getint("BAYESIAN_OPTIMIZER_SESSION", "MIN_SAMPLES")
max_samples = config.getint("BAYESIAN_OPTIMIZER_SESSION", "MAX_SAMPLES")
min_improvement = config.getfloat("BAYESIAN_OPTIMIZER_SESSION", "MIN_IMPROVEMENT")
BO_objectives = config.get("BAYESIAN_OPTIMIZER_SESSION", "BO_OBJECTIVES").split(',')
num_workers = config.getint("BAYESIAN_OPTIMIZER_SESSION", "MAX_WORKERS_PER_SESSION")

pd.set_option('display.width', 1000)  # widen the display
np.set_printoptions(precision=3)

# static logger
logger = get_logger(__name__, log_level=(
    "BAYESIAN_OPTIMIZER_SESSION", "LOGLEVEL"))


class SizingSession():
    """ This class manages the training samples in a single sizing session,
        dispatches jobs to the worker pool, and tracks the status of each job.
    """
    __instance_lock = threading.Lock()

    def __init__(self, session_id):
        self.session_id = session_id

        # A single worker pool for this session
        self.pool = SessionWorkerPool(num_workers)
        # Map for caching sample data throughout each sizing session
        self.sample_dataframe = None
        # Map for optimal perf_over_cost value from all samples evaluted
        self.optimal_poc = None
        # Map for caching all the available nodetypes for each session
        self.available_nodetype_set = None

    def get_candidates(self, app_name, sample_data):
        """ The public method to asychronously start the jobs for generating candidates.
        Args:
            app_name(str): Name of the target application
            sample_data(list): List of reported sample data per instance type
        """

        # Generate initial samples if the sample_data field is empty (only at the start of a session)
        if not sample_data or len(sample_data) == 0:
            assert self.available_nodetype_set is None,\
                "Incoming sample_data can only be empty at the beginning of a session"
            # initialize with all available nodetypes (defensive copy)
            self.available_nodetype_set = set(copy.deepcopy(get_all_nodetypes()).keys())

            # update available nodetypes with app container resource requests
            min_resources = get_resource_requests(app_name)
            excluded_nodetypes = []
            for nodetype_name in self.available_nodetype_set:
                raw_features = get_raw_features(nodetype_name)
                if raw_features[0] < min_resources['cpu'] or raw_features[2] < min_resources['mem']:
                    excluded_nodetypes.append(nodetype_name)
            logger.debug(
                f"[{self.session_id}] Nodetypes to be excluded due to insufficient resources: {excluded_nodetypes} ")
            self.update_available_nodetype_set(excluded_nodetypes)

            try:
                self.initialize_sizing_doc(app_name)
                logger.info(f"[{self.session_id}] Initial sizing document created")
            except Exception as e:
                return SessionStatus(status=Status.SERVER_ERROR,
                                     error="Failed to create initial sizing document: " + str(e))

            # draw inital samples
            logger.debug(f"[{self.session_id}] Generating {num_init_samples} random initial samples")
            functions = []
            functions.append(
                FuncArgs(SizingSession.generate_initial_samples, num_init_samples, self.available_nodetype_set))
            with self.__instance_lock:
                return self.pool.submit_funcs(functions)

        # Pre-process sample data and remove unavailable nodetypes
        logger.debug(f"[{self.session_id}] Received non-empty sample data; preprocessing...")
        unavailable_nodetypes = [i['instanceType'] for i in
                                 filter(lambda d: d['qosValue'] == 0., sample_data)]
        self.update_available_nodetype_set(unavailable_nodetypes)

        sample_data = list(filter(lambda d: d['qosValue'] != 0., sample_data))
        if not sample_data or len(sample_data) == 0:
            logger.debug(
                f"[{self.session_id}] All nodetypes suggested previously are unavailable; regenerating...")
            functions = []
            functions.append(
                FuncArgs(SizingSession.generate_initial_samples, num_init_samples, self.available_nodetype_set))
            with self.__instance_lock:
                return self.pool.submit_funcs(functions)


        # Update sample dataframe and check termination
        new_sample_dataframe = SizingSession.create_sample_dataframe(app_name, sample_data)
        # Store the sizing run result to the database
        self.update_sizing_run(new_sample_dataframe)
        self.update_available_nodetype_set(new_sample_dataframe['nodetype'].values)
        self.update_sample_dataframe(new_sample_dataframe)
        assert self.sample_dataframe is not None, "sample dataframe should not be empty"
        logger.debug(f"[{self.session_id}] All training samples evaluted:\n{self.sample_dataframe}")

        if self.check_termination():
            recommendations = self.compute_recommendations()
            logger.info(
                f"[{self.session_id}] Sizing analysis is done; final recommendations:\n{recommendations}")
            self.store_final_result(recommendations)
            #functions = []
            #functions.append(FuncArgs(self.store_final_result, recommendations))
            #return self.pool.submit_funcs(functions)
            return SessionStatus(status=Status.DONE)

        # Dispatch the optimizers for multiple objective functions in parallel
        functions = []
        logger.debug(f"Objective functions used: {BO_objectives}")
        for obj in BO_objectives:
            training_data = SizingSession.make_optimizer_training_data(
                self.sample_dataframe, obj)
            logger.debug(f"[{self.session_id}] Dispatching optimizer for objective {obj} \
                with training data:\n{training_data}")
            functions.append(
                FuncArgs(get_candidate, \
                         training_data.feature_mat, \
                         training_data.objective_arr, \
                         get_feature_bounds(normalized=True), \
                         acq='cei' if training_data.has_constraint() else 'ei', \
                         constraint_arr=training_data.constraint_arr, \
                         constraint_upper=training_data.constraint_upper))

        with self.__instance_lock:
            return self.pool.submit_funcs(functions)

    def get_status(self):
        """ The public method to get the state of current optimization jobs of a session.
        """
        status = self.pool.get_status()
        if status.status == Status.DONE:
            candidates = status.data
            if not candidates or len(candidates) == 0:
                logger.debug(f"[{self.session_id}] No more candidate suggested.")
            else:
                if type(candidates[0][0]) is str:
                    # candidates are nodetypes
                    status.data = candidates[0]
                    # TESTING: Return only the first candidate
                    #status.data = [candidates[0][0]]
                else:
                    # candidates are feature vectors; need to be decoded into nodetypes
                    # TESTING: Return only the first candidate
                    #candidates = [candidates[0]]
                    status.data = self.filter_candidates(
                        [decode_nodetype(c, list(self.available_nodetype_set))
                            for c in candidates if c is not None])
                logger.debug(
                    f"[{self.session_id}] New candidates suggested for the next sizing run: {status.data}")
                self.store_sizing_run(status.data)

        return status

    def update_available_nodetype_set(self, exclude_keys):
        with self.__instance_lock:
            assert self.available_nodetype_set is not None,\
                "This method should only be called after the a session was initialized"

            for k in exclude_keys:
                self.available_nodetype_set.discard(k)

    def update_sample_dataframe(self, new_sample_dataframe):
        with self.__instance_lock:
            curr_sample_dataframe = self.sample_dataframe
            if curr_sample_dataframe is not None:
                # check if incoming df contains duplicated nodetypes with existing sample_map
                intersection = set(new_sample_dataframe['nodetype']).intersection(
                    set(curr_sample_dataframe['nodetype']))
                if intersection:
                    logger.warning(f"[{self.session_id}] Duplicated samples were sent from the client")
                    logger.warning(f"[{self.session_id}]  new samples:\n\
                        {new_sample_dataframe}\ncurrent samples:\n{curr_sample_dataframe}")
                    logger.warning(f"[{self.session_id}]  intersection: {intersection}")

            self.sample_dataframe = pd.concat(
                [curr_sample_dataframe, new_sample_dataframe])

    def check_termination(self):
        """ This method determines if the optimization process for a given session_id can terminate.
        Termination conditions:
            1. if total number of samples evaluated exceeds max_samples, or
            2. if total number of samples evaluated exceeds min_samples && incremental improvement
                in the objective over previous runs is within min_improvement, or
            3. if available nodetype map is empty
        """
        all_samples = self.sample_dataframe
        if (all_samples is not None) and (len(all_samples) > max_samples):
            logger.debug(f"[session_id]:Termination condition is met due to enough number of samples = {len(df)}")
            return True

        if not self.available_nodetype_set:
            logger.debug(f"[session_id]:Termination condition is met due running out of available nodetypes")
            return True

        new_opt_poc = self.compute_optimum()
        optimal_poc = self.optimal_poc
        if (optimal_poc is None) or (len(all_samples) < min_samples) or\
                (new_opt_poc - optimal_poc >= min_improvement * optimal_poc):
            self.optimal_poc = new_opt_poc
            return False
        else:
            logger.debug(f"[session_id]:Termination condition is met due to small incremental improvement.\n\
                old_opt_poc = {optimal_poc}, new_opt_poc = {new_opt_poc}")
            return True

    def filter_candidates(self, candidate_rank_list):
        """ This method filters the recommended candidates before returning to the client
            and avoid returning duplicate result by greedily select the closest solutions as possible
        Args:
            candidate_rank_list: list of rank-ordered candidates
        Return:
            result (list): list of suggested nodetypes
        """
        # double check the candidate_rank_list does not consist of any nodetype in sample_map
        # if the samplei_map is None, BO is in initialization state
        if self.sample_dataframe is not None:
            for l in candidate_rank_list:
                for row in l:
                    nodetype = row[1]
                    assert nodetype not in self.sample_dataframe['nodetype'].values, \
                        f"{nodetype} shouldn't exist in sample map at this point"

        # Get the closest candidate greedily
        result = []
        for l in candidate_rank_list:
            for row in l:
                nodetype = row[1]
                if nodetype not in result:
                    result.append(nodetype)
                    break

        logger.debug(f"[{self.session_id}] Filtered candidates: {result}")
        assert len(set(result)) == len(result), "Filtered candidates cannot have duplicates"
        return result


    @staticmethod
    def generate_initial_samples(num_samples, available_nodetypes=None):
        """ This method randomly select a 'instanceFamily',
            and randomly select a 'nodetype' from that family repeatly
        """
        all_nodetypes = get_all_nodetypes()
        node_values = []
        if available_nodetypes:
            for nodetype in available_nodetypes:
                node_values.append(all_nodetypes[nodetype])
        else:
            node_values = list(all_nodetypes.values())

        dataframe = pd.DataFrame.from_dict(node_values)
        instance_families = list(set(dataframe['instanceFamily']))
        available = list(instance_families)
        # check if there is any instance's instanceFamily field is empty string
        assert '' not in instance_families, "instanceFamily shouldn't be empty"
        result = []

        while num_samples > 0:
            family = np.random.choice(instance_families, 1)[0]
            if family in available:
                nodetype = np.random.choice(
                    dataframe[dataframe['instanceFamily'] == family]['name'], 1)[0]
                result.append(nodetype)
                num_samples -= 1
                available.remove(family)

            # reset available when all families are visited
            if not available:
                available = list(instance_families)

        logger.debug(f"Generated initial random samples:\n{result}")
        return result

    @staticmethod
    def make_optimizer_training_data(sample_dataframe, objective_type=None):
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

        feature_mat = np.array(sample_dataframe['feature'].tolist())
        slo_type = sample_dataframe['slo_type'].iloc[0]
        budget = sample_dataframe['budget'].iloc[0]
        perf_constraint = sample_dataframe['slo_value'].iloc[0]
        perf_arr = sample_dataframe['qos_value']

        # Convert metric so we always try to maximize performance
        if slo_type == 'latency':
            perf_arr = 1. / sample_dataframe['qos_value']
            perf_constraint = 1. / perf_constraint
        elif slo_type == 'throughput':
            pass
        else:
            raise AssertionError(f'invalid slo type: {slo_type}')

        # Compute objectives
        perf_over_cost = (
            perf_arr / sample_dataframe['cost']).rename("performance over cost")

        if objective_type == 'perf_over_cost':
            return BOTrainingData(objective_type,
                                  feature_mat,
                                  perf_over_cost)
        elif objective_type == 'cost_given_perf_limit':
            return BOTrainingData(objective_type,
                                  feature_mat,
                                  -sample_dataframe['cost'],
                                  -perf_arr, -perf_constraint)
        elif objective_type == 'perf_given_cost_limit':
            return BOTrainingData(objective_type,
                                  feature_mat,
                                  perf_arr,
                                  sample_dataframe['cost'],
                                  budget)
        else:
            raise UserWarning("Unexpected error")

    @staticmethod
    def create_sample_dataframe(app_name, sample_data):
        """ Convert input sample data to dataframe of training samples.
        Args:
            app_name(str): Name of the target application
            sample_data(list): List of reported sample data per instance type
        Returns:
                dfs(dataframe): sample data organized in dataframe
        """
        slo_type = get_slo_type(app_name)
        assert slo_type in ['throughput', 'latency'], \
            f'slo type should be either throughput or latency, but got {slo_type}'

        dfs = []
        for data in sample_data:
            nodetype = data['instanceType']
            qos_value = data['qosValue']
            df = pd.DataFrame({'app_name': [app_name],
                               'qos_value': [qos_value],
                               'slo_type': [slo_type],
                               'nodetype': [nodetype],
                               'feature': [encode_nodetype(nodetype)],
                               'cost': [compute_cost(get_price(nodetype), slo_type, qos_value)],
                               'slo_value': [get_slo_value(app_name)],
                               'budget': [get_budget(app_name)]})
            dfs.append(df)
        assert dfs, f'dataframe is not created for sample_data:\n{sample_data}'

        dfs = pd.concat(dfs)
        return dfs

    def compute_optimum(self):
        """ Compute the optimal perf_over_cost value among all given samples
        """
        assert self.sample_dataframe is not None and len(
            self.sample_dataframe) > 0

        slo_type = self.sample_dataframe['slo_type'].iloc[0]
        if slo_type == 'latency':
            perf_arr = 1. / self.sample_dataframe['qos_value']
        else:
            perf_arr = self.sample_dataframe['qos_value']

        perf_over_cost = perf_arr / self.sample_dataframe['cost']
        return np.max(perf_over_cost)

    def compute_recommendations(self):
        """ Compute the final recommendations from the optimizer -
            optimal node types among all samples based on three different objective functions:
            1. MaxPerfOverCost
            2. MinCostWithPerfLimit
            3. MaxPerfWithCostLimit
            This method is called only after the analysis is completed.
        """

        recommendations = []

        perf_arr = self.sample_dataframe['qos_value'].values
        cost_arr = self.sample_dataframe['cost'].values
        nodetype_arr = self.sample_dataframe['nodetype'].values
        slo_type = self.sample_dataframe['slo_type'].iloc[0]
        budget = self.sample_dataframe['budget'].iloc[0]
        perf_constraint = self.sample_dataframe['slo_value'].iloc[0]

        # Convert qos value so we always maximize performance
        if slo_type == 'latency':
            perf_arr = 1. / perf_arr
            perf_constraint = 1. / perf_constraint
        perf_over_cost_arr = list(perf_arr / cost_arr)
        if perf_over_cost_arr:
            nodetype_best_ratio = {"nodetype": nodetype_arr[np.argmax(
                perf_over_cost_arr)], "objective": "MaxPerfOverCost"}
            recommendations.append(nodetype_best_ratio)

        nodetype_subset = [nodetype for nodetype, perf in zip(
            nodetype_arr, perf_arr) if perf >= perf_constraint]
        cost_subset = [cost for cost, perf in zip(
            cost_arr, perf_arr) if perf >= perf_constraint]
        if nodetype_subset and cost_subset:
            assert len(nodetype_subset) == len(cost_subset)
            nodetype_min_cost = {"nodetype": nodetype_subset[np.argmin(
                cost_subset)], "objective": "MinCostWithPerfLimit"}
            recommendations.append(nodetype_min_cost)

        nodetype_subset = [nodetype for nodetype, cost in zip(
            nodetype_arr, cost_arr) if cost <= budget]
        perf_subset = [perf for perf, cost in zip(
            perf_arr, cost_arr) if cost <= budget]
        if nodetype_subset and perf_subset:
            assert len(nodetype_subset) == len(perf_subset)
            nodetype_max_perf = {"nodetype": nodetype_subset[np.argmax(
                perf_subset)], "objective": "MaxPerfWithCostLimit"}
            recommendations.append(nodetype_max_perf)

        return recommendations

    def initialize_sizing_doc(self, app_name):
        """ This method creates the initial sizing document and stores it to the database.
            This method is called only when a sizing session is initiated
        """

        app = get_app_by_name(app_name)
        sizing_doc = {'sessionId': self.session_id, 'appName': app['name'], 'sloType': app['slo']['type'],
                      'sloValue': app['slo']['value'], 'budget': app['budget']['value'],
                      'sizingRuns': [], 'status': "started"}

        session_filter = {"sessionId": self.session_id}
        result = metricdb[sizing_collection].replace_one(
            session_filter, sizing_doc, True)
        if result.matched_count > 0:
            logger.warning(
                f"[{self.session_id}] Sizing document for this session already exists; overwritten")

    def store_sizing_run(self, candidates):
        """ This method stores the info of a new sizing run to the database.
        """

        session_filter = {'sessionId': self.session_id}
        sizing_doc = metricdb[sizing_collection].find_one(session_filter)
        if sizing_doc is None:
            logger.error(f"[{self.session_id}] Target sizing document cannot be found")
            raise KeyError(
                'Cannot find sizing document: filter={}'.format(session_filter))

        sizing_runs = sizing_doc['sizingRuns']
        if len(sizing_runs) > 0:
            last_sizing_run = sizing_runs[-1]
            if last_sizing_run['results'][0]["status"] == "running":
                logger.debug(f"[{self.session_id}] Last sizing run info already exists; skip creation")
                return None

        results = []
        for nodetype in candidates:
            result = {'nodetype': nodetype,
                      'status': "running"
                     }
            results.append(result)
        new_sizing_run = {'run': len(sizing_runs) + 1,
                          'samples': len(candidates),
                          'results': results
                         }
        sizing_runs.append(new_sizing_run)
        metricdb[sizing_collection].find_one_and_update(
            session_filter, {'$set': {'sizingRuns': sizing_runs, 'status': "running"}})
        logger.debug(f"[{self.session_id}] New sizing run info is saved to the database:\n{new_sizing_run}")

    def update_sizing_run(self, sample_dataframe):
        """ This method stores the sample test results from the last sizing run to the database.
        """

        session_filter = {'sessionId': self.session_id}
        sizing_doc = metricdb[sizing_collection].find_one(session_filter)
        if sizing_doc is None:
            logger.error(f"[{self.session_id}] Target sizing document cannot be found")
            raise KeyError(
                'Cannot find sizing document: filter={}'.format(session_filter))

        sizing_runs = sizing_doc['sizingRuns']
        last_sizing_run = sizing_runs[-1]
        results = last_sizing_run['results']

        for n, result in enumerate(results):
            updated = False
            for i, sample in sample_dataframe.iterrows():
                if sample['nodetype'] == result['nodetype']:
                    assert sample['cost'] > 0, "Non-positive cost value encountered."
                    new_result = {'nodetype': sample['nodetype'],
                                  'status': "done",
                                  'qosValue': sample['qos_value'],
                                  'cost': sample['cost'],
                                  'perfOverCost': sample['qos_value'] / sample['cost']
                                  }
                    updated = True
                    break
            if not updated:
                logger.debug(f"[{self.session_id}] No valid result came back for nodetype {result['nodetype']};\
                     set all metrics to zero")
                new_result = {'nodetype': result['nodetype'],
                              'status': "done",
                              'qosValue': 0.,
                              'cost': 0.,
                              'perfOverCost': 0.
                              }
            results[n] = new_result

        last_sizing_run['results'] = results
        metricdb[sizing_collection].find_one_and_update(
            session_filter, {'$set': {'sizingRuns': sizing_runs}})
        logger.info(f"[{self.session_id}] Results from the last sizing run are stored in the database\
            \n{last_sizing_run}")

    def store_final_result(self, recommendations):
        """ This method stores the final recommendations from the sizing session to the database.
            This method is called only after the analysis is completed
        """

        # TODO: check if mongodb is thread safe?
        session_filter = {'sessionId': self.session_id}
        sizing_doc = metricdb[sizing_collection].find_one_and_update(
            session_filter, {'$set': {"status": "complete", 'recommendations': recommendations}})

        if sizing_doc is None:
            logger.error(f"[{self.session_id}] Target sizing document cannot be found")
            raise KeyError(
                'Cannot find sizing document: filter={}'.format(session_filter))
        logger.info(f"[{self.session_id}] Final recommendations have been stored in the database")

        return None
