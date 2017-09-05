"""Data Source for xgboost."""
from influxdb import InfluxDBClient
from datetime import datetime
from math import fabs

import json

GROUP_IDX = 0
GENERATOR_IDX = 1


class XGBoostData():
    """XGBoostData."""

    def __init__(self, keys, data):
        """Constructor."""
        self.keys = keys
        self.data = data


def get_xgboost_data(app_metric, app_slo, tag_name, tag_value):
    """Get XGBoost data."""
    with open('data_source_config.json') as f:
        config = json.load(f)

    influxClient = InfluxDBClient(
        config['influx_host'],
        config['influx_port'],
        config['influx_username'],
        config['influx_password'],
        config['influx_database'])

    sampling_rate = config["sampling_rate"]
    acceptable_offset = config["acceptable_offset"]

    # query metrics by tag
    query_metric = "SELECT * FROM \"%s\" where %s='%s' order by time asc" % \
                   (app_metric, tag_name, tag_value)

    show_measurements = "SHOW MEASUREMENTS"

    rs_measurement = influxClient.query(show_measurements).items()
    measurement_list = [
        x['name'] for x in rs_measurement[0][GENERATOR_IDX]
        if "hyperpilot" not in x['name']
    ]

    rs_list = []
    for measurement in measurement_list:
        rs_list.append({measurement: list(influxClient.query('select * from "%s"' % measurement, epoch='s').items()[0][GENERATOR_IDX])})

    rs_app = influxClient.query(query_metric, epoch='s')

    # generate keys
    # [{'measurement': 'name', 'tagValue': 'tag value', 'tagKey': 'tag key', 'id': int_id}, ...]
    keys = generateKeys(influxClient, rs_list)

    data = []
    proceedRecords = 0
    next_sample_base = 0

    for tag in rs_app.items():

        # iterate per data point
        for data_point in tag[GENERATOR_IDX]:

            line = []
            # find related metrics in rs with time interval 1s
            item_time = data_point['time']
            if item_time < next_sample_base:
                continue
            else:
                next_sample_base = item_time + sampling_rate

            print datetime.fromtimestamp(item_time)

            # narrow this list
            rs_list = [
                {x.keys()[0]: binarySearch(x[x.keys()[0]], data_point, acceptable_offset, 0, len(x) - 1)}
                for x in rs_list
                if x
            ]
            found = []

            # iterate for each key
            for key in keys:
                rs_group = [x[key["measurement"]] for x in rs_list if x.keys()[0] == key["measurement"]]
                if len(rs_group) > 0 and rs_group[0] is not None:
                    l = [x for x in rs_group[0] if x[key["tagKey"]] == key["tagValue"]]
                    found = [x for x in l if fabs(x['time'] - item_time) <= acceptable_offset]
                    if len(found) > 0:
                        line.append("%d:%f" % (key["id"], mean([x['value'] for x in found])))
            proceedRecords += 1
            print(line)
            if len(line) > 0:
                data.append(line)
            print "%s records proceed" % proceedRecords

    return XGBoostData(dict([{k['measurement'], k['id']} for k in keys]), data)


def binarySearch(sorted_list, item, offset, lo, high):
    """Narrow the sorted list by truncating data with timestamp less than item['time']."""
    if not sorted_list:
        return None
    if len(sorted_list) == 0 or len(sorted_list) == 1:
        return None
    baseIndex = high / 2
    base = sorted_list[baseIndex]

    if fabs(base['time'] - item['time']) <= offset:
        return sorted_list[lo:]
    elif base['time'] < (item['time'] - offset):
        newList = sorted_list[baseIndex:]
        result = binarySearch(newList, item, offset, baseIndex, len(newList))
    elif base['time'] > (item['time'] + offset):
        result = binarySearch(sorted_list, item, offset, lo, baseIndex)

    if result:
        return sorted_list[lo:]
    else:
        return None


def generateKeys(influxClient, rs):
    """Generate Keys.

    Format: [
        {
            'measurement': 'name',
            'tagKey': 'tag key',
            'tagValue': 'tag value',
            'id': int_id
        },
        {...}
        [measurement: list_data]
    ]
    """
    tagKey = dict(
        docker="docker_id",
        procfs="nodename",
        goddd="method"
    )
    keys = []
    index = 0
    for x in rs:
        measurement_name = x.keys()[0]
        item = [k for k in tagKey if k in measurement_name]
        if len(item) == 1:
            tagQuery = 'SHOW TAG VALUES FROM "%s" WITH KEY="%s"' % (measurement_name, tagKey[item[0]])
            tagValues = influxClient.query(tagQuery)
            for tag in tagValues.items()[0][1]:
                index += 1
                keys.append({
                    'measurement': measurement_name,
                    'tagKey': tagKey[item[0]],
                    'tagValue': tag['value'],
                    'id': index
                })
    print "total %s keys" % index
    return keys


def mean(valueList):
    """Mean."""
    return sum(valueList) / float(len(valueList))


if __name__ == '__main__':
    d = get_xgboost_data(
        app_metric="hyperpilot/goddd/api_booking_service_request_count",
        app_slo=100,
        tag_name="method",
        tag_value="load")

    print d.keys
    print d.data
