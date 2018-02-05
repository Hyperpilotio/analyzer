from logger import get_logger
import time
from state import jobs

class UtilizationAnalyzer(object):
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(app_id, log_level=("UTILIZATION", "LOGLEVEL"))
        self.stop = False
        self.scheduled_time = time.strptime(config.get("UTILIZATION", "RUN_AT"), "%H:%M")

    def run_loop(self):
        self.logger.info("Starting utilization analyzer for cluster")

        last_status = jobs.get_job_status("utilization")
        if last_status:
            last_status["finished_at"]

        while self.stop != True:
            self.run_analysis()
            jobs.save_job_status("utilization", {"finished_at": int(time.time()), "job_name": "utilization"})

    def run_analysis(self):
        pass
