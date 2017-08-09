#!/usr/bin/env python3
from __future__ import division, print_function

import threading
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from config import get_config
from logger import get_logger

from .bayesian_optimizer import get_candidate
from .util import (compute_cost, decode_nodetype, encode_nodetype,
                   get_all_nodetypes, get_budget, get_feature_bounds,
                   get_price, get_slo_type, get_slo_value)

config = get_config()
max_samples = int(config.get("ANALYZER", "MAX_SAMPLES"))
min_improvement = float(config.get("ANALYZER", "MIN_IMPROVEMENT"))

pd.set_option('display.width', 1000)  # widen the display
np.set_printoptions(precision=3)
logger = get_logger(__name__, log_level=(
    "BAYESIAN_OPTIMIZER_POOL", "LOGLEVEL"))


class BayesianOptimizerPool():
    """ This class manages the training samples for each session_id,
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
        # Map for sharing data samples throughout the optimization session for each session_id
        self.sample_map = {}
        # Map for storing the future objects for python concurrent tasks
        self.future_map = {}
        # Pool of worker processes for handling jobs
        self.worker_pool = ProcessPoolExecutor(max_workers=16)
        # Optimal perf_over_cost value from all samples evaluted
        self.optimal_poc = {}
        # Record the avaialbe
        self.available_nodetype_map = {}

    def get_candidates(self, session_id, request_body, **kwargs):
        """ The public method to asychronously start the jobs for generating candidates.
        Args:
            session_id(str): unique key to identify the optimization session for each session_id
            request_body(dict): the request body sent from the client of the analyzer service
        """

        # Generate initial samples if the data field of request_body is empty (special case)
        if not request_body.get('data'):
            assert self.available_nodetype_map.get(
                session_id) is None, 'This block should only be executed once at the first beginning of a session'

            # initialize with all available nodetype
            self.available_nodetype_map[session_id] = get_all_nodetypes()
            # draw inital samples
            init_samples = BayesianOptimizerPool.generate_initial_samples()
            self.future_map[session_id] = [self.worker_pool.submit(
                encode_nodetype, i) for i in init_samples]
            return {"status": "success"}

        # Pre-process request
        unavailable_nodetypes = [i['instanceType'] for i in
                                 filter(lambda d: d['qosValue'] == 0., request_body['data'])]
        self.update_available_nodetype_map(session_id, unavailable_nodetypes)

        # remove and record unavailable nodetypes
        print('before')
        print(request_body)
        request_body['data'] = list(
            filter(lambda d: d['qosValue'] != 0., request_body['data']))
        print('after')
        print(request_body)
        if not request_body['data']:
            random_samples = BayesianOptimizerPool.generate_initial_samples()
            self.future_map[session_id] = [self.worker_pool.submit(
                encode_nodetype, i) for i in random_samples]
            return {"status": "success"}
        assert request_body['data'], 'The data field of filtered request_body should not be empty'

        # Update sample map and check termination
        self.update_sample_map(
            session_id, BayesianOptimizerPool.create_sample_dataframe(request_body))
        logger.info(f"[{session_id}]All training samples evaluted:\n{self.sample_map}")

        if self.check_termination(session_id):
            logger.info(f"[{session_id}]Sizing analysis is done; store final result in database")
            self.future_map[session_id] = [self.worker_pool.submit(
                BayesianOptimizerPool.store_final_result, session_id, self.sample_map.get(session_id))]
            return {"status": "success"}

        # Dispatch the optimizers
        assert self.sample_map.get(
            session_id) is not None, 'sample map should not be empty'
        training_data_list = [BayesianOptimizerPool.make_optimizer_training_data(
            self.sample_map[session_id], objective_type=o) for o in ['perf_over_cost',
                                                                 'cost_given_perf_limit',
                                                                 'perf_given_cost_limit']]
        self.future_map[session_id] = []
        for training_data in training_data_list:
            logger.info(
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
                    "error": f"session_id {session_id} is not found"}

        if all([future.done() for future in future_list]):
            candidates = [future.result() for future in future_list]
            if not candidates:
                logger.info(f"[{session_id}]No more candidate suggested.")
                return {"status": "done", "data": []}
            else:
                logger.info(f"[{session_id}]New candidates suggested:\n{candidates}")
                return {"status": "done",
                        "data": self.filter_candidates(session_id,
                                                       [decode_nodetype(c) for c in candidates if c is not None])}
        elif any([future.cancelled() for future in future_list]):
            return {"status": "server_error", "error": "task cancelled"}
        else:
            # Running or pending
            return {"status": "running"}

    def update_available_nodetype_map(self, session_id, exclude_keys):
        with self.__singleton_lock:
            assert self.available_nodetype_map.get(
                session_id) is not None, 'This method should only be called after the a session was initialized'

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

            # TODO: store the latest samples (df) to the database

    def check_termination(self, session_id):
        """ This method determines if the optimization process for a given session_id can terminate.
        Termination conditions:
            1. if total number of samples evaluated exceeds max_samples or,
            2. if incremental improvement in the objective over previous runs is within min_improvement.
        """
        df = self.sample_map.get(session_id)
        if (df is not None) and (len(df) > max_samples):
            return True

        opt_poc = BayesianOptimizerPool.compute_optimum(df)
        optimal_poc = self.optimal_poc.get(session_id)
        if (optimal_poc is None) or (opt_poc - optimal_poc > min_improvement * optimal_poc):
            self.optimal_poc[session_id] = opt_poc
            return False
        # if incremental improvement from the last batch is too small to continue
        else:
            return True

    @staticmethod
    def store_final_result(session_id, df):
        """ This method stores the final result of the optimization process to the database.
            This method is called only after the analysis is completed
        """
        recommendations = BayesianOptimizerPool.compute_recommendations(df)
        logger.info(f"[{session_id}]Final recommendations:\n{recommendations}")

        # TODO: update_sizing_in_metricdb with the final recommendations
        # TODO: check if mongodb is thread safe?
        # TODO: if return in the data format the client will take
        return None

    def filter_candidates(self, session_id, candidates):
        """ This method filters the recommended candidates before returning to the client
            and removes the duplicates within this run or with previous runs.
        """
        # remove duplicates within this run
        candidates = list(set(candidates))

        if self.sample_map.get(session_id) is None:
            return candidates
        else:
            # return candidates while removing duplicates with previous runs
            return [c for c in candidates if c not in self.sample_map.get(session_id)['nodetype'].values]

    # def filter_candidates(self, session_id, candidates, max_run=10):
    #     """ This method determine if candidates should be returned to client. # FORCING SELECT OTHER CANIDATES
    #     Terminate conditions: 1. if number of run exceed than max_run or,
    #                           2. if the recommended nodetype is duplicated within this run or with previous runs
    #     """
    #     # remove duplicates within this run
    #     candidates_ = list(set(candidates))

    #     if self.sample_map.get(session_id) is None:
    #         return candidates
    #     elif len(self.sample_map.get(session_id)) >= max_run:  # remove duplicates with previous run
    #         return []
    #     else:
    #         results = []
    #         for c in candidates:
    #             x = c
    #             while (x in self.sample_map.get(session_id)['nodetype'].values) or (x in results):
    #                 x = np.random.choice([i['name'] for i in get_all_nodetypes().values()])
    #             results.append(x)

    #         return results

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
    def psudo_random_generator(all_nodetype, sample_map, unavailable_nodetypes, num=1):
        """ Draw a nodetype that doesn't existed in sample_map
        """
        if sample_map.get('nodetype') is not None:
            for i in sample_map.get('nodetype'):
                if i in all_nodetype:
                    all_nodetype.remove(i)

        for i in unavailable_nodetypes:
            if i in all_nodetype:
                all_nodetype.remove(i)

        return np.random.choice(all_nodetype, num, replace=False) if all_nodetype else None

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
    def create_sample_dataframe(request_body):
        """ Convert request_body to dataframe of training samples.
        Args:
                request_body(dict): request body sent from workload profiler
        Returns:
                dfs(dataframe): sample data organized in dataframe
        """
        app_name = request_body['appName']
        slo_type = get_slo_type(app_name)
        assert slo_type in ['throughput', 'latency'],\
            f'slo type should be either throughput or latency, but got {slo_type}'

        dfs = []
        for data in request_body['data']:
            nodetype = data['instanceType']
            print(nodetype)
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
        return pd.concat(dfs)

    @staticmethod
    def compute_optimum(df):
        """ Compute the optimal perf_over_cost value among all given samples
        """
        assert df is not None and len(df) > 0

        slo_type = df['slo_type'].iloc[0]
        if slo_type == 'latency':
            perf_arr = 1. / df['qos_value']
        else:
            perf_arr = df['qos_value']

        perf_over_cost = perf_arr / df['cost']
        return np.max(perf_over_cost)

    @staticmethod
    def compute_recommendations(df):
        """ Compute the final recommendations from the optimizer -
            optimal node types among all samples based on three different objective functions:
            1. MaxPerfOverCost
            2. MinCostWithPerfLimit
            3. MaxPerfWithCostLimit
            This method is called only after the analysis is completed.
        """

        recommendations = []

        perf_arr = df['qos_value'].values
        cost_arr = df['cost'].values
        nodetype_arr = df['nodetype'].values
        slo_type = df['slo_type'].iloc[0]
        budget = df['budget'].iloc[0]
        perf_constraint = df['slo_value'].iloc[0]

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
