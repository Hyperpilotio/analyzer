# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.test import TestCase, Client

class BasicTest(TestCase):

    def setUp(self):
        self.client = Client()


    def testEcho(self):
        response = self.client.post('/common/echo/',
                                    data=json.dumps({
                                        'echo': 'ohce'
                                    }),
                                    content_type="application/json")
        data = json.loads(response.content)

        self.assertEquals(response.status_code, 200, response)
        self.assertEquals(data['echo'], 'ohce')

    def testConnectToDB(self):
        response = self.client.get('/common/connectToDB/')

        self.assertEquals(response.status_code, 200, response)
