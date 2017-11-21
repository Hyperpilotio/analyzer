import time
from collections import namedtuple


from diagnosis.metric_consumer import MetricConsumer
from config import get_config
from logger import get_logger

config = get_config()
BATCH_TIME = int(config.get("ANALYZER", "CORRELATION_BATCH_TIME"))
WINDOW = int(config.get("ANALYZER", "CORRELATION_WINDOW"))
logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))
tags = {"method": "request_routes", "summary": "quantile_90"}
METRIC_TYPES = set(["RAW", "DERIVED"])

class Diagnosis(object):
    def __init__(self, sl_metric, sl_metric_type, input_metric_type,
            start_time=None, end_time=None, sl_metric_json=None):
        if sl_metric_type not in METRIC_TYPES or input_metric_type not in METRIC_TYPES:
            raise ValueError("Supported metric types are RAW and DERIVED.")
        self.sl_metric = sl_metric
        if sl_metric_type == "DERIVED":
            if sl_metric_json == None:
                raise ValueError("Derived SL metric must be accompanied by SL metric json.")
        if sl_metric_type == "DERIVED" and input_metric_type == "RAW":
            raise ValueError("Combination of input and SL metric types not supported.")

        self.metric_consumer = MetricConsumer(sl_metric_type, input_metric_type)

    def get_averages(self):
        """ Get a Series with average value over time window for each feature. """
        return self.metric_consumer.input_df.mean(axis=0)

    def filter_features(self, series):
        return series[series > 50]
        
    def compute_correlation(self, df):
        pass

    def compute_score(self, df):
        pass


if __name__ == "__main__":
    diagnosis = Diagnosis("hyperpilot/goddd/api_booking_service_request_latency_microseconds",
            "RAW", "DERIVED")
    averages = diagnosis.get_averages()
    #print(averages.to_string())
    #print(diagnosis.filter_features(averages))

