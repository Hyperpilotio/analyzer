import time

import pandas as pd
from numpy import NaN
from influxdb import DataFrameClient

from logger import get_logger
from config import get_config
from api_service.db import Database
import diagnosis.data_source as ds

config = get_config()
logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))
resultdb = Database(config.get("ANALYZER", "RESULTDB_NAME"))

client_kwargs = {'host': config.get("INFLUXDB", "HOST"),
                 'port': config.getint("INFLUXDB", "PORT"),
                 'username': config.get("INFLUXDB", "USERNAME"),
                 'password': config.get("INFLUXDB", "PASSWORD")}

df_client_app = DataFrameClient(
    **client_kwargs,
    database=config.get("INFLUXDB", "APP_DB_NAME"))
df_client_node = DataFrameClient(
    **client_kwargs,
    database=config.get("INFLUXDB", "RAW_DB_NAME"))
BATCH_TIME = int(config.get("ANALYZER", "CORRELATION_BATCH_TIME"))
WINDOW = int(config.get("ANALYZER", "CORRELATION_WINDOW"))
app_metric = "hyperpilot/goddd/api_booking_service_request_latency_microseconds"
tags = {"method": "request_routes", "summary": "quantile_90"}
M = 1000000000


class MetricConsumer(object):
    def __init__(self, start_time=None, end_time=None):
        # load in initial data
        self.df = self.get_data(app_metric, tags)
        self.write_result()

    def get_data(self, start_time=None, end_time=None):
        """ Returns a dataframe of cleaned, interpolated data for the time specified.
        If no period is specified, it returns a dataframe from the last five minutes
        of influx data found. """

        tag_filter = " AND " .join(["%s='%s'" % (k, v)
                                    for k, v in tags.items()])
        q = "select last(*) from \"%s\" where %s" % \
            (app_metric, tag_filter)
        last_sample = df_client_app.query(q)

        last_time = last_sample[app_metric].index[0].timestamp() * M
        # set the end time to now (or just past the last timestamp in the data)
        end_time = last_time + M
        # print(end_time)
        # if 'start_time' in config and config['start_time'] != "":
        #    time_filter = "time > %d" % int(config['start_time'])
        # else:
        start_time = end_time - 5 * 60 * M
        time_filter = "time > %d" % start_time

        # if 'end_time' in config and config['end_time'] != "":
        #time_filter = "%s AND time < %d" % (time_filter, start_time + 5 * 60 * M)

        time_filter = "%s AND time < %d" % (time_filter, end_time)
        logger.info('Using time filter: ' + time_filter)

        # query metrics by tag and time filters
        query_metric = "select value from \"%s\" where %s AND %s order by time desc" % \
            (app_metric, tag_filter, time_filter)
        logger.info("Query to get app metric: \n " + query_metric)
        sl_data = df_client_app.query(query_metric)[app_metric]

        N = len(sl_data)

        time_buckets = range(int(end_time), int(start_time), -5 * M)
        df = self.match_timestamps(time_buckets, sl_data)
        df.columns = [app_metric]

        logger.info("Number of app metric samples fetched: %d" % len(sl_data))

        show_measurements = "SHOW MEASUREMENTS"

        rs_measurement = df_client_node.query(show_measurements)
        measurement_list = [
            x['name'] for x in rs_measurement['measurements']
            if "hyperpilot" not in x['name'] and x['name'] not in ds.EXCLUDE_MEASUREMENTS
        ]
        logger.info("Number of system metrics to be fetched: %d" %
                    len(measurement_list))

        for measurement in measurement_list:
            measurements_query = 'select value from "%s" where %s order by time desc' % (
                measurement, time_filter)
            logger.info("Query to get system metric: \n " + measurements_query)
            result = df_client_node.query(measurements_query)
            if measurement not in result:
                logger.info("No items found for measurement %s" % measurement)
                continue
            node_data = result[measurement]

            if type(node_data.iloc[0, 0]) == str:
                logger.info("Query incorrect for measurement %s" % measurement)
                continue

            df[measurement] = self.match_timestamps(
                time_buckets, node_data).iloc[:, 0]

        return df.interpolate()

    def shift_and_update(self):
        new_df = self.get_data()
        self.df = self.df.iloc[:54].append(new_df).interpolate()

    def write_result(self):
        correlations = self.df.drop(
            labels=app_metric, axis=1).corrwith(self.df[app_metric])
        correlations = correlations.sort_values(ascending=False)

        # jsonify a list of the top features for the current timestamp.
        doc = {"timestamp": time.time(),
               "coefficients": correlations[:3].to_json()}
        resultdb["correlations"].insert_one(doc)

    def match_timestamps(self, time_buckets, df):
        """ Grab one measurement value for each five second window. """
        matched_data = []
        timestamps = (ts for ts in df.index)
        for time_bucket in time_buckets:
            missing = True
            while True:
                try:
                    ts = next(timestamps)
                except StopIteration:
                    break
                ts_compare = ts.timestamp() * M
                if ts_compare > time_bucket - 5 * M and ts_compare <= time_bucket:
                    missing = False
                    if type(df.loc[ts]['value']) == pd.Series:
                        matched_data.append(df.loc[ts]['value'].iloc[0])
                    else:
                        matched_data.append(df.loc[ts]['value'])
                    break
                if ts_compare < time_bucket - 5 * M:
                    break
            if missing:
                matched_data.append(NaN)

        return pd.DataFrame(data=matched_data, index=time_buckets)


if __name__ == "__main__":
    mc = MetricConsumer()
