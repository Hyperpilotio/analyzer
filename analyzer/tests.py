# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from pathlib import Path
from time import sleep
from unittest import TestCase

import numpy as np
import pandas as pd
from bayes_opt import BayesianOptimization as BO_ref
from sklearn.gaussian_process.kernels import Matern
from concurrent.futures import ThreadPoolExecutor

from analyzer.bayesian_optimizer import (UtilityFunction, get_candidate,
                                         get_fitted_gaussian_processor)
from analyzer.bayesian_optimizer_pool import BayesianOptimizerPool as BOP
from api_service.app import app as api_service_app
from api_service.db import metricdb
from logger import get_logger

from .util import decode_nodetype, get_all_nodetypes, get_feature_bounds, encode_nodetype

logger = get_logger(__name__, log_level=("TEST", "LOGLEVEL"))


class BayesianOptimizerPoolTest(TestCase):
    def setUp(self):
        logger.debug('Creating flask clients')
        self.client = api_service_app.test_client()

    def testBayesianOptimizerPoolFlow(self):
        """ 2 sample was submitted by client through API
        """
        uuid = "hyperpilot-sizing-demo-1234-horray"
        request_body = {
            "appName": "redis",
            "data": [
                {"instanceType": "t2.large",
                 "qosValue": 200.
                 },
                {"instanceType": "m4.large",
                 "qosValue": 100.
                 }
            ]}
        # Sending request
        logger.debug(f'Sending request to API service:\n{request_body}')
        response = json.loads(self.client.post(f'/apps/{uuid}/suggest-instance-types',
                                               data=json.dumps(request_body),
                                               content_type="application/json").data)

        logger.debug(f"Response:\n{response}")
        self.assertEqual(response['status'], 'success', response)

        # Polling from workload profiler
        while True:
            logger.debug('Polling status from API service')
            response = json.loads(self.client.get(f'/apps/{uuid}/get-optimizer-status').data)
            logger.debug(f'Response:\n{response}')

            if response['status'] == 'running':
                logger.debug("Waiting for 1 sec")
                sleep(1)
            else:
                break

        self.assertEqual(response['status'], "done", response)

    def testCherryPickWorkFlow(self):
        """ Test Cherry pick workflow without testing multiprocrss pool functionality.
            nput: 3 training sample from workload profiller
            Output: 0~3 candidates for next run, number of candidates depends on the terminate condition
        """
        # Request body constains 2 input samples
        request_body = {
            "appName": "redis",
            "data": [
                {"instanceType": "t2.large",
                 "qosValue": 200.
                 },
                {"instanceType": "m4.large",
                 "qosValue": 100.
                 }
            ]}

        df = BOP.create_sample_dataframe(request_body)
        training_data_list = [BOP.make_optimizer_training_data(df, objective_type=o)
                              for o in ['perf_over_cost', 'cost_given_perf_limit', 'perf_given_cost_limit']]

        bounds = get_feature_bounds(normalized=True)
        outputs = []
        for t in training_data_list:
            logger.debug(f"Dispatching training data: {t}")
            acq = 'cei' if t.has_constraint() else 'ei'
            output = get_candidate(t.feature_mat, t.objective_arr, bounds,
                                   acq=acq, constraint_arr=t.constraint_arr,
                                   constraint_upper=t.constraint_upper, **{'standardize_y': False})
            outputs.append(output)

        # The final result of nodetype (i.e. [x2.large, x2.xlarge, t2.xlarge])
        candidates = [decode_nodetype(output) for output in outputs]
        logger.debug(candidates)

    def testSingleton(self):
        pool = ThreadPoolExecutor(40)
        future_list = [pool.submit(BOP.instance) for i in range(100000)]
        instances = [f.result() for f in future_list]
        self.assertEqual(len(set(instances)), 1,
                         "Only one instance should be created")
        del pool

    def testUpdateSampleMap(self):
        bop = BOP.instance()
        pool = ThreadPoolExecutor(40)
        app_id = 'hyperpilot'

        future_list, total = [], 0
        for i in range(1000):
            df = pd.DataFrame({"nodetype": [i]})
            future_list.append(pool.submit(
                bop.update_sample_map, app_id, df))
            total += i

        while any(f.running() for f in future_list):
            sleep(1)

        self.assertEqual(
            sum(bop.sample_map[app_id]['nodetype']), total, "Race condition detected")

        del pool

    def testGenerateInitialPoints(self):
        dataframe = pd.DataFrame.from_dict(list(get_all_nodetypes().values()))
        nodetype_map = {}

        for _, j in dataframe.iterrows():
            nodetype_map[j['name']] = j['instanceFamily']

        for i in range(100):
            samples = BOP.generate_initial_samples(
                len(set(dataframe['instanceFamily'])))
            if len(samples) != len(set([nodetype_map[i] for i in samples])):
                raise AssertionError(
                    "Initial samples coming from same instance families")

    def testPsudoGenerator(self):
        all_nodetype = ['a', 'b', 'c', 'd', 'e']
        dfs = [pd.DataFrame({'nodetype': [f'{i}']}) for i in all_nodetype[:-2]]
        df = pd.concat(dfs)

        # draw 100 times s
        for i in range(100):
            assert BOP.psudo_random_generator(
                all_nodetype, df) in all_nodetype[-2:]
        
        # draw 100 times s
        for i in range(100):
            assert BOP.psudo_random_generator(
                all_nodetype, df) not in all_nodetype[:-2]


