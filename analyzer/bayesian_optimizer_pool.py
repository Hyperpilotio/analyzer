import threading
from bayesian_optimizer import guess_best_trials
from concurrent.futures import ProcessPoolExecutor


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

    def guess_best_trials(self, app_id, raw_data_list):
        if self.sample_map.get(app_id):
            past_samples = self.sample_map.get(app_id)
        else:
            self.sample_map[app_id] = {}
            self.sample_map[app_id]['X'] = []
            self.sample_map[app_id]['y'] = []

        for raw_data in raw_data_list:
            X, y = encode_data(raw_data)
            self.sample_map[app_id]['X'].append(X)
            self.sample_map[app_id]['y'].append(y)

        future = self.worker_pool.submit(
            guess_best_trials,
            self.sample_map[app_id]['X'],
            self.sample_map[app_id]['y'],
            [(None, None)])  # TODO: compute bonuds of X

        self.future_map['app_id'] = future

    def get_status(self, app_id):
        if self.future_map.get(app_id):
            future = self.future_map.get(app_id)
            if future.running():
                return {"Status": "Running"}
            elif future.cancelled():
                return {"Status": "Cancelled"}
            elif future.done():
                return {"Status": "Done", "Data": decode_result(future.result())}
        else:
            return {"Status": "Not running"}

    def encode_data(raw_data):
        """ Extract feature vector and objective value.
        Args:
                raw_data(dict): raw data sent from workload profiler.
        Returns:
                X (np.array): feature
                y (float): objective_value

        """
        # TODO: parse the data
        X, y = None, None

        return X, y

    def decode_result(result):

        return None
