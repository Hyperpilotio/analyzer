import pandas as pd
import numpy as np
from django.conf import settings
from pymongo import MongoClient


def find_all(collection, filt={}, proj={}, database=settings.METRIC_DB, return_list=False):
    """ A wrapper for 'find' to ensure the connection will be closed.
    Args:
        collection(str): mongoDB collection
        filt(dict): mongoDB filter
        proj(dict): mongoDB projection
        database(str): name of database
    Return:
        documents(cursor): mongoDB cursor 
    """
    try:
        client = MongoClient(settings.DATABASE_URL, waitQueueTimeoutMS=200)
        db = client[database]
        db.authenticate(settings.USER, settings.PWD, source=database)
        documents = db[collection].find(filt)
    except Exception as e:
        raise e
    else:
        return documents if not return_list else list(documents)
    finally:
        client.close()


def find_one(collection, filt, database=settings.METRIC_DB):
    """ A wrapper for 'findOne' to ensure the connection will be closed.
    Args:
        collection(str): mongoDB collection
        filt(dict): mongoDB filter
        proj(dict): mongoDB projection
        database(str): name of database
    Return:
        documents(cursor): mongoDB cursor 
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
    finally:
        client.close()


def get_available_apps(collection):
    """
    Return:
        apps(list): list of dictionary.
    """
    documents, apps = find_all(collection=collection, filt={}), []
    if documents:
        for i in documents:
            if 'appName' in i.keys():
                apps.append({'appName': i['appName'], 'id': i['_id']})

    return apps

#TODO: probably need to change to app_id.
def create_profiling_dataframe(app_name):
    """ Create a dataframe of features.
    Args:
        app_name(str): Map to the 'appName' in Mongo database.
    Returns:
        df(pandas dataframe): Dataframe with rows of features, where each row is a service.
        (i.e. if an app has N services, where each service has K dimensions, the dataframe would be NxK)
    """
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
    return df


def get_services(app_name):
    """ Request from configDB, assuming appName is unique here.
    """
    filt = {'name': app_name}
    database, collection = settings.CONFIG_DB, 'applications'

    # alway search from configdb.application.
    app = find_one(database=database, collection=collection, filt=filt)
    if app == None:
        raise KeyError(
            'Cannot find document: filter={}, databse={}, collection={}'.format(filt, database, collection))
    service_names = app['serviceNames']

    return service_names
