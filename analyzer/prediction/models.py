# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings

from sklearn.datasets import load_digits
from django.db import models
from pymongo import MongoClient


def dummy_model():
    # get database client
    client = connect_database()
    # # get data
    digits = load_digits()
    # compute
    result = {"dummy": "yummy"}
    # response
    return result


def connect_database(url=settings.DATABASE_ADDRESS):
    db_client = MongoClient(url)

    return db_client
