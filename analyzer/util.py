import pandas as pd
import numpy as np
from api_service.db import metricdb


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
    app = metricdb[collection].find_one(filt)
    if app == None:
        raise KeyError(
            'Cannot find document: filter={}'.format(filt))
    serviceNames = pd.Index(app['services'])
    benchmarkNames = pd.Index(app['benchmarks'])

    # make dataframe
    ibenchScores = []
    for service in serviceNames:
        filt = {'appName': appName, 'serviceInTest': service}
        app = metricdb[collection].find_one(filt)
        if app == None:
            raise KeyError(
                'Cannot find document: filter={}'.format(filt))
        ibenchScores.append([i['toleratedInterference']
                             for i in app['testResult']])
    df = pd.DataFrame(data=np.array(ibenchScores),
                      index=serviceNames, columns=benchmarkNames)
    return df


def get_calibration_dataframe(calibration_document):
    if calibration_document is None:
        return None
    df = pd.DataFrame(calibration_document["testResult"])
    data = df.groupby("loadIntensity").apply(
        lambda group: group["qosValue"].describe()[["mean", "min", "max"]]
    ).reset_index()
    return data.to_dict(orient="records")


def percentile(n):
    f = lambda series: series.quantile(n / 100)
    f.__name__ = f"percentile_{n}"
    return f


def get_profiling_dataframe(profiling_document):
    if profiling_document is None:
        return None
    df = pd.DataFrame(profiling_document["testResult"])
    df = df.rename(columns={"qos": "qosValue"})
    data = df.groupby("benchmark").apply(
        lambda group: group.groupby("intensity")["qosValue"].agg(
            ["mean", percentile(10), percentile(90)]
        ).reset_index().to_dict(orient="records")
    )
    return data.to_dict()
