# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
log = logging.getLogger(__name__)
import json
import os
import pandas as pd
from unittest import TestCase
from time import sleep
from pathlib import Path
from api_service.app import app as api_service_app
from api_service.db import metricdb, configdb
from analyzer.bayesian_optimizer_pool import BayesianOptimizerPool
from analyzer.bayesian_optimizer import guess_best_trials

log.setLevel(logging.DEBUG)


class BayesianOptimizationTest(TestCase):

    def setUp(self):
        log.debug('Creating flask clients')
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

    def testFlowSingleCient(self):
        fake_uuid = "8whe-weui-qjhf-38os"
        response = json.loads(self.client.post('/get-next-instance-type/' + fake_uuid,
                                               data=json.dumps(self.getTestRequest()),
                                               content_type="application/json").data)
        log.debug(f"Response from posting request: {self.getTestRequest()}")
        log.debug(response)

        while True:
            response = json.loads(self.client.get(
                "/get-optimizer-status/" + fake_uuid).data)
            log.debug("Response after sending GET /get-optimizer-status")
            log.debug(response)

            if response['Status'] == 'Running':
                log.debug("Waiting for 5 sec")
                sleep(5)
            else:
                break

    def testGuessBestTrialsDirect(self):
        import numpy as np
        # dimension=7, nsamples=2
        result = guess_best_trials(np.array([[6, 9, 9, 0, 8, 0, 9], [
            9, 8, 8, 0, 8, 5, 8]]), np.array([0.8, 0.7]), [(0, 1)] * 7)
        log.debug(result)


class PredictionTest(TestCase):

    def setUp(self):
        log.debug('Creating flask client')
        self.client = api_service_app.test_client()
        self.test_collection = 'test-collection'

    def getTestRequest(self):
        return {'app1': 'testApp',
                'app2': 'testApp2',
                'model': 'LinearRegression1',
                'collection': self.test_collection}

    def testFlow(self):
        try:
            log.debug(f'Getting database {metricdb.name}')
            db = metricdb._get_database()  # This triggers lazy-loading
            log.debug('Setting up test documents')
            testFiles = (Path(__file__).parent /
                         'test_profiling_result').rglob('*.json')
            for path in testFiles:
                log.debug("Adding: {}".format(path))
                with path.open('r') as f:
                    doc = json.load(f)
                    db[self.test_collection].insert_one(doc)
            response = self.client.post('/cross-app/predict',
                                        data=json.dumps(
                                            self.getTestRequest()),
                                        content_type="application/json")
            self.assertEqual(response.status_code, 200, response)
            data = json.loads(response.data)

            log.debug('====Request====\n')
            log.debug(self.getTestRequest())
            log.debug('\n====Cross-App Interference Score Prediction====')
            log.debug('\n' + str(pd.read_json(response.data)))
        except Exception as e:
            raise e
        finally:
            log.debug(f'Clean up test collection: {self.test_collection}')
            db[self.test_collection].drop()
            db.client.close()
            log.debug('Client connection closed')
