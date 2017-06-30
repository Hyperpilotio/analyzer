import pandas as pd
import numpy as np
from api_service.db import metricdb, configdb

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
    df = df.rename(columns={"qosMetric": "qosValue"})
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


def get_radar_dataframe(profiling_document):
    # Currently calibration document and profilng document are not related
    # together.
    final_result = metricdb['calibration'].find_one({'appName': 'kafka', 'finalIntensity': profiling_document[
        'appCapacity']}, {'finalResult': 1})['finalResult']

    qos_value = final_result['qosValue']
    slo = configdb['applications'].find_one(
        {'name': 'kafka'})['slo']

    slo_value, slo_metric_type = slo['value'], slo['type']
    test_results = pd.DataFrame(profiling_document['testResult'])

    radar_data = {}
    radar_data['benchmark'], radar_data[
        'tolerated_interference'], radar_data['score'] = [], [], []
    for benchmark, df in test_results.groupby(['benchmark', 'intensity'])['qosValue'].agg("mean").groupby(level=0):
        df.index = df.index.droplevel(level=0)
        result = compute_tolerated_interference(
            df, slo_value, metric_type=slo_metric_type)
        radar_data['benchmark'].append(benchmark)
        radar_data['tolerated_interference'].append(min(result))
        # compute score
        radar_data['score'].append(100. - min(result))

    return radar_data


def compute_tolerated_interference(benchmarks, slo_value, metric_type, tolerated_percentage=10.):
    """ Compute Tolerated Interference, with linear interpolation.  
    Args: 
        benchmarks(DataFrame): index=intensity and columns=['qosValue']
        slo_value(float): service level objective for the application
        metric_type(str): 'throughput', 'latency'
        tolerated_percentage(float): percentage of slo tolerance
    Return:
        ti(float): tolerated interference between [0, 100].
    """
    def _linearIntp(tup1, tup2, y3):
        x1, y1 = tup1
        x2, y2 = tup2
        if y1 > y2:
            return _linearIntp((x2, y2), (x1, y1), y3)
        if y3 < y1 or y3 > y2:
            return None
        else:
            return (y3 - y1) * (x2 - x1) / (y2 - y1) + x1

    intensities, slo_values = np.append(
        0, benchmarks.index.values), np.append(slo_value, benchmarks.values)
    candidates = []

    # check metric type
    if metric_type == 'throughput':
        tolerated_slo_value = slo_value * (1. - tolerated_percentage / 100.)
        if min(slo_values) > tolerated_slo_value:
            candidates.append(100.)
    elif metric_type == 'latency':
        tolerated_slo_value = slo_value * (1. + tolerated_percentage / 100.)
        if max(slo_values) < tolerated_slo_value:
            candidates.append(100.)
    else:
        assert False, 'invalid metric type'

    # check input data
    assert (sorted(intensities) == intensities).all(
    ), 'intensities are not monotonic. intensities: {}'.format(intensities)
    assert all(intensity >= 0 and intensity <=
               100 for intensity in intensities), 'invalid intensities. intensites: {}'.format(intensities)
    assert len(slo_values) == len(
        intensities), 'length of slo_values and intensities does not match. slo_values: {}, intensities: {}'.format(slo_values, intensities)

    for i in range(len(slo_values) - 1):  # edge case tested
        x = _linearIntp((intensities[i], slo_values[i]), (intensities[
                        i + 1], slo_values[i + 1]), tolerated_slo_value)
        if x:
            candidates.append(x)

    return sorted(candidates)
