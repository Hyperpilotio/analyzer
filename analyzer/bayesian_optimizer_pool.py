#!/usr/bin/env python3
from __future__ import division, print_function

import threading
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from logger import get_logger

from .bayesian_optimizer import get_candidate
from .util import (compute_cost, decode_instance_type, encode_instance_type,
                   get_all_nodetypes, get_bounds, get_price, get_slo_type)

logger = get_logger(__name__, log_level=("BAYESIAN_OPTIMIZER", "LOGLEVEL"))


class BOTrainingData():
    """ Training data for bayesian optimizer
    """

    def __init__(self, objective_type, feature_mat, objective_arr, constraint_arr=None, constraint_upper=None):
        self.objective_type = objective_type
        self.feature_mat = feature_mat
        self.objective_arr = objective_arr
        self.constraint_arr = constraint_arr
        self.constraint_upper = constraint_upper


class BayesianOptimizerPool():
    """ This class manages the training samples for each app_id,
        dispatches the optimization jobs, and track the status of jobs.
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
            request_body(dict): the request body sent from workload profiler
        Returns:
            None. client are expect to pull the results with get_status method.
        """
        # update the shared sample map holder
        self.update_sample_map(app_id, request_body)
        # fetch the latest sample_map
        df = self.sample_map[app_id]
        # create the training data to Bayesian optimizer
        c1 = BayesianOptimizerPool.create_optimizer_training_data(
            df, objective_type='perf_over_cost')
        c2 = BayesianOptimizerPool.create_optimizer_training_data(
            df, objective_type='cost_given_perf')
        c3 = BayesianOptimizerPool.create_optimizer_training_data(
            df, objective_type='perf_given_cost')

        bounds = get_bounds(get_all_nodetypes())

        self.future_map[app_id] = []
        for c in [c1, c2, c3]:
            logger.info(f"Dispatching optimizer: \n {c}")
            acq = 'ei' if c.constraint_upper is None else 'cei_numeric'

            future = self.worker_pool.submit(
                get_candidate,
                c.feature_mat,
                c.objective_arr,
                bounds,
                acq=acq,
                constraint_arr=c.constraint_arr,
                constraint_upper=c.constraint_upper
            )
            self.future_map[app_id].append(future)

    def get_status(self, app_id):
        """ The public method to get the running state of each worker.
        """
        future_list = self.future_map.get(app_id)
        if future_list:
            if any(map(lambda future: future.running(), future_list)):
                return {"Status": "Running"}
            elif any(map(lambda future: future.cancelled(), future_list)):
                return {"Status": "Cancelled"}
            elif all(map(lambda future: future.done(), future_list)):
                try:
                    candidates = all(map(lambda x: x.result(), future_list))
                except Exception as e:
                    return {"Status": "Exception", "Exception": str(e)}
                else:
                    return {"Status": "Done",
                            "instance_types": [decode_instance_type(c) for c in candidates if not self.should_terminate(c)]}
                return {"Status": "Unexpected future state"}
        else:
            return {"Status": "Not running"}

    def update_sample_map(self, app_id, request_body):
        # TODO: thread safe?
        df = BayesianOptimizerPool.create_sample_dataframe(request_body)
        if df is not None:
            self.sample_map[app_id] = pd.concat(
                [df, self.sample_map.get(app_id)])
        else:
            logger.warning(
                "request body cannot is not converted to sample map dataframe")
            logger.warning(f"request body dump: \n{request_body}")

    # TODO: implement this
    def should_terminate(self, instance_type):
        return True

    @staticmethod
    def create_optimizer_training_data(df, objective_type=None):
        """ Convert the objective and constraints such the optimizer can always‰:
            1. maximize objective function such that 2. constraints function < constraint
        """
        implmentation = ['perf_over_cost',
                         'cost_given_perf', 'perf_given_cost']
        if objective_type not in implmentation:
            raise NotImplementedError(f'objective_type: {objective_type} is not implemented.')

        slo_type = df['slo_type'].values[0]
        assert slo_type in ['throughput', 'latency'], f'invalid slo type: {slo_type}'

        feature_mat = np.array(df['feature'].tolist())
        perf_arr = df['qos_value'] if slo_type == 'throughput' else 1. / \
            df['qos_value']

        if objective_type == 'perf_over_cost':
            return BOTrainingData(objective_type, feature_mat, perf_arr / df['cost'])
        elif objective_type == 'cost_given_perf':
            # minus inverse the comparison operater
            return BOTrainingData(objective_type, feature_mat, df['cost'], -perf_arr, -df['perf_constraint'])
        elif objective_type == 'perf_given_cost':
            return BOTrainingData(objective_type, feature_mat, perf_arr, df['cost'], df['cost_constraint'])
        else:
            logger.error('Impossible...')
            raise UserWarning("Something wrong...")

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
        assert slo_type in ['throughtput', 'latency'],\
            'slo type should be either throught or latency'

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
                               'perf_constraint': [0],  # TODO
                               'cost_constraint': [0]  # TODO
                               })
            dfs.append(df)
        return pd.concat(dfs)
