import time
from collections import namedtuple

from diagnosis.derived_metrics import MetricsConsumer
from diagnosis.diagnosis import Diagnosis
from diagnosis.problems_detector import ProblemsDetector
from config import get_config

config = get_config()
WINDOW = int(config.get("ANALYZER", "CORRELATION_WINDOW"))
NANOSECONDS_PER_SECOND = 1000000000

class AppAnalyzer(object):
    def __init__(self, config):
        self.config = config
        self.metrics_consumer = MetricsConsumer("./diagnosis/derived_slo_metric_config.json", "./diagnosis/derived_metrics_config.json")
        self.diagnosis = Diagnosis()
        self.problems_detector = ProblemsDetector(config)

    def loop_all_app_metrics(self, start_time, batch_window):
        while True:
            end_time = start_time + batch_window
            print("Processing metrics from start: %d, end: %d" % (start_time, end_time))
            derived_metrics = self.metrics_consumer.get_derived_metrics(start_time, end_time)
            if derived_metrics.app_metrics is None:
                print("No app metrics found, exiting..")
                return
            metrics_with_cs = self.diagnosis.process_metrics(derived_metrics)
            self.problems_detector.detect(metrics_with_cs)
            start_time += batch_window

if __name__ == "__main__":
    aa = AppAnalyzer(None)
    aa.loop_all_app_metrics(1510969424453702319 - 120 * 1000000000, WINDOW * 1000000000)
