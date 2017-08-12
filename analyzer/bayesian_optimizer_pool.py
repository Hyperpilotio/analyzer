from __future__ import division, print_function

import threading
import numpy as np
from .bayesian_optimizer_session import BayesianOptimizerSession


class BayesianOptimizerPool():
    """ This class manages Bayesian optimizer session objects """
    __singleton_lock = threading.Lock()
    __singleton_instance = None

    @classmethod
    def instance(cls):
        """ The singleton instance of BayesianOptimizerSession """
        if not cls.__singleton_instance:
            with cls.__singleton_lock:
                if not cls.__singleton_instance:
                    cls.__singleton_instance = cls()
        return cls.__singleton_instance

    def __init__(self):
        # store the bayesian optimizer session objects
        self.session_map = {}

    def get_candidates(self, session_id, request_body, **kwargs):
        bo_session = self.get_session(session_id)
        return bo_session.get_candidates(request_body, **kwargs)

    def get_status(self, session_id):
        bo_session = bo_session = self.get_session(session_id)
        return bo_session.get_status()

    def get_session(self, session_id):
        with self.__singleton_lock:
            bo_session = self.session_map.get(session_id)
            if bo_session is not None:
                return bo_session
            else:
                self.session_map[session_id] = BayesianOptimizerSession(
                    session_id)
                return self.session_map[session_id]
