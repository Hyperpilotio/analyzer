import math
from uuid import uuid1

from api_service.db import Database
from config import get_config


config = get_config()
resultdb = Database(config.get("ANALYZER", "RESULTDB_NAME"))


class ProblemsDetector(object):
    def __init__(self, config):
        self.config = config

    def convertNaN(self, value):
        if math.isnan(value):
            return 0.0
        return value

    def detect(self, metric_results, deployment_id, app_name, incident_id,
               severity_type, threshold, timestamp):
        print("Feature rankings for deployment: " + deployment_id)
        CORRELATION_WINDOW = self.config.get(
            "ANALYZER", "CORRELATION_WINDOW_SECOND")

        # Find top k metrics from metric results
        sorted_metrics = sorted(metric_results, key=lambda x: self.convertNaN(
            x.confidence_score), reverse=True)[:10]
        i = 1
        problems = []
        for m in sorted_metrics:
            doc = {}
            print("Rank: " + str(i))
            print("Metric name: " + m.metric_name)
            print("Node name: " + m.node_name)
            print("Pod name: " + str(m.pod_name))
            print("Resource type: " + str(m.resource_type))
            print("Average severity (over last %d seconds): %f" %
                  (m.observation_window, m.average))
            print("Correlation (over last %s seconds): %f, p-value: %.2g" %
                  (CORRELATION_WINDOW, m.correlation, m.corr_p_value))
            print("Confidence score: " + str(m.confidence_score))
            i += 1
            if i > 4:
                continue
            metric_type = m.metric_name.split("/")[-1]
            metric_name = m.metric_name[:len(
                m.metric_name) - len(metric_type) - 1]
            doc["rank"] = i
            doc["problem_id"] = "problem" + "-" + str(uuid1())
            doc["type"] = metric_type
            doc["labels"] = {"node_name": m.node_name}
            if m.pod_name:
                doc["labels"]["pod_name"] = m.pod_name
            doc["metric"] = {"name": m.metric_name,
                             "type": m.resource_type}
            doc["threshold"] = {"type": m.threshold_type,
                                "value": m.threshold,
                                "unit": m.threshold_unit}
            doc["config"] = {"detection_window_sec": self.config.get(
                "ANALYZER", "AVERAGE_WINDOW_SECOND"),
                "severity_type": severity_type,
                "min_percentage": threshold}
            doc["analysis_result"] = {"severity": m.average,
                                      "correlation": m.correlation,
                                      "score": m.confidence_score}
            doc["timestamp"] = timestamp
            problems.append(doc)
        resultdb["problems"].insert(problems)
        diagnosis_doc = {"app_name": app_name,
                         "incident_id": incident_id,
                         "top_related_problems": [
                             {"id": p["problem_id"],
                              "remediation_options": []}
                             for p in problems],
                         "timestamp": timestamp,
                         "timeout_window_sec": self.config.get("ANALYZER",
                                                               "DIAGNOSIS_TIMEOUT_WINDOW")}
        resultdb["diagnoses"].insert_one(diagnosis_doc)
