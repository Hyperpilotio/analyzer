"""Data Source for xgboost."""
from influxdb import InfluxDBClient
from datetime import datetime

import json

GROUP_IDX = 0
GENERATOR_IDX = 1
EXCLUDE_MEASUREMENTS = [
    'intel/docker/spec/creation_time',
    'intel/docker/spec/image_name',
    'intel/docker/spec/labels/value',
    'intel/docker/spec/size_root_fs',
    'intel/docker/spec/size_rw',
    'intel/docker/spec/status',
    'intel/docker/stats/cgroups/cpu_stats/cpu_usage/per_cpu/value',
    'intel/docker/stats/cgroups/pids_stats/limit',
    'intel/docker/stats/filesystem/device_name']
TAG_KEYS = dict(
    docker="docker_id",
    procfs="nodename",
    goddd="method"
)
METADATA_KEYS = ['nodename', 'app', 'docker_id']

class XGBoostData():
    """XGBoostData."""

    def __init__(self, keys, data):
        """Constructor."""
        self.keys = keys
        self.data = data


def get_xgboost_data(app_metric, app_slo, tags):
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

    tag_filter = " AND " .join(["%s='%s'" % (k, v) for k, v in tags.items()])
    # query metrics by tag
    query_metric = "SELECT * FROM \"%s\" where %s order by time asc" % \
                   (app_metric, tag_filter)
    print("App query: " + query_metric)

    show_measurements = "SHOW MEASUREMENTS"

    print "preparing data..."

    rs_measurement = influxClient.query(show_measurements).items()
    measurement_list = [
        x['name'] for x in rs_measurement[GROUP_IDX][GENERATOR_IDX]
        if "hyperpilot" not in x['name'] and x['name'] not in EXCLUDE_MEASUREMENTS
    ]

    rs_list = []
    for measurement in measurement_list:
        items = influxClient.query('select * from "%s"' % measurement, epoch='s').items()
        if len(items) == 0:
            print "No items found for measurement %s" % measurement
            continue
        rs_list.append({
            'key': measurement,
            'generator': items[GROUP_IDX][GENERATOR_IDX],
            'currentData': items[GROUP_IDX][GENERATOR_IDX].next()
        })

    rs_app = influxClient.query(query_metric, epoch='s')

    # generate keys
    # [{'measurement': 'name', 'tagValue': 'tag value', 'tagKey': 'tag key', 'id': int_id}, ...]
    print "generate keys..."
    keys = generateKeys(influxClient, rs_list)

    data = []
    proceedRecords = 0
    previous_item_time = 0


    # iterate per data point
    print "scanning..."
    for data_point in rs_app.items()[0][GENERATOR_IDX]:
        line = []
        print(data_point)
        item_time = data_point['time']
        if previous_item_time == 0:
            previous_item_time = item_time
            continue

        print datetime.fromtimestamp(item_time)

        for measurement_data in rs_list:
            values = []
            key_list = [
                key for key in keys
                if key["measurement"] == measurement_data["key"]]
            if len(key_list) == 0:
                continue

            while True:
                current_data = measurement_data['currentData']
                if not current_data:
                    break

                if current_data['time'] <= item_time and current_data['time'] > previous_item_time:
                    if type(current_data['value']) is not unicode and type(current_data['value']) is not str:
                        values.append(current_data['value'])
                    measurement_data['currentData'] = next(measurement_data['generator'], None)
                elif current_data['time'] > item_time:
                    # measurement_data time > item_time
                    break
                else:
                    # measurement_data time <= previous_item_time
                    measurement_data['currentData'] = next(measurement_data['generator'], None)
            if len(values) > 0:
                line.append('%d:%f' % (key_list[0]['id'], mean(values)))

        if len(line) > 0:
            line = [str(data_point['value'])] + line
            data.append(" ".join(line))
            proceedRecords += 1
            previous_item_time = item_time

    print "total data: %d" % len(data)
    print "write keys to key.txt"
    write_to_file([dict(id=k['id'], tagKey=k['tagKey'], tagValue=k['tagValue'], measurement=k['measurement']) for k in keys], "keys.txt")
    print "write mapping file to mapping.txt"
    write_to_file([dict(id=m['id'], metadata=m['metadata']) for m in keys], 'mapping.txt')
    print "write data to data.txt"
    write_to_file(data, "data.txt")
    print "write xgboost key to xgboost_key.txt"
    # all values has parsed into float type
    write_to_file(["%d %s %s" % (k['id'], k['measurement'], 'float') for k in keys], "xgboost_key.txt")

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
            'metadata': {app: [app_name], nodename: [node_name], deploymentId: [deployment_id]}
        },
        {...}
        [measurement: list_data]
    ]
    """

    keys = []
    index = 0
    for x in rs:
        measurement_name = x['key']
        item = [k for k in TAG_KEYS if k in measurement_name]
        if len(item) == 1:
            tagQuery = 'SHOW TAG VALUES FROM "%s" WITH KEY="%s"' % (measurement_name, TAG_KEYS[item[0]])
            metadataQuery = 'SHOW TAG VALUES FROM "{measurement_name}" WITH KEY="{metadata_key}" WHERE {id_key} = \'{id_value}\''
            tagValues = influxClient.query(tagQuery)
            for tag in tagValues.items()[0][1]:
                index += 1
                metadata = {}
                for t in METADATA_KEYS:
                    metaRs = influxClient.query(metadataQuery.format(measurement_name=measurement_name, metadata_key=t, id_key=TAG_KEYS[item[0]], id_value=tag['value']))
                    if len(metaRs.items()) > 0:
                        metadata[t] = [x['value'] for x in list(metaRs.items()[GROUP_IDX][GENERATOR_IDX])]
                keys.append({
                    'measurement': measurement_name,
                    'tagKey': TAG_KEYS[item[0]],
                    'tagValue': tag['value'],
                    'id': index,
                    'metadata': metadata
                })
    print "total %s keys" % index
    return keys


def mean(valueList):
    """Mean."""
    return sum(valueList) / float(len(valueList))


if __name__ == '__main__':
    d = get_xgboost_data(
        app_metric="hyperpilot/goddd/api_booking_service_request_latency_microseconds",
        app_slo=100,
        tags={"method": "load", "summary": "quantile_90"})

    # print d.keys
    # print d.data
