import time

import pandas as pd
import numpy as np
from influxdb import DataFrameClient

from . import data_source as ds
from logger import get_logger
from config import get_config

config = get_config()
logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))
df_client = DataFrameClient(
    host=config.get("INFLUXDB", "HOST"),
    port=config.getint("INFLUXDB", "PORT"),
    username=config.get("INFLUXDB", "USERNAME"),
    password=config.get("INFLUXDB", "PASSWORD"),
    database=config.get("INFLUXDB", "DATABASE"))
BATCH_TIME = int(config.get("ANALYZER", "CORRELATION_BATCH_TIME"))
WINDOW = int(config.get("ANALYZER", "CORRELATION_WINDOW"))
app_metric="hyperpilot/goddd/api_booking_service_request_latency_microseconds"
tags={"method": "request_routes", "summary": "quantile_90"}


class MetricConsumer(object):
    def __init__(self):
        # load in initial data

        self.get_data(app_metric, tags)

    def get_data(self, app_metric, tags, start_time=None, end_time=None):
        tag_filter = " AND " .join(["%s='%s'" % (k, v) for k, v in tags.items()])
        q = "select first(*) from \"%s\" where %s" % \
                (app_metric, tag_filter)
        first_sample = df_client.query(q)

        initial_time = first_sample[app_metric].index[0].timestamp() * 1000000000

        #if 'start_time' in config and config['start_time'] != "":
        #    time_filter = "time > %d" % int(config['start_time'])
        #else:
        time_filter = "time > %d" % initial_time
        #if 'end_time' in config and config['end_time'] != "":
        #time_filter = "%s AND time < %d" % (time_filter, initial_time + 5 * 60 * 1000000000)

        time_filter = "%s AND time < %d" % (time_filter, initial_time + 5 * 60 * 1000000000)
        print('Using time filter:', time_filter)

        # query metrics by tag and time filters
        query_metric = "select value from \"%s\" where %s AND %s order by time asc" % \
            (app_metric, tag_filter, time_filter)
        print("Query to get app metric: \n " + query_metric)
        rs_app = df_client.query(query_metric)
        N = len(rs_app[app_metric])

        timestamps = [ts.timestamp() * 1000000000 for ts in rs_app[app_metric].index]
        print("Number of app metric samples fetched: ", len(rs_app[app_metric]))

        show_measurements = "SHOW MEASUREMENTS"

        print("Preparing data...")

        rs_measurement = df_client.query(show_measurements)
        measurement_list = [
            x['name'] for x in rs_measurement['measurements']
            if "hyperpilot" not in x['name'] and x['name'] not in ds.EXCLUDE_MEASUREMENTS
        ]
        print("Number of system metrics to be fetched", len(measurement_list))


        for measurement in measurement_list:
            query_measurements = 'select * from "%s" where %s order by time asc' % (measurement, time_filter)
            print("Query to get system metric: \n " + query_measurements)
            result = df_client.query(query_measurements)
            if len(result) == 0:
                print("No items found for measurement %s" % measurement)
                continue
            result[measurement]


    def shift_and_update(self):
        pass

    def write_result(self):
        # write to result db
        pass

    def run(self):
        time.sleep(BATCH_TIME)
        self.shift_and_update()
        self.write_result()
        # todo: write to log.
        #logger

if __name__ == '__main__':
    mc = MetricConsumer()

