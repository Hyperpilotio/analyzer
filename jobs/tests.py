
from unittest import TestCase
from logger import get_logger
from config import get_config
from .runner import JobsRunner

logger = get_logger(__name__, log_level=("TEST", "LOGLEVEL"))

config = get_config()


def test_run(self, config, job_config, date):
    print("Running test job")

class JobRunnerTests(TestCase):
    def setUp(self):
        self.runner = JobsRunner(config)
        self.runner.run_loop()

    def tearDown(self):
        self.runner.stop_loop()

    def testAddJob(self):
        self.runner.add_job("test_job", "jobs.tests.test_run", {"schedule_at": "01:00"})
