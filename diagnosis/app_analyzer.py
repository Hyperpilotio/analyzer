import time
from collections import namedtuple

from diagnosis.derived_metrics import MetricsConsumer
from diagnosis.diagnosis import Diagnosis
from config import get_config

config = get_config()
WINDOW = int(config.get("ANALYZER", "CORRELATION_WINDOW"))
#logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))
METRIC_TYPES = set(["RAW", "DERIVED"])

class AppAnalyzer(object):
    def __init__(self, config):
        self.config = config

    def loop_all_app_metrics(self, start_time, batch_window):
        mc = MetricsConsumer("./diagnosis/derived_slo_metric_config.json", "./diagnosis/derived_metrics_config.json")
        d = Diagnosis()

        while True:
            end_time = start_time + batch_window
            derived_metrics = mc.get_derived_metrics(start_time, end_time)
            if len(derived_metrics.app_metrics.index) == 0:
                print("No more app metrics, exiting..")
                return
            metrics_with_cs = d.process_metrics(derived_metrics)
            print(metrics_with_cs)
            start_time += batch_window
            break

if __name__ == "__main__":
    aa = AppAnalyzer(None)
    print(WINDOW)
    aa.loop_all_app_metrics(1510593271081647191, WINDOW * 1000000000)

