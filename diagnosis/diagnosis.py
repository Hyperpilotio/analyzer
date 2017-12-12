import time
from collections import namedtuple


from diagnosis.derived_metrics import MetricsResults
from config import get_config
from logger import get_logger
import pandas as pd
from numpy import NaN, mean
from scipy.stats.stats import pearsonr

config = get_config()
WINDOW = int(config.get("ANALYZER", "CORRELATION_WINDOW_SECOND"))
DIAGNOSIS_INTERVAL = int(config.get("ANALYZER", "DIAGNOSIS_INTERVAL_SECOND"))
SAMPLE_INTERVAL = int(config.get("ANALYZER", "SAMPLE_INTERVAL_SECOND"))

logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))

class Diagnosis(object):
    def __init__(self):
        if config.get("ANALYZER", "SEVERITY_COMPUTE_TYPE") == "AREA":
            self.average_threshold = float(config.get("ANALYZER", "AREA_THRESHOLD"))
        else:
            self.average_threshold = float(config.get("ANALYZER", "FREQUENCY_THRESHOLD"))
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

    def filter_on_average(self, metric_results):
        return [result for result in metric_results if result.average > self.average_threshold]

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
                        for s in range(0, WINDOW, SAMPLE_INTERVAL)]

        app_df = self.match_timestamps(time_buckets, metrics.app_metric)
        for metric_result in metric_results:
            metric_result.df = self.match_timestamps(time_buckets, metric_result.df)

        metric_results = self.compute_averages(metric_results)
        l = len(metric_results)
        metric_results = self.filter_features(metric_results, filter_type="average")
        print("Filtered %d of %d features with average threshold %s%%" %
              (l - len(metric_results),
               l,
               self.average_threshold))
        metric_results = self.compute_correlations(app_df, metric_results)
        l = len(metric_results)
        metric_results = self.filter_features(metric_results, filter_type="correlation")
        print("Filtered %d of %d features with correlation significance threshold %s" %
              (l - len(metric_results),
               l,
               config.get("ANALYZER", "CORR_SIGNIF_THRESHOLD")))
        metric_results = self.compute_confidence_score(metric_results)

        return metric_results

    def match_timestamps(self, time_buckets, df):
        """ Get the average for a measurement value for each sampling interval. """
        matched_data = []
        timestamps = df.index
        i = 0
        for time_bucket in time_buckets:
            bucket_data = []
            while True:
                if i >= len(timestamps) - 1:
                    break
                ts = timestamps[i]
                if ts < time_bucket + pd.Timedelta(seconds=SAMPLE_INTERVAL) and ts >= time_bucket:
                    bucket_data.append(df.loc[ts]['value'])
                    i += 1
                elif ts >= time_bucket + pd.Timedelta(seconds=SAMPLE_INTERVAL):
                    break
                else:
                    # the timestamp is before the bucket.
                    i += 1
            if not bucket_data:
                matched_data.append(NaN)
            else:
                matched_data.append(mean(bucket_data))
        if len(matched_data) != len(time_buckets):
            print("we have a problem.")
        return pd.DataFrame(data=matched_data, index=time_buckets)
