import threading
import numpy as np
import logging
log = logging.getLogger(__name__)
from sklearn.feature_extraction import DictVectorizer
from .bayesian_optimizer import guess_best_trials
from concurrent.futures import ProcessPoolExecutor
from api_service.db import configdb



log.setLevel(logging.DEBUG)


def hash_list(l):
    assert type(l) is list, f"input type of {l}: {type(l)} is not list"
    return hash(tuple(l))


class BayesianOptimizerPool(object):
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
        self.sample_map = {}
        self.future_map = {}
        self.worker_pool = ProcessPoolExecutor(max_workers=16)
        v = DictVectorizer(sparse=False)
        # TODO: Currently only choose cpuconfig
        configs = [i['cpuConfig']
                   for i in configdb.nodetypes.find({}, {'_id': 0})]
        names = [i['name'] for i in configdb.nodetypes.find({}, {'_id': 0})]

        self.feature_encoder, self.feature_decoder = {}, {}
        X = v.fit_transform(configs)
        for i, j in zip(names, X):
            self.feature_encoder[i] = j
            self.feature_decoder[hash_list(list(j))] = i

        log.debug("feature_encoder")
        log.debug(self.feature_encoder)
        log.debug("feature_decoder")
        log.debug(self.feature_decoder)

    def guess_best_trials(self, app_id, raw_data):
        if not self.sample_map.get(app_id):
            self.sample_map[app_id] = ([], [])

        for data in raw_data['data']:
            input_vector, target_value = self.encode(data)
            self.sample_map[app_id][0].append(input_vector)
            self.sample_map[app_id][1].append(target_value)

        # self.sample_map[app_id][0] = np.array(self.sample_map[app_id][0])

        X, y = np.array(self.sample_map[app_id][0]), np.array(
            self.sample_map[app_id][1])
        bounds = [(0, 1)] * X.shape[1]
        log.debug(f"X: {X}")
        log.debug(f'y: {y}')
        # TODO: compute bonuds of input_vector
        log.debug(f"Bounds: {bounds}")
        log.debug(bounds)
        future = self.worker_pool.submit(
            guess_best_trials,
            X,
            y, bounds
        )
        self.future_map[app_id] = future

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

    # TODO: get the price(dollar per unit time) of an instance_type
    def get_price(self, instance_type):
        return 6.

    def encode(self, data):
        """ Extract input feature vector and objective value.
        Args:
                raw_data(dict): raw data sent from workload profiler.
        Returns:
                x (np.array): feature
                y (float): objective_value

        """
        # TODO: design the feature encoding and objective function
        # Is the objective funrtion varies from app to app, client to client?

        node_instance = configdb.nodetypes.find_one(
            {'name': data['instanceType']})['name']
        x = self.feature_encoder[node_instance]
        y = np.random.rand(1)[0]

        return x, y

    def decode(self, input_vector):
        return self.feature_decoder[hash_list(list(input_vector))]
