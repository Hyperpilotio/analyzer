# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from sklearn.datasets import load_digits
from django.db import models
from pymongo import MongoClient


def dummy_model(test_id):
    # Connect to database
    client = MongoClient(settings.DATABASE_URL)

    metric_db = client[settings.METRIC_DB]
    metric_db.authenticate(settings.USER, settings.PWD,
                           source=settings.METRIC_DB)

    try:
        app_feature_dims = [i['benchmark'] for i in metric_db[
            'profiling'].find_one({'testId': test_id})['testResult']]

        app_feature_value = [i['toleratedInterference'] for i in metric_db[
            'profiling'].find_one({'testId': test_id})['testResult']]

    except Exception as e:
        return {'exception': str(e)}

    else:
        return {'test_id': test_id, 'feature_dims': app_feature_dims, 'feature_values': app_feature_value}
