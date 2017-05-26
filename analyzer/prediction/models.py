# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings

import sklearn
from django.db import models
from pymongo import MongoClient


def dummy_model():
    # get database client
    client = connect_database()
    # get data
    digits = sklearn.datasets.load_digits()
    # compute
    result = {"dummy": "yummy"}
    # response
    return result


def connect_database(url=settings.DATABASE_ADDRESS):
    db_client = MongoClient(url)

    return db_client
