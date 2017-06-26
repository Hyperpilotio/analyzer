# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
log = logging.getLogger(__name__)
import json
import os
import pandas as pd
import common.mongoUtil as mu
from pymongo import MongoClient
from django.test import TestCase, Client
from django.conf import settings


TEST_COLLECTION = 'test-collection'


class PredictionTest(TestCase):

    def setUp(self):
        log.debug('Creating django client')
        self.client = Client()

    def testPrediction(self):
        try:
            log.debug('Getting database {}'.format(settings.METRIC_DB))
            mongoClient = MongoClient(
                settings.DATABASE_URL, waitQueueTimeoutMS=200)
            db = mongoClient[settings.METRIC_DB]
            status = db.authenticate(
                settings.USER, settings.PWD, source=settings.METRIC_DB)
            log.debug('Auth stats: {}'.format(status))
            log.debug('Setting up test documents')
            testFiles = [i for i in os.listdir(
                settings.BASE_DIR + '/crossApp/testProfiles') if '.json' in i]
            for i in testFiles:
                log.debug("Adding: {}".format(i))
                with open(settings.BASE_DIR + '/crossApp/testProfiles/' + i, 'r') as f:
                    doc = json.load(f)
                    db[TEST_COLLECTION].insert(doc)
            response = self.client.post('/crossApp/predict/',
                                        data=json.dumps(
                                            predictSampleRequest()),
                                        content_type="application/json")
            self.assertEquals(response.status_code, 200, response)
            data = json.loads(response.content)

            log.debug('====Request====')
            log.debug('\n{}'.format(predictSampleRequest()))

            log.debug('====Cross-App Interference Score Prediction====')
            log.debug('\n{}'.format(pd.read_json(response.content)))
        except Exception as e:
            raise e
        finally:
            log.debug('Clean up test collection: {}'.format(TEST_COLLECTION))
            db[TEST_COLLECTION].drop()
            mongoClient.close()
            log.debug('client connection closed')


def predictSampleRequest():
    return {'app1': 'testApp',
            'app2': 'testApp2',
            'model': 'LinearRegression1',
            'collection': TEST_COLLECTION}
