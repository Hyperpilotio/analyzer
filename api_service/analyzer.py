from singleton_decorator import singleton
from config import get_config
from sizing_service.bayesian_optimizer_pool import BayesianOptimizerPool
from diagnosis.app_analyzer import DiagnosisTracker
from jobs.runner import JobsRunner

@singleton
class Analyzer(object):
    def __init__(self):
        self.config = get_config()
        self.diagnosis = DiagnosisTracker(self.config)
        self.bop = BayesianOptimizerPool()
        self.jobs = JobsRunner(self.config)
        self.jobs_context = self.jobs.run_loop()

        self.initialize_utilization_jobs()

    def initialize_utilization_jobs(self):
        self.jobs.add_job("utilization_node_cpu", "utilization.sizing_analyzer.node_cpu_job", {"schedule_at": "12:30"})
        self.jobs.add_job("utilization_node_memory", "utilization.sizing_analyzer.node_memory_job", {"schedule_at": "12:30"})
        self.jobs.add_job("utilization_container_cpu", "utilization.sizing_analyzer.container_cpu_job", {"schedule_at": "12:30"})
        self.jobs.add_job("utilization_container_memory", "utilization.sizing_analyzer.container_memory_job", {"schedule_at": "12:30"})
