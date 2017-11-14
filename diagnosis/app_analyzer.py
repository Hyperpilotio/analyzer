import time

from diagnosis.metric_consumer import MetricConsumer
from config import get_config

config = get_config()
BATCH_TIME = int(config.get("ANALYZER", "CORRELATION_BATCH_TIME"))
WINDOW = int(config.get("ANALYZER", "CORRELATION_WINDOW"))
logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))


if __name__ == "__main__":
    # for testing purposes: 
    mc = MetricConsumer()
    # with running snap collectors:
    # mc = Metric_Consumer(end_time=now, start_time=now-5min)

    while True:
        time.sleep(WINDOW)
        mc.shift_and_update()
        mc.write_result()
        logger.info("Wrote correlation coefficient to result db.")
