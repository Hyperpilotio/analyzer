from influxdb import InfluxDBClient
from dateutil import parser

class XGBoostData():
    def __init__(self, keys, data):
        self.keys = keys
        self.data = data

def get_xgboost_data(app_metric, app_slo):
    # TODO: Replace with configuration
    client = InfluxDBClient('localhost', 8086, 'root', 'root', 'snap')
    rs = client.query('SHOW MEASUREMENTS')
    keys = {}
    i = 0
    for pair in rs.items()[0][1]:
        # We skip hyperpilot namespace stats (goddd, etc)
        if not pair['name'].startswith("hyperpilot"):
            keys[pair['name']] = i
            i += 1

    # Include app metric in the results
    keys[app_metric] = i

    # NOTE: Limiting to subset of points for now...
    measurement_names = ",".join(['"%s"' % v for v in keys.keys()[0:20]])
    query = 'SELECT * FROM %s' % measurement_names
    print(query)
    rs = client.query(query)
    # Data streams holds each metric's generator, key's index and current item
    data_streams = []
    # All data is a list of list, which each list stores the time, and
    # in that time each key and value. key name is substituted as an index
    all_data = []
    current_time = None
    for item in rs.items():
        key_name = item[0][0]
        generator = item[1]
        first_item = generator.next()
        # We assume data is already sorted ascending by time
        first_time = parser.parse(first_item['time']).replace(microsecond=0)
        print(first_time)
        if not current_time or current_time > first_time:
            current_time = first_time
        data_streams.append([key_name, keys[key_name], generator, first_item, first_time])

    next_earliest_time = None
    found_new_time = True
    while found_new_time:
        found_new_time = False
        line_data = []
        print("Current time")
        print(current_time)
        for stream in data_streams:
            print("Current")
            print(stream[4])
            if stream[4] and stream[4] == current_time:
                print("New item")
                line_data.append("%d:%f" % (stream[1], stream[3]['value']))
                next_item = stream[2].next()
                next_time = None
                if next_item:
                    next_time = parser.parse(next_item['time']).replace(microsecond=0)
                stream[4] = next_time
                stream[3] = next_item

            if stream[4] and stream[4] > current_time and (not next_earliest_time or next_earliest_time > stream[4]):
                print("Found new earliest")
                print(stream[4])
                found_new_time = True
                next_earliest_time = stream[4]

        if len(line_data) > 0:
            all_data.append(" ".join(line_data))

        if found_new_time:
            current_time = next_earliest_time

    return XGBoostData(keys, all_data)