class BayesianOptimizerTest(TestCase):

    def testGetCandidateEIFlow(self):
        """ Flow dummy data through get_candidate with acquisition = ei
        """
        # Preparing dummy data
        n_dimension, n_sample = 5, 4
        lo, hi = 0, 1

        X_train, y_train, c_train = np.random.rand(
            n_sample, n_dimension), np.random.rand(n_sample), np.random.rand(n_sample)
        bounds = [(lo, hi)] * n_dimension  # boundary for of searching space

        # Test with EI acquisition
        candidate = get_candidate(X_train, y_train, bounds, acq='ei')
        logger.debug(f"argmax of acquisition EI:\n {candidate}")

    def testGetCandidateConstrainedEIFlow(self):
        """ Flow dummy data through get_candidate with acquisition = cei
        """
        # Preparing dummy data
        n_dimension, n_sample = 5, 4
        lo, hi = 0, 1

        X_train, y_train, c_train = np.random.rand(
            n_sample, n_dimension), np.random.rand(n_sample), np.random.rand(n_sample)
        bounds = [(lo, hi)] * n_dimension  # boundary for of searching space

        # Test with CEI_numeric acquisition
        candidate = get_candidate(X_train, y_train, bounds, 'cei',
                                  constraint_arr=c_train, constraint_upper=2.)
        logger.debug(f"argmax of acquisition cei:\n{candidate}")

    def testReferenceImplementation(self):
        """ Check for numeric correctness against reference implementation
        """
        def f(x):
            return np.exp(-(x - 2)**2) + np.exp(-(x - 6)**2 / 10) + 1 / (x**2 + 1)

        def posterior(gp, x):
            mu, sigma = gp.predict(x, return_std=True)
            return mu, sigma
        # Generate trainning data
        x = np.linspace(-2, 10, 10000).reshape(-1, 1)
        y = f(x)
        X_train = np.array([0, 4])
        y_train = f(X_train)
        rand_seed = 0

        gp_params = {"alpha": 1e-5, "n_restarts_optimizer": 25,
                     "kernel": Matern(nu=2.5), "random_state": rand_seed}

        # Reference implementation
        optimizer = BO_ref(f, {'x': (-2, 10)}, verbose=0)
        # append trainning data
        optimizer.explore({'x': X_train})
        # fit gaussian process regressor
        optimizer.maximize(init_points=0, n_iter=0,
                           acq='ei', xi=1e-4, **gp_params)
        # get results
        mu_ref, std_ref = posterior(optimizer.gp, x)
        utility_ref = optimizer.util.utility(
            x, optimizer.gp, optimizer.Y.max())

        # Testing implementation
        gp = get_fitted_gaussian_processor(
            X_train.reshape(2, -1), y_train, standardize_y=False, **gp_params)
        util = UtilityFunction(kind='ei', gp_objective=gp, xi=1e-4)

        mu_impl, std_impl = posterior(gp, x)
        utility_impl = util.utility(x)

        assert (mu_ref == mu_impl).all(),\
            "mu(x) comparison failed"
        assert (std_ref == std_impl).all(),\
            "std(x) comparison failed"
        assert (utility_ref == utility_impl).all(),\
            "utility(x) comparison failed"

    def testReferenceImplementation3D(self):
        """ Check for numeric correctness against reference implementation
        """
        def f(x):  # vector version
            return np.exp(-(x[0] - 2)**2) + np.exp(-(x[0] - 6)**2 / 10) + \
                1 / (x[0]**2 + 1) + np.sin(x[1]) + 5 * np.cos(6.42 * x[2])

        def ff(x, y, z):  # variable version
            return np.exp(-(x - 2)**2) + np.exp(-(x - 6)**2 / 10) + \
                1 / (x**2 + 1) + np.sin(y) + 5 * np.cos(6.42 * z)

        def posterior(gp, x):
            mu, sigma = gp.predict(x, return_std=True)
            return mu, sigma
        bounds = np.array([[-5, 5]] * 3)

        # Generate trainning data
        np.random.seed(6)
        X = np.random.uniform(bounds[:, 0], bounds[:, 1],
                              size=(1000, bounds.shape[0]))
        w = [f(x) for x in X]

        np.random.seed(6)
        X_train = np.random.uniform(bounds[:, 0], bounds[:, 1],
                                    size=(3, bounds.shape[0]))
        y_train = [f(x) for x in X_train]
        rand_seed = 0

        gp_params = {"alpha": 1e-5, "n_restarts_optimizer": 25,
                     "kernel": Matern(nu=2.5), "random_state": rand_seed}

        # Reference implementation
        optimizer = BO_ref(
            ff, {'x': (-5, 5), 'y': (-5, 5), 'z': (-5, 5)}, verbose=0)
        # append trainning data
        optimizer.explore(
            {'x': X_train[:, 0], 'y': X_train[:, 1], 'z': X_train[:, 2]})
        # fit gaussian process regressor
        optimizer.maximize(init_points=0, n_iter=0,
                           acq='ei', xi=1e-4, **gp_params)
        # get results
        post = np.array([posterior(optimizer.gp, x.reshape(1, -1)) for x in X])
        mu_ref, std_ref = post[:, 0], post[:, 1]

        utility_ref = optimizer.util.utility(
            X, optimizer.gp, optimizer.Y.max())

        # Testing implementation
        gp = get_fitted_gaussian_processor(
            np.array(X_train), np.array(y_train), standardize_y=False, **gp_params)
        util = UtilityFunction(kind='ei', gp_objective=gp, xi=1e-4)

        post_impl = np.array([posterior(gp, x.reshape(1, -1)) for x in X])
        mu_impl, std_impl = post_impl[:, 0], post_impl[:, 1]
        utility_impl = util.utility(X)

        assert (mu_ref == mu_impl).all(),\
            "mu(x) comparison failed"
        assert (std_ref == std_impl).all(),\
            "std(x) comparison failed"
        assert (utility_ref == utility_impl).all(),\
            "utility(x) comparison failed"


