import time
from collections import namedtuple


from diagnosis.derived_metrics import MetricsResults
from config import get_config
from logger import get_logger
import pandas as pd
from numpy import NaN

config = get_config()
logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))
tags = {"method": "request_routes", "summary": "quantile_90"}
METRIC_TYPES = set(["RAW", "DERIVED"])

class Diagnosis(object):
    def __init__(self):
        return

    def set_averages(self, metric_results):
        """ Get the average value over time window for each feature. """
        for result in metric_results:
            result.average = result.df.mean(axis=0)
        return metric_results

    def filter_features(self, series, threshold=None):
        return series[series > threshold]

    def set_correlations(self, app_df, metric_results):
        for result in metric_results:
            result.correlation = result.df.corrwith(app_df)
        return metric_results

    def set_confidence_score(self, metric_results):
        for result in metric_results:
            result.confidence_score = (result.average * result.correlation)[0].item()
        return metric_results

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

        metric_results = self.set_averages(metric_results)
        metric_results = self.set_correlations(app_df, metric_results)
        metric_results = self.set_confidence_score(metric_results)
        return metric_results

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
