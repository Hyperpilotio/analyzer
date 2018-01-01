import bson

from pymongo import ReturnDocument
from pymongo.cursor import Cursor
import numpy as np
import pandas as pd

from config import get_config
from logger import get_logger

from .db import configdb, metricdb

logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))

config = get_config()

app_collection = config.get("ANALYZER", "APP_COLLECTION")

def get_all_apps():
    return configdb[app_collection].find()


def get_all_apps_by_state(state_filter):
    return configdb[app_collection].find({"state": state_filter})


def create_app(app_json):
    return configdb[app_collection].insert_one(app_json)


def update_and_get_app(app_id, update_doc, unset=False):
    if unset:
        updated_doc = configdb[app_collection].find_one_and_update(
            {"app_id": app_id},
            {"$unset": update_doc},
            return_document=ReturnDocument.AFTER
        )
    else:
        updated_doc = configdb[app_collection].find_one_and_update(
            {"app_id": app_id},
            {"$set": update_doc},
            return_document=ReturnDocument.AFTER
        )

    updated_doc.pop("_id")
    return updated_doc

def update_app(app_id, update_doc):
    result = configdb[app_collection].update_one(
        {"app_id": app_id},
        {"$set": update_doc}
    )

    return result.modified_count > 0

def get_app_microservices(app_id):
    application = configdb[app_collection].find_one({"app_id": app_id})
    if application:
        return application.get("microservices", [])

def get_app_by_id(app_id):
    return configdb[app_collection].find_one({"app_id": app_id})

# get from configdb the application json
def get_app_by_name(app_name):
    app_filter = {'name': app_name}
    app = configdb[app_collection].find_one(app_filter)
    return app


# get from configdb the type of an application ("long-running" or "batch")
def get_app_type(app_name):
    app = get_app_by_name(app_name)

    return app['type']


# get from configdb the slo metric type of an application
def get_slo_type(app_name):
    app = get_app_by_name(app_name)

    return app['slo']['type']


def get_slo_value(app_name):
    app = get_app_by_name(app_name)

    try:
        slo_value = app['slo']['value']
    except KeyError:
        slo_value = 500.  # TODO: put an nan

    return slo_value


def get_budget(app_name):
    app = get_app_by_name(app_name)

    try:
        budget = app['budget']['value']
    except KeyError:
        budget = 25000.  # all types allowed

    return budget


# get from configdb the {cpu|mem} requests (i.e. min) for the app service container
def get_resource_requests(app_name):
    app = get_app_by_name(app_name)

    # TODO: handle apps with multiple services
    service = app['serviceNames'][0]

    min_resources = {'cpu': 0., 'mem': 0.}

    for task in app['taskDefinitions']:
        if task['nodeMapping']['task'] == service:
            container_spec = \
                task['taskDefinition']['deployment']['spec']['template']['spec']['containers'][0]
            try:
                resource_requests = container_spec['resources']['requests']
            except KeyError:
                logger.debug(
                    f"No resource requests for the container running {service}")
                return min_resources

            try:
                cpu_request = resource_requests['cpu']
                # conver cpu unit from millicores to number of vcpus
                if cpu_request[-1] == 'm':
                    min_resources['cpu'] = float(
                        cpu_request[:len(cpu_request) - 1]) / 1000.
                else:
                    min_resources['cpu'] = float(cpu_request)
            except KeyError:
                logger.debug(
                    f"No cpu request for the container running {service}")

            try:
                mem_request = resource_requests['memory']
                # convert memory unit to GB
                if mem_request[-1] == 'M':
                    min_resources['mem'] = float(
                        mem_request[:len(mem_request) - 1]) / 1000.
                elif mem_request[-2:] == 'Mi':
                    min_resources['mem'] = float(
                        mem_request[:len(mem_request) - 2]) / 1024.
                else:
                    min_resources['mem'] = float(mem_request) / 1024. / 1024.
            except KeyError:
                logger.debug(
                    f"No memory request for the container running {service}")

    logger.info(
        f"Found resource requests for app {app_name} service {service}: {min_resources}")
    return min_resources


# TODO: probably need to change to appId.
def create_profiling_dataframe(app_name, collection='profiling'):
    """ Create a dataframe of features.
    Args:
        app_name(str): Map to the 'appName' in Mongo database.
    Returns:
        df(pandas dataframe): Dataframe with rows of features, where each row is a service.
        (i.e. if an app has N services, where each service has K dimensions, the dataframe would be NxK)
    """
    filt = {'appName': app_name}
    app = metricdb[collection].find_one(filt)
    if app is None:
        raise KeyError(
            'Cannot find document: filter={}'.format(filt))
    serviceNames = pd.Index(app['services'])
    benchmarkNames = pd.Index(app['benchmarks'])

    # make dataframe
    ibenchScores = []
    for service in serviceNames:
        filt = {'appName': app_name, 'serviceInTest': service}
        app = metricdb[collection].find_one(filt)
        if app is None:
            raise KeyError(
                'Cannot find document: filter={}'.format(filt))
        ibenchScores.append([i['toleratedInterference']
                             for i in app['testResult']])
    df = pd.DataFrame(data=np.array(ibenchScores),
                      index=serviceNames, columns=benchmarkNames)
    return df
