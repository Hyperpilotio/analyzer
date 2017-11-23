import math

class ProblemsDetector(object):
    def __init__(self, config):
        self.config = config

    def convertNaN(self, value):
        if math.isnan(value):
            return 0.0
        return value

    def detect(self, metric_results):
        # Find top k metrics from metric results
        sorted_metrics = sorted(metric_results, key=lambda x: self.convertNaN(x.confidence_score), reverse=True)[:10]
        i = 1
        for m in sorted_metrics:
            print("Rank: " + str(i))
            print("Metric name: " + m.metric_name)
            print("Node name: " + m.node_name)
            print("Pod name: " + str(m.pod_name))
            print("Resource type: " + str(m.resource_type))
            print("Average: " + str(m.average))
            print("Correlation: " + str(m.correlation))
            print("Confidence score: " + str(m.confidence_score))
            i += 1
