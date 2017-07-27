# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from pathlib import Path
from unittest import TestCase

import numpy as np
import pandas as pd
from bayes_opt import BayesianOptimization as BO_ref
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern

from analyzer.bayesian_optimizer import UtilityFunction, get_candidate
from analyzer.bayesian_optimizer_pool import BayesianOptimizerPool as BOP
from api_service.app import app as api_service_app
from api_service.db import configdb, metricdb
from logger import get_logger

from .util import get_bounds

logger = get_logger(__name__, log_level=("TEST", "LOGLEVEL"))


class BayesianOptimizationPoolTest(TestCase):
    def setUp(self):
        logger.debug('Creating flask clients')
        self.client = api_service_app.test_client()
        self.client2 = api_service_app.test_client()

    def getTestRequest(self):
        return {"appName": "redis",
                "data": [
                    {"instanceType": "t2.large",
                     "qosValue": 200.
                     },
                    {"instanceType": "m4.large",
                     "qosValue": 100.
                     }
                ]}

    # def testPoolFlowSingleCient(self):
    #     fake_uuid = "8whe-weui-qjhf-38os"
    #     response = json.loads(self.client.post('/get-next-instance-types/' + fake_uuid,
    #                                            data=json.dumps(self.getTestRequest()),
    #                                            content_type="application/json").data)
    #     logger.debug(f"Response from posting request: {self.getTestRequest()}")
    #     logger.debug(response)

    #     while True:
    #         response = json.loads(self.client.get(
    #             "/get-optimizer-status/" + fake_uuid).data)
    #         logger.debug("Response after sending GET /get-optimizer-status")
    #         logger.debug(response)

    #         if response['Status'] == 'Running':
    #             logger.debug("Waiting for 5 sec")
    #             sleep(5)
    #         else:
    #             break

    def testCherryPickWorkFlow(self):
        """ Test Cherry pick workflow without testing BayesianOptimizationPool 
        """
        rawdata = self.getTestRequest()
        df = BOP.create_sizing_dataframe(rawdata)  # convert request to rawdata

        # Feature
        feature = np.array(df['feature'])
        # Objective values
        objective_perf_over_cost = np.array(
            df['objective_perf_over_cost'])
        objective_cost_satisfies_slo = np.array(
            df['objective_cost_satisfies_slo'])
        objective_perf_satisfies_slo = np.array(
            df['objective_perf_satisfies_slo'])
        # Set the boundary of encoded feature space. (to be implemented)
        bounds = util.get_bounds()

        outputs = []
        for j in [objective_perf_over_cost, objective_cost_satisfies_slo, objective_perf_satisfies_slo]:
            output = get_candidate(features, j, bounds)
            outputs.append(output)

        # The final result of instance_type (i.e. [x2.large, x2.xlarge, t2.xlarge])
        candidates = [decode(output) for output in outputs]

    def testSingleton(self):
        # TODO: Test if the singleton is thread safe
        pass


class BayesianOptimizationTest(TestCase):

    def testGetCandidateEI(self):
        """ Flow dummy data through get_candidate with acquisition = ei
        """
        # Preparing dummy data
        n_dimension, n_sample = 12, 10
        lo, hi = 0, 1

        X_train, y_train, c_train = np.random.rand(
            n_sample, n_dimension), np.random.rand(n_sample), np.random.rand(n_sample)
        bounds = [(lo, hi)] * n_dimension  # boundary for of searching space

        # Test with EI acquisition
        candidate = get_candidate(X_train, y_train, bounds, acq='ei')
        logger.debug(f"argmax of acquisition EI:\n {candidate}")

    def testGetCandidateCEIAnalytic(self):
        """ Flow dummy data through get_candidate with acquisition = cei_analytic
        """
        # Preparing dummy data
        n_dimension, n_sample = 12, 10
        lo, hi = 0, 1

        X_train, y_train, c_train = np.random.rand(
            n_sample, n_dimension), np.random.rand(n_sample), np.random.rand(n_sample)
        bounds = [(lo, hi)] * n_dimension  # boundary for of searching space

        # Test with CEI_analytic acquisition
        candidate = get_candidate(X_train, y_train, bounds, acq='cei_analytic',
                                  constraint=2., constraints=y_train)
        logger.debug(f"argmax of acquisition CEI_analytic:\n{candidate}")

    def testGetCandidateCEINumeric(self):
        """ Flow dummy data through get_candidate with acquisition = cei_numeric
        """
        # Preparing dummy data
        n_dimension, n_sample = 12, 10
        lo, hi = 0, 1

        X_train, y_train, c_train = np.random.rand(
            n_sample, n_dimension), np.random.rand(n_sample), np.random.rand(n_sample)
        bounds = [(lo, hi)] * n_dimension  # boundary for of searching space

        # Test with CEI_numeric acquisition
        candidate = get_candidate(X_train, y_train, bounds, acq='cei_numeric',
                                  constraint=2., constraints=c_train)
        logger.debug(f"argmax of acquisition CEI_numeric:\n{candidate}")

    def oracleTest(self):
        """ Check for correctness with reference implementation
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
        y_train = np.array(list(map(f, X_train)))
        rand_seed = 0

        gp_params = {"alpha": 1e-5, "n_restarts_optimizer": 25,
                     "kernel": Matern(nu=2.5), "random_state": rand_seed}

        # Reference implementation
        bo = BO_ref(f, {'x': (-2, 10)}, verbose=1)
        # append trainning data
        bo.explore({'x': X_train})
        # fit gaussian process regressor
        bo.maximize(init_points=0, n_iter=0, acq='ei',
                    xi=1e-4, **gp_params)
        # get results
        mu_ref, std_ref = posterior(bo.gp, x)
        utility_ref = bo.util.utility(x, bo.gp, bo.Y.max())

        # Testing implementation
        X_train = X_train.reshape(2, -1)
        gp = GaussianProcessRegressor()
        gp.set_params(**gp_params)
        gp.fit(X_train, y_train)
        util = UtilityFunction(kind='ei', xi=1e-4)

        mu_impl, std_impl = posterior(gp, x)
        utility_impl = util.utility(x, gp, y_train.max())

        assert (mu_ref == mu_impl).all(), "mu(x) comparison failed"
        assert (std_ref == std_impl).all(), "std(x) comparison failed"
        assert (utility_ref == utility_impl).all(
        ), "utility(x) comparison failed"


class PredictionTest(TestCase):

    def setUp(self):
        logger.debug('Creating flask client')
        self.client = api_service_app.test_client()
        self.test_collection = 'test-collection'

    def getTestRequest(self):
        return {'app1': 'testApp',
                'app2': 'testApp2',
                'model': 'LinearRegression1',
                'collection': self.test_collection}

    def testFlow(self):
        try:
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
                                            self.getTestRequest()),
                                        content_type="application/json")
            self.assertEqual(response.status_code, 200, response)
            data = json.loads(response.data)

            logger.debug('====Request====\n')
            logger.debug(self.getTestRequest())
            logger.debug('\n====Cross-App Interference Score Prediction====')
            logger.debug('\n' + str(pd.read_json(response.data)))
        except Exception as e:
            raise e
        finally:
            logger.debug(f'Clean up test collection: {self.test_collection}')
            db[self.test_collection].drop()
            db.client.close()
            logger.debug('Client connection closed')
