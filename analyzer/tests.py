# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import json
import pandas as pd
import numpy as np
from unittest import TestCase
from time import sleep
from pathlib import Path
from api_service.app import app as api_service_app
from api_service.db import metricdb, configdb
from analyzer.bayesian_optimizer_pool import BayesianOptimizerPool
from analyzer.bayesian_optimizer import get_candidate
from logger import get_logger

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

    # def testFlowSingleCient(self):
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
        df = encode(rawdata)  # convert request to rawdata

        # Feature
        feature = np.array(df['feature'])
        # Objective values
        objective_perf_over_cost = np.array(df['objective_perf_over_cost'])
        objective_cost_satisfies_slo = np.array(
            df['objective_cost_satisfies_slo'])
        objective_perf_satisfies_slo = np.array(
            df['objective_perf_satisfies_slo'])
        # Set the boundary of encoded feature space. (to be implemented)
        bounds = get_bounds()

        outputs = []
        for j in [objective_perf_over_cost, objective_cost_satisfies_slo, objective_perf_satisfies_slo]:
            output = get_candidate(features, j, bounds)
            outputs.append(output)
        # The final result of instance_type (i.e. [x2.large, x2.xlarge, t2.xlarge])
        candidates = [decode(output) for output in outputs]
    
    def testSingleton(self):
        # TODO: Test if the singleton works in multiprocess
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
        logger.debug(candidate)

    def testGetCandidateCEIAnaltric(self):
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
        logger.debug(candidate)

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
        logger.debug(candidate)



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
            testFiles = (Path(__file__).parent /
                         'test_profiling_result').rglob('*.json')
            for path in testFiles:
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
