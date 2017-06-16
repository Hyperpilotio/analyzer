# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
        print 'Creating django client'
        self.client = Client()

    def testPrediction(self):
        try:
            print 'Getting database {}'.format(settings.METRIC_DB)
            mongoClient = MongoClient(
                settings.DATABASE_URL, waitQueueTimeoutMS=200)
            db = mongoClient[settings.METRIC_DB]
            status = db.authenticate(
                settings.USER, settings.PWD, source=settings.METRIC_DB)
            print 'Auth stats: {}'.format(status)
            print 'Setting up test documents'
            testFiles = [i for i in os.listdir(
                settings.BASE_DIR + '/common/testProfiles') if '.json' in i]
            for i in testFiles:
                print "Adding: {}".format(i)
                with open(settings.BASE_DIR + '/common/testProfiles/' + i, 'r') as f:
                    doc = json.load(f)
                    db[TEST_COLLECTION].insert(doc)
            response = self.client.post('/crossApp/predict/',
                                        data=json.dumps(
                                            predictSampleRequest()),
                                        content_type="application/json")
            self.assertEquals(response.status_code, 200, response)
            data = json.loads(response.content)

            print '====Request===='
            print predictSampleRequest()
            print ''
            print '====Cross-App Interference Score Prediction===='
            print pd.read_json(response.content)
        except Exception as e:
            raise e
        finally:
            print 'Clean up test collection: {}'.format(TEST_COLLECTION)
            db[TEST_COLLECTION].drop()
            mongoClient.close()
            print ''
            print 'Done. close connection'


def predictSampleRequest():
    return {'app1': 'testApp',
            'app2': 'testApp2',
            'model': 'LinearRegression1',
            'collection': TEST_COLLECTION}
