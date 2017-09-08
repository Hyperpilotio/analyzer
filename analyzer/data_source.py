"""Data Source for xgboost."""
from influxdb import InfluxDBClient
from datetime import datetime

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

    # sampling_rate = config["sampling_rate"]
    # acceptable_offset = config["acceptable_offset"]

    # query metrics by tag
    query_metric = "SELECT * FROM \"%s\" where %s='%s' order by time asc" % \
                   (app_metric, tag_name, tag_value)

    show_measurements = "SHOW MEASUREMENTS"

    print "preparing data..."

    rs_measurement = influxClient.query(show_measurements).items()
    measurement_list = [
        x['name'] for x in rs_measurement[0][GENERATOR_IDX]
        if "hyperpilot" not in x['name']
    ]

    rs_list = []
    for measurement in measurement_list:
        rs_list.append({
            'key': measurement,
            'generator': influxClient.query('select * from "%s"' % measurement, epoch='s').items()[0][GENERATOR_IDX],
            'currentData': {}
        })

    rs_app = influxClient.query(query_metric, epoch='s')

    # generate keys
    # [{'measurement': 'name', 'tagValue': 'tag value', 'tagKey': 'tag key', 'id': int_id}, ...]
    keys = generateKeys(influxClient, rs_list)

    data = []
    proceedRecords = 0
    previous_item_time = 0

    for tag in rs_app.items():

        # iterate per data point
        print "scanning..."
        for data_point in tag[GENERATOR_IDX]:

            line = []
            item_time = data_point['time']

            print datetime.fromtimestamp(item_time)

            for measurement_data in rs_list:
                values = []
                key_list = [
                    key for key in keys
                    if key["measurement"] == measurement_data["key"]]
                if len(key) == 0:
                    continue

                while True:
                    current_data = measurement_data['currentData']

                    measurement_data['currentData'] = next(measurement_data['generator'], None)

                    if current_data is None:
                        break
                    if not current_data:
                        continue

                    if current_data['time'] <= item_time and current_data['time'] > previous_item_time:
                        if type(current_data['value']) is unicode or type(current_data['value']) is str:
                            continue
                        values.append(current_data['value'])
                    else:
                        # measurement_data time > item_time
                        break
                if len(values) > 0:
                    line.append('%d:%f' % (key_list[0]['id'], mean(values)))

            if len(line) > 0:
                line.append(str(data_point['value']))
                print line
                data.append(" ".join(line))
            proceedRecords += 1
            previous_item_time = item_time
    print "total data: %d" % len(data)
    print "write keys to key.txt"
    write_to_file(keys, "keys.txt")
    print "write data to data.txt"
    write_to_file(data, "data.txt")

    return XGBoostData(keys, data)


def write_to_file(list, file_name):
    """Write to file."""
    with open(file_name, 'w') as text_file:
        for item in list:
            text_file.write(str(item))
            text_file.write("\n")


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
        measurement_name = x['key']
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

    # print d.keys
    # print d.data
