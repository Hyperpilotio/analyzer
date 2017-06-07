import pandas as pd
import numpy as np
from django.conf import settings
from pymongo import MongoClient

# still in a mess, code is highly dependent on the database schema


def find_all(collection, filt, database=settings.METRIC_DB):
    """ A wrapper for find_all.
    """
    try:
        client = MongoClient(settings.DATABASE_URL, waitQueueTimeoutMS=200)
        db = client[database]
        db.authenticate(settings.USER, settings.PWD, source=database)
        documents = db[collection].find(filt)
    except Exception as e:
        raise e
    else:
        return documents


def find_one(collection, filt, database=settings.METRIC_DB):
    """ A wrapper for find_all.
    """
    try:
        client = MongoClient(settings.DATABASE_URL, waitQueueTimeoutMS=200)
        db = client[database]
        db.authenticate(settings.USER, settings.PWD, source=database)
        document = db[collection].find_one(filt)
    except Exception as e:
        raise e
    else:
        return document


def get_available_apps(collection):
    try:
        # TODO: inefficient?
        documents = find_all(collection=collection, filt={})
        apps = [i['appName'] for i in documents] if documents != None else []
    except Exception as e:
        raise e
    else:
        return apps


def create_profiling_dataframe(app_name):
    """ Create a dataframe of features.
    Args:
        app_name(str): Map to the 'appName' in Mongo database.
    Returns:
        df(pandas dataframe): Dataframe with rows of features, where each row is a service.
        (i.e. if an app has N services, where each service has K dimensions, the dataframe would be NxK)
    """
    try:
        filt = {'appName': app_name}
        app = find_one(collection='profiling', filt=filt)
        if app == None:
            raise KeyError(
                'Cannot find document: filter={}'.format(filt))
        service_names = pd.Index(app['services'])
        benchmark_names = pd.Index(app['benchmarks'])

        # make dataframe
        ibench_scores = []
        for service in service_names:
            {'appName': app_name, 'serviceInTest': service}
            app = find_one(collection='profiling', filt=filt)
            if app == None:
                raise KeyError(
                    'Cannot find document: filter={}'.format(filt))
            ibench_scores.append([i['toleratedInterference']
                                  for i in app['testResult']])
        df = pd.DataFrame(data=np.array(ibench_scores),
                          index=service_names, columns=benchmark_names)
    except Exception as e:
        raise e
    else:
        return df


def get_services(app_name):
    try:
        filt = {'appName': app_name}
        app = find_one(collection='profiling', filt=filt)
        if app == None:
            raise KeyError(
                'Cannot find document: filter={}'.format(filt))
        service_names = app['services']
    except Exception as e:
        raise e
    else:
        return service_names


def get_calibration_document(app_name):
    try:
        filt = {'appName': app_name}
        document = find_one(collection='calibration', filt=filt)
        if document == None:
            raise KeyError(
                'Cannot find document: filter={}'.format(filt))
    except Exception as e:
        raise e
    else:
        return document
