from concurrent.futures import ThreadPoolExecutor
from logger import get_logger
import rollbar
import importlib
import traceback
import threading
import time
import datetime
import schedule
from state import jobs

class JobState(object):
    PENDING = "Pending"
    SUBMITTED = "Submitted"
    RUNNING = "Running"
    FINISHED = "Finished"
    FAILED = "Failed"

    def init_from_map(state):
        return JobState(state["job_name"], state["job_function"], state["job_config"], \
                        state["schedule_at"], state["created_at"], state["finished_at"])

    def to_map(self):
        return {
            "job_name": self.job_name,
            "job_function": self.job_module + "." + self.job_function,
            "job_config": self.job_config,
            "schedule_at": self.schedule_at,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "last_error": self.last_error
        }

    def __init__(self, job_name, job_function, job_config, schedule_at, created_at, finished_at=None):
        self.job_name = job_name
        self.job_config = job_config
        self.job_module, self.job_function = job_function.rsplit(".", 1)
        self.schedule_at = schedule_at
        self.created_at = created_at
        self.running_at = None
        self.status = JobState.PENDING
        self.last_error = ""
        if finished_at:
            self.finished_at = int(finished_at)
        else:
            self.finished_at = None

"""
JobsRunner is responsible for scheduling and running periodic jobs.
It will store jobs and it's past execution state so it can also recover jobs after restart.
"""
class JobsRunner(object):
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(__name__, log_level=("JOBS", "LOGLEVEL"))
        self.stop = False
        self.job_states = {}
        workers = int(config.get("JOBS", "WORKER_SIZE"))
        self.worker_pool = ThreadPoolExecutor(max_workers=workers)
        self.running = None
        self.recover()

    def recover(self):
        job_states = jobs.get_job_states()
        now = int(time.time())
        recovered = 0
        for job_state in job_states:
            job_state = JobState.init_from_map(job_state)
            self.job_states[job_state.job_name] = job_state
            schedule_at = time.strptime(job_state.schedule_at, "%H:%M")
            finished_at = None
            if job_state.finished_at:
                finished_at = datetime.datetime.fromtimestamp(job_state.finished_at)
            created_at = datetime.datetime.fromtimestamp(job_state.created_at)

            # We want to start the jobs right away when we recover if we find that
            # the job didn't run longer than a day after it was created. We won't
            # try to backfill all past runs yet.
            last_completion_time = finished_at
            if not last_completion_time:
                last_completion_time = created_at

            if now - last_completion_time > datetime.timedelta(days=1):
                yesterday = now.date() + datetime.timedelta(days=-1)
                self.logger.info("Submitting job %s to be executed now as it has missed it's last execution" % job_state.job_name)
                self._submit_job(job_state, yesterday)

            self.schedule_job(job_state)
            recovered += 1
        self.logger.info("Job runner recovered %d jobs", recovered)

    def get_job_states(self):
        return self.job_states.values()

    def run_loop(self, interval=1):
        if self.running:
            self.logger.warning("Runner already running")
            return

        self.running = self._run_loop(interval)
        self.logger.info("Job runner is running")

    def stop_loop(self):
        if not self.running:
            self.logger.warning("Runner is not running")
            return

        self.running.set()
        self.running = None

    def _run_loop(self, interval):
        cease_continuous_run = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                while not cease_continuous_run.is_set():
                    schedule.run_pending()
                    time.sleep(interval)

        continuous_thread = ScheduleThread()
        continuous_thread.start()
        return cease_continuous_run

    def job_finish(self, fn, job_state):
        job_state.running_at = None
        job_state.finished_at = job_state.running_at
        if fn.cancelled():
            self.logger.warning("Job %s cancelled" % job_state.job_name)
        elif fn.done():
            error = fn.exception()
            if error:
                self.logger.warning("Job %s failed: %s" % (job_state.job_name, error))
            else:
                self.logger.info("Job %s completed" % job_state.job_name)

    def _run_job(logger, config, function, job_state, current_date):
        job_state.running_at = int(time.time())
        job_state.status = JobState.RUNNING
        job_failed = False
        attempts = 0

        # TODO: Make attempt count configurable
        while attempts <= 3:
            attempts += 1

            logger.info("Running job %s with attempt %d" % (job_state.job_name, attempts))
            job_failed = False
            error = None
            try:
                error = function(config, job_state.job_config, current_date)
            except Exception as e:
                logger.warning("Job %s failed with error: %s" % (job_state.job_name, e))
                traceback.print_exc()
                rollbar.report_exc_info()
                rollbar.report_message("Job %s failed with error: %s" % (job_state.job_name, e), "warning")
                job_failed = True

            if error:
                job_failed = True
                logger.warning("Job %s failed with error: %s" % (job_state.job_name, error))

            if job_failed == False:
                job_state.status = JobState.FINISHED
                return

        job_state.status = JobState.FAILED
        job_state.last_error = error
        logger.warning("Unable to run job after 3 attempts, aborting job")
        self.save_job_state(job_state)

    def _submit_job(self, job_state, current_date=datetime.datetime.now().date()):
        self.logger.info("Submitting new job %s to be executed" % job_state.job_name)

        try:
            module = importlib.import_module(job_state.job_module)
            function = getattr(module, job_state.job_function)
        except Exception as e:
            self.logger.warning("Job %s function cannot be referenced: %s" % (job_state.job_name, e))
            rollbar.report_message("Job %s function cannot be referenced: %s" % (job_state.job_name, e), "warning")
            return

        job_state.status = JobState.SUBMITTED
        f = self.worker_pool.submit(JobsRunner._run_job, self.logger, self.config, function, job_state, current_date)
        f.add_done_callback(lambda fn: self.job_finish(fn, job_state))


    def add_job(self, job_name, job_function, job_config):
        """
        Adds a new job to be scheduled and run by the job runner.
        Job func is assumed to be a function that accepts config and job_config.
        """

        if job_name in self.job_states:
            self.logger.warning("Job %s already exists while adding, skipping add." % job_name)
            return

        job_state = JobState(job_name, job_function, job_config, job_config["schedule_at"], int(time.time()))
        self.job_states[job_name] = job_state
        self.schedule_job(job_state)

    def schedule_job(self, job_state):
        schedule.every(1).days.at(job_state.schedule_at).do(self._submit_job, job_state).tag(job_state.job_name)
        #schedule.every(5).seconds.do(self._submit_job, job_state).tag(job_state.job_name)

    def save_job_state(self, job_state):
        jobs.save_job_state(job_state.job_name, job_state.to_map())
