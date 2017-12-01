import time
from collections import namedtuple


from diagnosis.derived_metrics import MetricsResults
from config import get_config
from logger import get_logger
import pandas as pd
from numpy import NaN
from scipy.stats.stats import pearsonr

config = get_config()
logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))
tags = {"method": "request_routes", "summary": "quantile_90"}
METRIC_TYPES = set(["RAW", "DERIVED"])

class Diagnosis(object):
    def __init__(self):
        return

    def compute_averages(self, metric_results):
        """ Get the average value over time window for each feature. """
        for result in metric_results:
            observation_end = result.df.index[-1]
            observation_start = observation_end - \
                    pd.Timedelta(seconds=result.observation_window)
            observation_window_df = result.df.loc[result.df.index >= observation_start]
            result.average = observation_window_df.mean(axis=0)[0]
        return metric_results

    def filter_features(self, metric_results, filter_type="average"):
        if filter_type == "average":
            return self.filter_on_average(metric_results)
        else:
            return self.filter_on_correlation(metric_results)

    def filter_on_average(self, metric_results,
                          threshold=float(config.get(
                                          "ANALYZER",
                                          "AVERAGE_FILTER_THRESHOLD"))):
        return [result for result in metric_results if result.average > threshold]

    def filter_on_correlation(self, metric_results,
                              threshold=float(config.get(
                                              "ANALYZER",
                                              "CORR_SIGNIF_THRESHOLD"))):
        return [result for result in metric_results
                                if result.corr_p_value < threshold]

    def compute_correlations(self, app_df, metric_results):
        for result in metric_results:
            result.correlation, result.corr_p_value = pearsonr(result.df.iloc[:,0].interpolate(),
                                                               app_df.iloc[:,0].interpolate())
        return metric_results

    def compute_confidence_score(self, metric_results):
        for result in metric_results:
            result.confidence_score = (result.average * result.correlation)
        return metric_results

    def process_metrics(self, metrics):
        metric_results = [metrics.node_metrics[metric_name][node_name] for
                      metric_name in metrics.node_metrics
                      for node_name in metrics.node_metrics[metric_name]] \
                        + \
                    [metrics.container_metrics[metric_name][node_name][pod_name]
                        for metric_name in metrics.container_metrics
                        for node_name in metrics.container_metrics[metric_name]
                        for pod_name in metrics.container_metrics[metric_name][node_name]]

        start_time = metrics.app_metric.index[0]
        time_buckets = [start_time + pd.Timedelta(seconds=s)
                        for s in range(0,
                                       int(config.get(
                                           "ANALYZER",
                                           "CORRELATION_WINDOW_SECOND")),
                                       int(config.get(
                                           "ANALYZER",
                                           "SAMPLE_INTERVAL_SECOND")))]
        app_df = self.match_timestamps(time_buckets, metrics.app_metric)
        for metric_result in metric_results:
            metric_result.df = self.match_timestamps(time_buckets, metric_result.df)

        metric_results = self.compute_averages(metric_results)
        l = len(metric_results)
        metric_results = self.filter_features(metric_results, filter_type="average")
        print("Filtered %d of %d features with average threshold %s%%." %
              (l - len(metric_results),
               l,
               config.get("ANALYZER", "AVERAGE_FILTER_THRESHOLD")))
        metric_results = self.compute_correlations(app_df, metric_results)
        l = len(metric_results)
        metric_results = self.filter_features(metric_results, filter_type="correlation")
        print("Filtered %d of %d features with correlation threshold %s." %
              (l - len(metric_results),
               l,
               config.get("ANALYZER", "CORR_SIGNIF_THRESHOLD")))
        metric_results = self.compute_confidence_score(metric_results)

        return metric_results

    def match_timestamps(self, time_buckets, df):
        """ Grab one measurement value for each sampling interval. """
        sample_interval = int(config.get("ANALYZER",
                                         "SAMPLE_INTERVAL_SECOND"))
        matched_data = []
        timestamps = df.index
        i = 0
        for time_bucket in time_buckets:
            missing = True
            while True:
                if i >= len(timestamps) - 1:
                    break
                ts = timestamps[i]
                if ts < time_bucket + pd.Timedelta(seconds=sample_interval) and ts >= time_bucket:
                    missing = False
                    # the logic below applies when the database wrote multiple values for the same time.
                    if type(df.loc[ts]['value']) == pd.Series:
                        matched_data.append(df.loc[ts]['value'].iloc[0])

                    else:
                        matched_data.append(df.loc[ts]['value'])
                    i += 1
                    break
                elif ts >= time_bucket + pd.Timedelta(seconds=sample_interval):
                    break
                else:
                    i += 1
            if missing:
                matched_data.append(NaN)
        return pd.DataFrame(data=matched_data, index=time_buckets)
