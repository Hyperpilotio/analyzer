import time
from collections import namedtuple


from diagnosis.derived_metrics import MetricsResults
from config import get_config
from logger import get_logger

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
        print(type(metrics.app_metrics))#df
        print(type(metrics.node_metrics))#dict
        print(type(metrics.container_metrics))#dict
        #averages = self.get_averages()
        #correlations = self.compute_correlations()
        #result = MetricResult()
        #result.confidence_score = self.compute_score(averages, correlations)


if __name__ == "__main__":
    diagnosis = Diagnosis(
            "hyperpilot/goddd/api_booking_service_request_latency_microseconds",
            "RAW",
            "DERIVED")
