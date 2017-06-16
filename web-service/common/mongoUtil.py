import logging
import traceback
import pandas as pd
import numpy as np
from django.conf import settings
from pymongo import MongoClient
log = logging.getLogger(__name__)


def findAll(collection, filt={}, proj=None, database=settings.METRIC_DB, returnList=False):
    """ A wrapper for 'find' to ensure the connection will be closed.
    Args:
        collection(str): mongoDB collection
        filt(dict): mongoDB filter
        proj(dict): mongoDB projection
        database(str): name of database
    Return:
        documents(cursor): mongoDB cursor, 'None' if not found.
    """
    try:
        client = MongoClient(settings.DATABASE_URL, waitQueueTimeoutMS=200)
        db = client[database]
        db.authenticate(settings.USER, settings.PWD, source=database)
        documents = db[collection].find(filt, proj) if proj else db[
            collection].find(filt)
    except Exception as e:
        log.exception(e)
        return [] if returnList else None
    else:
        log.debug('query findAll collection={} filt={} proj={} database={}'.format(
            collection, filt, proj, database))
        log.debug('got {}'.format(documents))
        return documents if not returnList else list(documents)
    finally:
        client.close()


def findOne(collection, filt={}, proj=None, database=settings.METRIC_DB):
    """ A wrapper for 'findOne' to ensure the connection will be closed.
    Args:
        collection(str): mongoDB collection
        filt(dict): mongoDB filter
        proj(dict): mongoDB projection
        database(str): name of database
    Return:
        documents(cursor): dictionary, 'None' if not found.
    """
    try:
        client = MongoClient(settings.DATABASE_URL, waitQueueTimeoutMS=200)
        db = client[database]
        db.authenticate(settings.USER, settings.PWD, source=database)
        documents = db[collection].find_one(filt, proj) if proj else db[
            collection].find_one(filt)
    except Exception as e:
        log.exception(e)
        return None
    else:
        log.debug('query findOne collection={} filt={} proj={} database={}'.format(
            collection, filt, proj, database))
        log.debug('got {}'.format(documents))
        return documents
    finally:
        client.close()


def getAvailableApps(collection):
    """
    Return:
        apps(list): list of dictionary.
    """
    documents, apps = findAll(collection=collection, filt={}), []
    if documents:
        for i in documents:
            if 'appName' in i.keys():
                apps.append({'appName': i['appName'], 'id': i['_id']})

    return apps


# TODO: probably need to change to appId.
def createProfilingDataframe(appName, collection='profiling'):
    """ Create a dataframe of features.
    Args:
        appName(str): Map to the 'appName' in Mongo database.
    Returns:
        df(pandas dataframe): Dataframe with rows of features, where each row is a service.
        (i.e. if an app has N services, where each service has K dimensions, the dataframe would be NxK)
    """
    filt = {'appName': appName}
    app = findOne(collection=collection, filt=filt)
    if app == None:
        raise KeyError(
            'Cannot find document: filter={}'.format(filt))
    serviceNames = pd.Index(app['services'])
    benchmarkNames = pd.Index(app['benchmarks'])

    # make dataframe
    ibenchScores = []
    for service in serviceNames:
        {'appName': appName, 'serviceInTest': service}
        app = findOne(collection=collection, filt=filt)
        if app == None:
            raise KeyError(
                'Cannot find document: filter={}'.format(filt))
        ibenchScores.append([i['toleratedInterference']
                             for i in app['testResult']])
    df = pd.DataFrame(data=np.array(ibenchScores),
                      index=serviceNames, columns=benchmarkNames)
    return df


def getServices(appName):
    """ Request from configDB, assuming appName is unique here.
    """
    filt = {'name': appName}
    database, collection = settings.CONFIG_DB, 'applications'

    # alway search from configdb.application.
    app = findOne(database=database, collection=collection, filt=filt)
    if app == None:
        raise KeyError(
            'Cannot find document: filter={}, databse={}, collection={}'.format(filt, database, collection))
    serviceNames = app['serviceNames']

    return serviceNames
