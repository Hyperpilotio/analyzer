from __future__ import division, print_function

import threading
import numpy as np
from .bayesian_optimizer_session import BayesianOptimizerSession

class BayesianOptimizerPool():
    def __init__(self):
        # store the bayesian optimizer session objects
        self._create_lock = threading.Lock()
        self.session_map = {}

    def get_candidates(self, session_id, request_body):
        bo_session = self.get_session(session_id)
        return bo_session.get_candidates(request_body['appName'], request_body['data'])

    def get_status(self, session_id):
        bo_session = self.get_session(session_id)
        return bo_session.get_status()

    def get_session(self, session_id):
        with self._create_lock:
            session = self.session_map.get(session_id)
            if not session:
                session = BayesianOptimizerSession(session_id)
                self.session_map[session_id] = session
        return session
