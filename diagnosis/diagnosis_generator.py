import json
from uuid import uuid1

from api_service.db import Database
from config import get_config

config = get_config()
resultdb = Database(config.get("ANALYZER", "RESULTDB_NAME"))
TIMEOUT_WINDOW = int(config.get(
    "ANALYZER", "DIAGNOSIS_TIMEOUT_WINDOW_SECOND"))
problems_collection = config.get("ANALYZER", "PROBLEM_COLLECTION")
diagnoses_collection = config.get("ANALYZER", "DIAGNOSIS_COLLECTION")
pods_json_file = "./diagnosis/tech-demo-pods.json"
remediations_config = config.get("ANALYZER", "REMEDIATIONS_CONFIG")


class DiagnosisGenerator(object):
    def __init__(self, config):
        self.config = config

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

    def map_problems(self, sorted_metrics, timestamp):

        # Find the list of current pods in the application
        with open(pods_json_file) as json_data:
            app_pods = json.load(json_data)
       
        problems = []
        i = 0
        for m in sorted_metrics:
            metrics = []
            metric_doc = {}

            metric_type = m.metric_name.split("/")[-1] # not directly used for now
            metric_name = m.metric_name[:len(
                m.metric_name) - len(metric_type) - 1]

            metric_doc["name"] = metric_name
            metric_doc["threshold"] = {"type": m.threshold_type,
                                "value": m.threshold,
                                "unit": m.threshold_unit}
            metric_doc["analysis_result"] = {"severity": m.average,
                                      "correlation": m.correlation,
                                      "score": m.confidence_score}

            problem_description = {}
            if m.pod_name: # container metric
                if m.pod_name in app_pods:
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
            elif len(problems) == 3:
                continue
            else: # add a new problem
                problem_id = "problem" + "-" + str(uuid1())
                problem_doc = {"problem_id": problem_id,
                               "description": problem_description,
                               "metrics": [],
                               "timestamp": timestamp}
                problem_doc["metrics"].append(metric_doc)
                problems.append(problem_doc)
           
            i += 1

        return problems    


    def generate_remediations(self, problem):
        with open(remediations_config) as json_data:
            remed_configs = json.load(json_data)
       
        problem_type = problem["description"]["type"]
        resource_type = problem["description"]["resource"]
        remed_options = []

        for config in remed_configs:
            if problem_type == config["problem_type"]:
                if config["resource"] == [] or resource_type in config["resource"]:
                    remed_options = config["remediation_options"]

                    for option in remed_options:
                        for k in option["metadata"]:
                            option["metadata"][k] = problem["description"][k]

                        if "source_node" in option["spec"]:
                            option["spec"]["source_node"] = problem["description"]["node_name"]

        return remed_options


    def process_features(self, sorted_metrics, app_name, incident_id, timestamp):

        # Construct top three problems from the top k metrics 
        problems = self.map_problems(sorted_metrics, timestamp) 
        print("Top three problems found:\n", problems)
        resultdb[problems_collection].insert(problems)
      
        # Construct diagnosis result and store it in resultdb
        diagnosis_doc = {"app_name": app_name,
                         "incident_id": incident_id,
                         "top_related_problems": [],
                         "timestamp": timestamp,
                         "timeout_window_sec": TIMEOUT_WINDOW}

        i = 1
        for problem in problems:
            problem_id = problem["problem_id"]
            remed_options = self.generate_remediations(problem)
            if len(remed_options) == 0:
                print("WARNING: No remediation options can be found for %s" %
                       (problem_id))

            diagnosis_doc["top_related_problems"].append(
                {"id": problem_id,
                 "rank": i,
                 "remediation_options": remed_options})
            i += 1

        print("Diagnosis result:\n", diagnosis_doc)
        resultdb[diagnoses_collection].insert_one(diagnosis_doc)
