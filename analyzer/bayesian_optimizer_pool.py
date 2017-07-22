import threading
import logging
import numpy as np
import pandas as pd
log = logging.getLogger(__name__)
from sklearn.feature_extraction import DictVectorizer
from .bayesian_optimizer import get_candidates
from concurrent.futures import ProcessPoolExecutor
from api_service.db import configdb
log.setLevel(logging.DEBUG)


class BayesianOptimizerPool(object):
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

    def update_sample_map(self, app_id, raw_data):
        # TODO: thread safe?
        # Init empty
        if not self.sample_map.get(app_id):
            self.sample_map[app_id] = pd.DataFrame(
                columns=['feature', 'qos_value ', 'price', 'slo_type', 'duration'])

        dfs = self.encode(raw_data)
        self.sample_map[app_id].append(dfs)

    def get_candidates(self, app_id, raw_data):
        # update the shared sample place holder
        self.update_sample_map(app_id, raw_data)

        X, y = np.array(self.sample_map[app_id]['feature']), np.array(
            self.sample_map[app_id]['qos_value'])
        bounds = get_bounds()

        future = self.worker_pool.submit(
            get_candidates,
            X,
            y,
            bounds
        )
        self.future_map[app_id] = future

    def get_bounds(self):
        pass

    def get_status(self, app_id):
        if self.future_map.get(app_id):
            future = self.future_map.get(app_id)
            if future.running():
                return {"Status": "Running"}
            elif future.cancelled():
                return {"Status": "Cancelled"}
            elif future.done():
                try:
                    candidates = future.result()
                except Exception as e:
                    return {"Status": "Exception", "Exception": str(e)}
                else:
                    return {"Status": "Done", "instance_type": list(map(lambda x: self.decode(x), candidates))}
            else:
                return {"Status": "Unexpected future state"}
        else:
            return {"Status": "Not running"}

    # TODO: get the price(dollar per unit time) of an instance_type from database
    def get_price(self, instance_type):
        return 6.

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

    # TODO: implement this
    def encode(self, raw_data, objective='perf_over_cost'):
        """ Convert raw_data to dataframe.
        Args:
                raw_data(dict): raw data sent from workload profiler.
        Returns:
                df(dataframe): pandas dataframe in the format
                i.e. pd.DataFrame({'feature': [x], 'qos_value': [j], 'price': [get_price(raw_data), ...]})

        """
        dfs = []
        for data in raw_data['data']:
            if objective == 'perf_over_cost':
                j = self._objective_perf_over_cost(data)
            elif objective == 'cost_satisfies_slo':
                j = self._objective_cost_satisfies_slo(data)
            elif objective == 'perf_satisfies_slo':
                j = self._objective_perf_satisfies_slo(data)

            node_instance = configdb.nodetypes.find_one({'name': data['instanceType']})['name']
            x = np.random.rand(8)
            df = pd.DataFrame({'feature': [x], 'qos_value': [j], 'price': [
                self.get_price(data)], 'slo_type': ['latency'], 'duration': [253]})
            dfs.append(df)

        return pd.concat(dfs)

    # TODO: implement this
    def decode(self, feature):
        return 'x2.large'
