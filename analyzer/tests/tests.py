# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.test import TestCase
from django.test import Client


class BasicTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_echo(self):
        response = self.client.post('/tests/echo/',
                                    data=json.dumps({
                                        'echo': 'ohce'
                                    }),
                                    content_type="application/json")
        data = json.loads(response.content)

        self.assertEquals(response.status_code, 200)
        self.assertEquals(data['echo'], 'ohce')

    def test_connect_db(self):
        response = self.client.get('/tests/connect_db/')

        self.assertEquals(response.status_code, 200)
