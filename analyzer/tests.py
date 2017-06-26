# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
log = logging.getLogger(__name__)
import json
import os
import pandas as pd
from pymongo import MongoClient
from pathlib import Path
from api_service.app import app as api_service_app
from api_service.db import metricdb, configdb
from unittest import TestCase


TEST_COLLECTION = 'test-collection'


class PredictionTest(TestCase):

    def setUp(self):
        log.debug('Creating flask client')
        self.client = api_service_app.test_client()

    def testPrediction(self):
        try:
            log.debug(f'Getting database {metricdb.name}')
            db = metricdb._get_database() # This triggers lazy-loading
            log.debug('Setting up test documents')
            testFiles = (Path(__file__).parent / 'testProfiles').rglob('*.json')
            for path in testFiles:
                log.debug("Adding: {}".format(path))
                with path.open('r') as f:
                    doc = json.load(f)
                    db[TEST_COLLECTION].insert_one(doc)
            response = self.client.post('/cross-app/predict',
                                        data=json.dumps(
                                            predictSampleRequest()),
                                        content_type="application/json")
            self.assertEqual(response.status_code, 200, response)
            data = json.loads(response.data)

            log.debug('====Request====\n')
            log.debug(predictSampleRequest())

            log.debug('====Cross-App Interference Score Prediction====\n')
            log.debug(pd.read_json(response.data))
        except Exception as e:
            raise e
        finally:
            log.debug(f'Clean up test collection: {TEST_COLLECTION}')
            db[TEST_COLLECTION].drop()
            db.client.close()
            log.debug('client connection closed')


def predictSampleRequest():
    return {'app1': 'testApp',
            'app2': 'testApp2',
            'model': 'LinearRegression1',
            'collection': TEST_COLLECTION}
