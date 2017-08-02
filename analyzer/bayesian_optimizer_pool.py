#!/usr/bin/env python3
from __future__ import division, print_function

import threading
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from logger import get_logger

from .bayesian_optimizer import get_candidate
from .util import (compute_cost, decode_instance_type, encode_instance_type,
                   get_all_nodetypes, get_feature_bounds, get_price, get_slo_type, get_slo_value, get_budget)

logger = get_logger(__name__, log_level=(
    "BAYESIAN_OPTIMIZER_POOL", "LOGLEVEL"))


class BayesianOptimizerPool():
    """ This class manages the training samples for each app_id,
        dispatches the optimization jobs, and tracks the status of each job.
    """

    # TODO: Thread safe?
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
        # Place for storing samples of each app_id.
        self.sample_map = {}
        # Place for storing python concurrent object.
        self.future_map = {}
        # Pool of worker processes
        self.worker_pool = ProcessPoolExecutor(max_workers=16)

    def get_candidates(self, app_id, request_body):
        """ The public method to dispatch optimizers asychronously.
        Args:
            app_id(str): unique key to identify the application
            request_body(dict): the request body sent from the client of the analyzer service
        """

        # initialize points if there is no training sample coming
        if not request_body.get('data'):
            self.future_map[app_id] = []
            init_points = BayesianOptimizerPool.generate_initial_points()
            for i in init_points:
                future = self.worker_pool.submit(encode_instance_type, i)
                self.future_map[app_id].append(future)
        # Else dispatch the optimizers
        else:
            # create datafame
            df = BayesianOptimizerPool.create_sample_dataframe(request_body)
            # update the shared sample map
            self.update_sample_map(app_id, df)
            # fetch the latest sample_map
            dataframe = self.sample_map[app_id]
            # create the training data to Bayesian optimizer
            training_data_list = [BayesianOptimizerPool.make_optimizer_training_data(
                dataframe, objective_type=o)
                for o in ['perf_over_cost',
                          'cost_given_perf', 'perf_given_cost']]

            feature_bounds = get_feature_bounds()
            self.future_map[app_id] = []
            for training_data in training_data_list:
                logger.debug(f"[{app_id}]Dispatching optimizer:\n{training_data}")
                acq = 'cei' if training_data.has_constraint() else 'ei'

                future = self.worker_pool.submit(
                    get_candidate,
                    training_data.feature_mat,
                    training_data.objective_arr,
                    feature_bounds,
                    acq=acq,
                    constraint_arr=training_data.constraint_arr,
                    constraint_upper=training_data.constraint_upper
                )
                self.future_map[app_id].append(future)
            return {"status": "submitted"}

    def get_status(self, app_id):
        """ The public method to get the running state of each worker.
        """
        future_list = self.future_map.get(app_id)
        if future_list:
            if any([future.running() for future in future_list]):
                return {"status": "running"}
            elif any([future.cancelled() for future in future_list]):
                return {"status": "execption", "exception": "task cancelled"}
            elif all([future.done() for future in future_list]):
                try:
                    candidates = [future.result() for future in future_list]
                except Exception as e:
                    return {"status": "exception",
                            "data": str(e)}
                else:

                    return {"status": "done",
                            "data": self.filter_candidates(app_id, [decode_instance_type(c) for c in candidates])}

                return {"status": "unexpected future state"}
        else:
            return {"status": "not running"}

    def update_sample_map(self, app_id, df):
        with self.__singleton_lock:
            if self.sample_map.get(app_id) is not None:
                # check if incoming df contains duplicated instance_type with sample_map:
                intersection = set(df['instance_type']).intersection(
                    set(self.sample_map[app_id]['instance_type']))
                if intersection:
                    logger.warning(f"Duplicated sample was sent from client")
                    logger.warning(f"input:\n{df}\nsample_map:\n{self.sample_map.get(app_id)}")
                    logger.warning(f"intersection: {intersection}")

            self.sample_map[app_id] = pd.concat(
                [df, self.sample_map.get(app_id)])

    def filter_candidates(self, app_id, candidates, max_run=10):
        """ This method determine if candidates should be returned to client.
        Terminate conditions: 1. if number of run exceed than max_run or,
                              2. if the recommended instance_type is duplicated within this run or with previous runs
        """
        # remove duplicates within this run
        candidates = list(set(candidates))

        if self.sample_map.get(app_id) is None:
            return candidates
        else:  # remove duplicates with previous run
            return [c for c in candidates if c not in self.sample_map.get(app_id)['instance_type'].values]

    @staticmethod
    def generate_initial_points(init_points=3):
        """ This method randomly select a 'instanceFamily',
            and randomly select a 'nodetype' from that family repeatly
        """
        dataframe = pd.DataFrame.from_dict(get_all_nodetypes()['data'])
        instance_families = list(set(dataframe['instanceFamily']))
        available = list(instance_families)
        # check if there is any instance's instanceFamily field is empty string
        assert '' not in instance_families, "instanceFamily shouldn't be empty"
        result = []

        logger.debug("Generating random initial points")
        while init_points > 0:
            family = np.random.choice(instance_families, 1)[0]  # O(1)
            if family in available:  # O(n)
                instance_type = np.random.choice(
                    dataframe[dataframe['instanceFamily'] == family]['name'], 1)[0]
                result.append(instance_type)
                init_points -= 1
                available.remove(family)  # O(n)

            # refill available
            if not available:
                available = list(instance_families)

        logger.debug(f"initial points:\n{result}")
        return result

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
                return f'objective_type:\n{self.objective_type}\n' +\
                    f'feature_mat:\n{self.feature_mat}\n' +\
                    f'objective_arr:\n{self.objective_arr}\n' +\
                    f'constraint_arr:\n{self.constraint_arr}\n' +\
                    f'constraint_upper:\n{self.constraint_upper}\n'

            def has_constraint(self):
                """ See if this trainning data has constraint """
                return self.constraint_upper is not None

        implmentation = ['perf_over_cost',
                         'cost_given_perf', 'perf_given_cost']
        if objective_type not in implmentation:
            raise NotImplementedError(f'objective_type: {objective_type} is not implemented.')

        feature_mat = np.array(df['feature'].tolist())
        slo_type = df['slo_type'].iloc[0]
        budget = df['budget'].iloc[0]
        perf_constraint = df['slo'].iloc[0]
        perf_arr = df['qos_value']

        # Convert metric so we always try to maximize performance
        if slo_type == 'latency':
            perf_arr = 1. / df['qos_value']
            perf_constraint = 1 / perf_constraint
        elif slo_type == 'throughput':
            pass
        else:
            raise AssertionError(f'invalid slo type: {slo_type}')

        if objective_type == 'perf_over_cost':
            return BOTrainingData(objective_type, feature_mat, perf_arr / df['cost'])
        elif objective_type == 'cost_given_perf':
            return BOTrainingData(objective_type, feature_mat, df['cost'], -perf_arr, -perf_constraint)
        elif objective_type == 'perf_given_cost':
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
            instance_type = data['instanceType']
            qos_value = data['qosValue']

            df = pd.DataFrame({'app_name': [app_name],
                               'qos_value': [qos_value],
                               'slo_type': [slo_type],
                               'instance_type': [instance_type],
                               'feature': [encode_instance_type(instance_type)],
                               'cost': [compute_cost(get_price(instance_type), slo_type, qos_value)],
                               'slo': [get_slo_value(app_name)],
                               'budget': [get_budget(app_name)]
                               })
            dfs.append(df)
        if not dfs:
            raise AssertionError(f'dataframe is not created\nrequest_body:\n{request_body}')
        return pd.concat(dfs)
