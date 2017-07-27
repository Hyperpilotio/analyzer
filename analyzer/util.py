import pandas as pd
import numpy as np
from api_service.db import metricdb, configdb
from functools import lru_cache

# TODO: Move these into a config or constants file
NODETYPE_COLLECTION = 'nodetypes'
APP_COLLECTION = 'applications'
MY_REGION = 'us-east-1'
COST_TYPE = 'LinuxReserved'

DEFAULT_CLOCK_SPEED = 2.3
DEFAULT_NET_PERF = 'Low'
DEFAULT_IO_THPT = 125

# TODO: Use the upper bounds to normalize the feature variables
MAX_VCPU = 128
MAX_CLOCK_SPEED = 3.5
MAX_MEM_SIZE = 1952
MAX_NET_BW = 20000
MAX_IO_THPT = MAX_NET_BW / 8.0

NETWORK_DICT = {'Very Low': 50, 'Low': 100, 'Low to Moderate': 300, 'Moderate': 500, "High": 1000,
                "10 Gigabit": 10000, "Up to 10 Gigabit": 10000, "20 Gigabit": 20000}


def get_all_nodetypes(collection=NODETYPE_COLLECTION, region=MY_REGION):
    region_filter = {'region': region}
    all_nodetypes = configdb[collection].find_one(region_filter)
    if all_nodetypes is None:
        raise KeyError(
            'Cannot find nodetype document: filter={}'.format(region_filter))
    return all_nodetypes


@lru_cache(maxsize=1)
def get_bounds(all_node_types):
    """ Get the (min, max) boundary for each dimension
    """
    features = [encode_instance_type(node_type) for node_type in all_node_types]
    return list(zip(features.min(axis=0), features.max(axis=0)))


def encode_instance_type(instance_type):
    """ convert each instance type to a vector of feature values 
        TODO: improve query efficiency by precomputing & caching all feature vectors
    """

    all_nodetypes = get_all_nodetypes()
    for nodetype in all_nodetypes:
        if nodetype['name'] == instance_type:
            vcpu = nodetype['cpuConfig']['vCPU']
            clock_speed = nodetype['cpuConfig']['clockSpeed']['value']
            mem_size = nodetype['memConfig']['size']['value']
            net_perf = nodetype['networkConfig']['performance']
            io_thpt = nodetype['storageConfig']['expectedThroughput']['value']

            if clock_speed == 0:
                clock_speed = DEFAULT_CLOCK_SPEED

            if net_perf == "":
                net_perf = DEFAULT_NET_PERF
            net_bw = NETWORK_DICT[net_perf]

            if io_thpt is None:
                io_thpt = DEFAULT_IO_THPT

            feature_vector = np.array(
                [vcpu, clock_speed, mem_size, net_bw, io_thpt])

            return feature_vector
    else:
        raise KeyError(f'Cannot find instance type: name={instance_type}')


def decode_instance_type(feature_vector):
    """ convert a candidate solution recommended by the optimizer into an aws instance type
        Args:
            feature_vector: candidate solution in a vector space
        Returns:
            instance_type: node type closest to the feature vector based on a distance function
    """

    all_nodetypes = get_all_nodetypes()
    instane_types = [nodetype['name'] for nodetype in all_nodetypes]
    distance = np.array(list(map(lambda x: feature_distance(encode_instance_type(x), feature_vector), 
                                 instance_types)))

    return instance_types[np.argmin(distance)]


def feature_distance(f1, f2):
    return np.linalg.norm(f1 - f2)


# TODO: improve query efficiency
# get from configdb the price (hourly cost) of an instance_type
def get_price(instance_type):
    all_nodetypes = get_all_nodetypes()

    for nodetype in all_nodetypes:
        if nodetype['name'] == instance_type:
            price = nodetype['hourlyCost'][COST_TYPE]['value']
            return price
    else:
        raise KeyError(f'Cannot find instance type: name={instance_type}')


# cost function based on sloMetric type and value, and hourly price
def compute_cost(price, slo_type, qos_value):
    if slo_type in ['latency', 'throughput']:
        # for long-running services, calculate the montly cost based on hourly price
        cost = price * 24 * 30
    else:
        # for batch jobs, qos_value = job_completion_time in minutes
        cost = price * qos_value / 60

    return cost


# get from configdb the type of an application ("long-running" or "batch")
def get_app_type(app_name):
    app_filter = {'appName': app_name}
    app = configdb[APP_COLLECTION].find_one(app_filter)
    app_type = app['type']

    return app_type


# get from configdb the slo metric type of an application
def get_slo_type(app_name):
    app_filter = {'appName': app_name}
    app = configdb[APP_COLLECTION].find_one(app_filter)
    slo_type = app['slo']['type']

    return slo_type


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
    if app == None:
        raise KeyError(
            'Cannot find document: filter={}'.format(filt))
    serviceNames = pd.Index(app['services'])
    benchmarkNames = pd.Index(app['benchmarks'])

    # make dataframe
    ibenchScores = []
    for service in serviceNames:
        filt = {'appName': app_name, 'serviceInTest': service}
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
    def f(series): return series.quantile(n / 100)
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
    app_name = profiling_document['appName']
    slo = configdb.applications.find_one({'name': app_name})['slo']

    test_results = pd.DataFrame(profiling_document['testResult'])
    test_results = test_results.rename(columns={'qos': 'qosValue'})

    radar_data = {
        'benchmark': [],
        'tolerated_interference': [],
        'score': [],
    }

    for benchmark, df in test_results.groupby(['benchmark', 'intensity'])['qosValue'].mean().groupby(level='benchmark'):
        df.index = df.index.droplevel('benchmark')
        result = compute_tolerated_interference(
            benchmarks=df,
            slo_value=slo['value'],
            metric_type=slo['type'],
        )
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
