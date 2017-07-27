#!/usr/bin/env python3
import threading

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from .bayesian_optimizer import get_candidate
from .util import compute_cost, encode_instance_type, decode_instance_type, get_price, get_slo_type


class BayesianOptimizerPool():
    """ BayesianOptimizerPool manages the trainning data for each app_id,
        dispatches the optimization job to different worker, and tracks the status
    """
    # TODO: Thread safe?
    __singleton_lock = threading.Lock()
    __singleton_instance = None

    @classmethod
    def instance(cls):
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

    def update_sample_map(self, app_id, request_body):
        # TODO: thread safe?
        df = self.create_sizing_dataframe(request_body)
        if self.sample_map.get(app_id):
            self.sample_map[app_id].append(df)
        else:
            self.sample_map[app_id] = df

    def get_candidates(self, app_id, request_body):
        df = self.sample_map[app_id]
        # update the shared sample place holder
        self.update_sample_map(app_id, request_body)
        self.future_map[app_id] = []

        df = self.create_sizing_dataframe(request_body)
        features = np.array(df['feature'])
        objective_perf_over_cost = np.array(df['objective_perf_over_cost'])
        objective_cost_satisfies_slo = np.array(
            df['objective_cost_satisfies_slo'])
        objective_perf_satisfies_slo = np.array(
            df['objective_perf_satisfies_slo'])
        bounds = get_bounds()

        for obj in [objective_perf_over_cost, objective_cost_satisfies_slo, objective_perf_satisfies_slo]:
            future = self.worker_pool.submit(
                get_candidate,
                features,
                obj,
                bounds
            )
            self.future_map[app_id].append(future)

    def get_status(self, app_id):
        future_list = self.future_map.get(app_id)
        if future_list:
            if any(map(lambda x: x.running(), future_list)):
                return {"Status": "Running"}
            elif any(map(lambda x: x.cancelled(), future_list)):
                return {"Status": "Cancelled"}
            elif all(map(lambda x: x.done(), future_list)):
                try:
                    candidates = all(map(lambda x: x.result(), future_list))
                except Exception as e:
                    return {"Status": "Exception", "Exception": str(e)}
                else:
                    return {"Status": "Done", "instance_type": list(map(lambda feature: decode_instance_type(feature), candidates))}
            else:
                return {"Status": "Unexpected future state"}
        else:
            return {"Status": "Not running"}

    # TODO: implement objective functions
    @staticmethod
    def _objective_perf_over_cost(data):
        return np.random.rand(1)[0]

    @staticmethod
    def _objective_cost_satisfies_slo(data):
        return np.random.rand(1)[0]

    @staticmethod
    def _objective_perf_satisfies_slo(data):
        return np.random.rand(1)[0]

    @staticmethod
    def create_sizing_dataframe(request_body):
        """ Convert request_body from the workload profiler to dataframe.
        Args:
                request_body(dict): raw data sent from workload profiler.
        Returns:
                df(dataframe): sample data in the format of pandas dataframe
                i.e. pd.DataFrame({'feature': [x], 'qos_value': [j], 'price': [get_price(request_body), ...]})

        """

        slo_type = get_slo_type(request_body['appName'])

        dfs = []
        for data in request_body['data']:
            j1 = BayesianOptimizerPool._objective_perf_over_cost(data)
            j2 = BayesianOptimizerPool._objective_cost_satisfies_slo(data)
            j3 = BayesianOptimizerPool._objective_perf_satisfies_slo(data)

            instance_type = data['instanceType']
            features = encode_instance_type(instance_type)
            qos_value = data['qosValue']
            cost = compute_cost(get_price(instance_type), slo_type, qos_value)
            df = pd.DataFrame({'feature': [features], 'qos_value': [qos_value],
                               'cost': [cost], 'slo_type': [slo_type],
                               'objective_perf_over_cost': [j1], 'objective_cost_satisfies_slo': [j2],
                               'objective_perf_satisfies_slo': [j3]})
            dfs.append(df)

        return pd.concat(dfs)
