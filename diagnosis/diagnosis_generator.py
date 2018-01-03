import json
from uuid import uuid1

from api_service.db import Database
from config import get_config
from logger import get_logger

config = get_config()
resultdb = Database(config.get("ANALYZER", "RESULTDB_NAME"))
TIMEOUT_WINDOW = int(config.get(
    "ANALYZER", "DIAGNOSIS_TIMEOUT_WINDOW_SECOND"))
remediations_config = config.get("ANALYZER", "REMEDIATIONS_CONFIG")
logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))

class DiagnosisGenerator(object):
    def __init__(self, config, app_config):
        self.config = config
        self.app_config = app_config
        self.app_deployments = []
        for microservice in self.app_config["microservices"]:
            if microservice["kind"] == "deployments":
                self.app_deployments.append(microservice["name"])
        with open(remediations_config) as json_data:
            self.remed_configs = json.load(json_data)


    def find_same_problem(self, problems, problem_desc):
        for problem in problems:
            if self.is_same_map(problem["description"], problem_desc):
                return problem

        return None

    def is_same_map(self, map1, map2):
        for k,v in map1.items():
            if k not in map2 or v != map2[k]:
                return False

        return True

    def is_app_pod(self, pod_name):
        for deployment in self.app_deployments:
            if pod_name.startswith(deployment):
                return True
        return False

    def map_problems(self, sorted_metrics, timestamp):
        problems = []
        i = 0
        for m in sorted_metrics:
            metrics = []
            metric_doc = {}

            metric_type = m.metric_name.split("/")[-1] # not directly used for now
            metric_name = m.metric_name[:len(
                m.metric_name) - len(metric_type) - 1]

            metric_doc["name"] = metric_name
            metric_doc["source"] = m.raw_metric_name
            metric_doc["threshold"] = {"type": m.threshold_type,
                                "value": m.threshold,
                                "unit": m.threshold_unit}
            metric_doc["analysis_result"] = {"severity": m.average,
                                      "correlation": m.correlation,
                                      "score": m.confidence_score}

            problem_description = {}
            if m.pod_name: # container metric
                if self.is_app_pod(m.pod_name):
                    problem_description["type"] = "container_over_utilization"
                else:
                    problem_description["type"] = "container_interference"
                problem_description["pod_name"] = m.pod_name
            else: # node metric
                problem_description["type"] = "node_resource_bottleneck"
            problem_description["node_name"] = m.node_name
            problem_description["resource"] = m.resource_type

            problem_doc = self.find_same_problem(problems, problem_description)
            if problem_doc: # problem already exists
                problem_doc["metrics"].append(metric_doc)
                problem_doc["overall_score"] = max(problem_doc["overall_score"], m.confidence_score)
            elif len(problems) == 3:
                continue
            else: # add a new problem
                problem_id = "problem" + "-" + str(uuid1())
                problem_doc = {"problem_id": problem_id,
                               "description": problem_description,
                               "metrics": [],
                               "overall_score": m.confidence_score,
                               "timestamp": timestamp}
                problem_doc["metrics"].append(metric_doc)
                problems.append(problem_doc)

            i += 1

        return problems


    def generate_remediations(self, nodes, problem):
        problem_type = problem["description"]["type"]
        resource_type = problem["description"]["resource"]
        remed_options = []

        for config in self.remed_configs:
            if problem_type == config["problem_type"]:
                if config["resource"] == [] or resource_type in config["resource"]:
                    remed_options = config["remediation_options"]

                    for option in remed_options:
                        for k in option["metadata"]:
                            option["metadata"][k] = problem["description"][k]

                        if "source_node" in option["spec"]:
                            my_node_name = problem["description"]["node_name"]
                            option["spec"]["source_node"] = my_node_name

                            # TODO: Have a more intelligent way to pick a target node.
                            # For now, just pick a node that's not your current running node.
                            target_node = ""
                            for node in nodes:
                                if node != my_node_name:
                                    target_node = node
                                    break

                            option["spec"]["destination_node"] = target_node
        return remed_options


    def process_features(self, sorted_metrics, nodes, app_id, app_name, incident_id, timestamp):
        # Construct top three problems from the top k metrics
        problems = self.map_problems(sorted_metrics, timestamp)
        logger.info("Top problems found:\n%s" % json.dumps(problems))

        # Construct diagnosis result and store it in resultdb
        diagnosis_doc = {"app_id": app_id,
                         "app_name": app_name,
                         "incident_id": incident_id,
                         "top_related_problems": [],
                         "timestamp": timestamp,
                         "timeout_window_sec": TIMEOUT_WINDOW}

        i = 1
        for problem in problems:
            problem_id = problem["problem_id"]
            remed_options = self.generate_remediations(nodes, problem)
            if len(remed_options) == 0:
                logger.warning("No remediation options can be found for %s" %
                       (problem_id))

            diagnosis_doc["top_related_problems"].append(
                {"id": problem_id,
                 "rank": i,
                 "remediation_options": remed_options})
            i += 1

        logger.info("Diagnosis result:\n%s" % json.dumps(diagnosis_doc))
        return (problems, diagnosis_doc)