class PredictionTest(TestCase):

    def setUp(self):
        logger.debug('Creating flask client')
        self.client = api_service_app.test_client()
        self.test_collection = 'test-collection'

    def testPredictionFlow(self):
        try:
            request_body = {'app1': 'testApp',
                            'app2': 'testApp2',
                            'model': 'LinearRegression1',
                            'collection': self.test_collection}
            logger.debug(f'Getting database {metricdb.name}')
            db = metricdb._get_database()  # This triggers lazy-loading
            logger.debug('Setting up test documents')
            test_files = (Path(__file__).parent /
                          'test_profiling_result').rglob('*.json')
            for path in test_files:
                logger.debug("Adding: {}".format(path))
                with path.open('r') as f:
                    doc = json.load(f)
                    db[self.test_collection].insert_one(doc)
            response = self.client.post('/cross-app/predict',
                                        data=json.dumps(
                                            request_body),
                                        content_type="application/json")
            self.assertEqual(response.status_code, 200, response)
            data = json.loads(response.data)

            logger.debug('====Request====\n')
            logger.debug(request_body)
            logger.debug('\n====Cross-App Interference Score Prediction====')
            logger.debug('\n' + str(pd.read_json(response.data)))
        except Exception as e:
            raise e
        finally:
            logger.debug(f'Clean up test collection: {self.test_collection}')
            db[self.test_collection].drop()
            db.client.close()
            logger.debug('Client connection closed')


class UtilTest(TestCase):
    def testGetBounds(self):
        pass

    def testGetFeatureBoundsNorm(self):
        pass

    def testDeEncoder(self):
        """ decode(encode(x) should be itself)
        """
        # TODO: Have a better way to test the decoder as the decoded types is expected to not match the encoded.
        # for n in get_all_nodetypes():
        #    logger.debug(f"deeencoded: {decode_nodetype(encode_nodetype(n))}, origin: {n}")
        #    if decode_nodetype(encode_nodetype(n)) != n:
        #        logger.warning(f"deencoded: {decode_nodetype(encode_nodetype(n))}, origin: {n} not consistent")
