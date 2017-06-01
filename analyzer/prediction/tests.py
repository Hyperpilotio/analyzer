# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import pandas as pd
from django.test import TestCase, Client


class PredictionTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_app2app(self):
        response = self.client.post('/prediction/app2app/',
                                    data=json.dumps(app2app_sample_request()),
                                    content_type="application/json")

        self.assertEquals(response.status_code, 200, response)
        data = json.loads(response.content)

        print '====Request===='
        print app2app_sample_request()
        print
        print '====Cross-App Interference Score Prediction===='
        print pd.read_json(response.content)


def app2app_sample_request():
    return {'app_1': 'testApp',
            'app_2': 'testApp2',
            'model': 'LinearRegression1'}
