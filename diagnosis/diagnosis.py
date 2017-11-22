import time
from collections import namedtuple


from diagnosis.derived_metrics import MetricsResults
from config import get_config
from logger import get_logger
import pandas as pd
from numpy import NaN

config = get_config()
BATCH_TIME = int(config.get("ANALYZER", "CORRELATION_BATCH_TIME"))
WINDOW = int(config.get("ANALYZER", "CORRELATION_WINDOW"))
logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))
tags = {"method": "request_routes", "summary": "quantile_90"}
METRIC_TYPES = set(["RAW", "DERIVED"])

class Diagnosis(object):
    def __init__(self):
        return

    def get_averages(self):
        """ Get the average value over time window for each feature. """
        return self.input_df.mean(axis=0)

    def filter_features(self, series, threshold=None):
        return series[series > threshold]
        
    def compute_correlations(self):
        return self.input_df.corrwith(
                         self.sl_df[self.sl_metric])

    def compute_score(self, averages, correlations):
        return averages.multiply(correlations)

    def process_metrics(self, metrics):
        metric_results = [metrics.node_metrics[metric_name][node_name] for
                      metric_name in metrics.node_metrics
                      for node_name in metrics.node_metrics[metric_name]] \
                        + \
                    [metrics.container_metrics[metric_name][node_name][container_name] 
                        for metric_name in metrics.container_metrics
                        for node_name in metrics.container_metrics[metric_name] 
                        for container_name in metrics.container_metrics[metric_name][node_name]]

        start_time = metrics.app_metrics.index[0]
        time_buckets = [start_time + pd.Timedelta(seconds=s) for s in range(0, 60, 5)]
        app_df = self.match_timestamps(time_buckets, metrics.app_metrics)

        for metric_result in metric_results:
            metric_result.df = self.match_timestamps(time_buckets, metric_result.df)

        #averages = self.get_averages()
        #correlations = self.compute_correlations()
        #result = MetricResult()
        #result.confidence_score = self.compute_score(averages, correlations)

    def match_timestamps(self, time_buckets, df):
        """ Grab one measurement value for each five second window. """
        #print(time_buckets)
        #print(df)
        matched_data = []
        timestamps = (ts for ts in df.index)
        for time_bucket in time_buckets:
            missing = True
            while True:
                try:
                    ts = next(timestamps)
                except StopIteration:
                    break
                if ts < time_bucket + pd.Timedelta(seconds=5) and ts >= time_bucket:
                    missing = False
                    # the logic below applies when the database wrote multiple values for the same time.
                    if type(df.loc[ts]['value']) == pd.Series:
                        matched_data.append(df.loc[ts]['value'].iloc[0])
                    else:
                        matched_data.append(df.loc[ts]['value'])
                    break
                if ts > time_bucket + pd.Timedelta(seconds=5):
                    break
            if missing:
                matched_data.append(NaN)
        return pd.DataFrame(data=matched_data, index=time_buckets)


if __name__ == "__main__":
    diagnosis = Diagnosis(
            "hyperpilot/goddd/api_booking_service_request_latency_microseconds",
            "RAW",
            "DERIVED")
