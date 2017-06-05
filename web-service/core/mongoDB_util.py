import pandas as pd
import numpy as np
from django.conf import settings
from pymongo import MongoClient


def create_profiling_dataframe(app_name):
    """ Create a dataframe of features.
    Args:
        app_name(str): Map to the 'appName' in Mongo database.
    Returns:
        df(pandas dataframe): Dataframe with rows of features, where each row is a service.
        (i.e. if an app has N services, where each service has K dimensions, the dataframe would be NxK)
    """
    try:
        client = MongoClient(settings.DATABASE_URL)
        metric_db = client[settings.METRIC_DB]
        metric_db.authenticate(settings.USER, settings.PWD,
                               source=settings.METRIC_DB)
        # request from database
        filt = {'appName': app_name}
        app = metric_db['profiling'].find_one(filt)
        if app == None:
            raise KeyError(
                'Cannot find document: filter={} from {}'.format(filt, metric_db))
        service_names = pd.Index(app['services'])
        benchmark_names = pd.Index(metric_db['profiling'].find_one(
            {'appName': app_name})['benchmarks'])

        # make dataframe
        ibench_scores = []
        for service in service_names:
            filt = {'appName': app_name, 'serviceInTest': service}
            app = metric_db['profiling'].find_one(filt)
            if app == None:
                raise KeyError(
                    'Cannot find document: filter={} from {}'.format(filt, metric_db))
            ibench_scores.append([i['toleratedInterference']
                                  for i in app['testResult']])
        df = pd.DataFrame(data=np.array(ibench_scores),
                          index=service_names, columns=benchmark_names)
    except Exception as e:
        raise e
    else:
        return df
    finally:
        client.close()
