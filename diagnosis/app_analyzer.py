import math
import time
import requests
import sys
import threading
import nanotime
from collections import namedtuple
from math import isnan
from pandas import to_datetime
from uuid import uuid1

from influxdb import InfluxDBClient

from diagnosis.derived_metrics import MetricsConsumer
from diagnosis.features_selector import FeaturesSelector
from diagnosis.diagnosis_generator import DiagnosisGenerator
from config import get_config
from api_service.db import Database
from logger import get_logger

config = get_config()
WINDOW = int(config.get("ANALYZER", "CORRELATION_WINDOW_SECOND"))
INTERVAL = int(config.get("ANALYZER", "DIAGNOSIS_INTERVAL_SECOND"))
DELAY_INTERVAL = int(config.get("ANALYZER", "DELAY_INTERVAL_SECOND"))
AVERAGE_WINDOW = int(config.get("ANALYZER", "AVERAGE_WINDOW_SECOND"))
severity_compute_type = config.get("ANALYZER", "SEVERITY_COMPUTE_TYPE")
if severity_compute_type == "AREA":
    DIAGNOSIS_THRESHOLD = float(config.get("ANALYZER", "AREA_THRESHOLD"))
else:
    DIAGNOSIS_THRESHOLD = float(config.get("ANALYZER", "FREQUENCY_THRESHOLD"))
NANOSECONDS_PER_SECOND = 1000000000
RESULTDB = Database(config.get("ANALYZER", "RESULTDB_NAME"))
incidents_collection = config.get("ANALYZER", "INCIDENT_COLLECTION")
logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))


class AppAnalyzer(object):
    def __init__(self, config):
        self.config = config
        self.stop = False
        self.metrics_consumer = MetricsConsumer(
            self.config.get("ANALYZER", "DERIVED_SLO_CONFIG"),
            self.config.get("ANALYZER", "DERIVED_METRICS_CONFIG"))
        self.features_selector = FeaturesSelector(config)
        self.diagnosis_generator = DiagnosisGenerator(config)
        influx_host = config.get("INFLUXDB", "HOST")
        influx_port = config.get("INFLUXDB", "PORT")
        influx_db = config.get("INFLUXDB", "RESULT_DB_NAME")
        requests.post("http://%s:%s/query" % (influx_host, influx_port), params="q=CREATE DATABASE %s" % influx_db)
        self.influx_client = InfluxDBClient(
            influx_host,
            influx_port,
            config.get("INFLUXDB", "USER"),
            config.get("INFLUXDB", "PASSWORD"),
            influx_db)
        self.influx_client.create_retention_policy('result_policy', '3w', 1, default=True)

    def diagnosis_cycle(self, app_name, start_time, end_time):
        app_metric = self.metrics_consumer.get_app_metric(start_time, end_time, is_derived=True)
        if app_metric is None:
            logger.info("No app metric found, exiting diagnosis...")
            return False
        window = int(config.get("ANALYZER", "AVERAGE_WINDOW_SECOND")) * NANOSECONDS_PER_SECOND
        window_start = to_datetime(end_time - window, unit="ns")
        app_metric_mean = app_metric.loc[app_metric.index >= window_start].mean()
        if app_metric_mean["value"] < DIAGNOSIS_THRESHOLD:
            logger.info("Derived app metric mean: %f below threshold %f; skipping diagnosis..." %
                        (app_metric_mean["value"], DIAGNOSIS_THRESHOLD))
            return False
        else:
            logger.info("Derived app metric mean: %f above threshold %f; starting diagnosis..." %
                        (app_metric_mean["value"], DIAGNOSIS_THRESHOLD))

        derived_metrics = self.metrics_consumer.get_derived_metrics(start_time, end_time,
                                                                            app_metric)
        incident_id = "incident" + "-" + str(uuid1())
        incident_doc = {"incident_id": incident_id,
                        "type": self.metrics_consumer.incident_type,
                        "labels": {"app_name": app_name},
                        "metric": self.metrics_consumer.incident_metric,
                        "threshold": self.metrics_consumer.incident_threshold,
                        "severity": app_metric_mean["value"],
                        "timestamp": end_time}
        RESULTDB[incidents_collection].insert_one(incident_doc)

        filtered_metrics = self.features_selector.process_metrics(derived_metrics)
        if not filtered_metrics:
            logger.info("All %d features have been filtered." % self.features_selector.num_features)
            it += 1
            return True

        self.write_results(filtered_metrics, end_time, app_name,
                           self.metrics_consumer.deployment_id)

        # Sort top k derived metrics based on conficent score
        sorted_metrics = sorted(filtered_metrics, key=lambda x: self.convert_nan(
            x.confidence_score), reverse=True)[:10]
        logger.info("Top related metrics for incident %s for application %s:" %
                    (incident_id, app_name))
        self.print_sorted_metrics(sorted_metrics)

        # Identify top problems and generate diagnosis result
        logger.info("\nStart generating diagnosis for incident %s for application %s:" %
                    (incident_id, app_name))
        self.diagnosis_generator.process_features(
            sorted_metrics, app_name, incident_id, end_time)

        return True

    def now_nano(self):
        return nanotime.now().nanoseconds()

    def run_daemon(self, *args):
        thread = threading.Thread(target=self.run, args=args)
        thread.daemon = True
        thread.start()

    def run(self, batch_window, sliding_interval, delay_interval):
        app_name = config.get("ANALYZER", "APP_NAME")
        logger.info("Starting live diagnosis run for application %s" % app_name)
        end_time =  self.now_nano() - delay_interval
        start_time = end_time - batch_window
        while self.stop != True:
            start_run_time = self.now_nano()
            logger.info("Diagnosis cycle start: %f, end: %f", start_time, end_time)
            self.diagnosis_cycle(app_name, start_time, end_time)
            diagnosis_time = self.now_nano() - start_run_time
            logger.info("Diagnosis cycle took %s" % diagnosis_time)
            sleep_time = ((sliding_interval - diagnosis_time) * 1.) / (NANOSECONDS_PER_SECOND * 1.)
            if sleep_time > 0:
                logger.info("Sleeping for %f before next cycle" % sleep_time)
                time.sleep(sleep_time)

    def loop_all_app_metrics(self, end_time, batch_window, sliding_interval):
        it = 1
        app_name = config.get("ANALYZER", "APP_NAME")
        while True:
            start_time = end_time - batch_window
            logger.info("\nIteration %d - Processing metrics from start: %d, to end: %d" %
                  (it, start_time, end_time))
            if self.diagnosis_cycle(app_name, start_time, end_time) == False:
                return
            end_time += sliding_interval
            it += 1

    def convert_nan(self, value):
        if math.isnan(value):
            return 0.0
        return value

    def write_results(self, metrics, end_time, app_name, deployment_id):
        points_json = []
        for metric in metrics:
            point_json = {}
            # In Influx, measurements in two different databases cannot have the same name.
            # Below, we avoid a name conflict with derivedmetrics database.
            point_json["measurement"] = metric.metric_name + "_result"
            point_json["time"] = end_time
            fields = {}
            fields["average"] = float(metric.average)
            fields["correlation"] = float(metric.correlation)
            fields["confidence_score"] = float(metric.confidence_score)
            for field in ["average", "correlation", "confidence_score"]:
                if isnan(fields[field]):
                    fields[field] = None
            if not any(fields[field] for field in ["average", "correlation", "confidence_score"]):
                # InfluxDB requires non-empty data points.
                continue
            point_json["fields"] = fields
            tags = {}
            tags["app_name"] = app_name
            tags["deployment_id"] = deployment_id
            tags["resource_type"] = metric.resource_type
            tags["node_name"] = metric.node_name
            tags["pod_name"] = metric.pod_name
            tags
            point_json["tags"] = tags
            points_json.append(point_json)

        self.influx_client.write_points(points_json)


    def print_sorted_metrics(self, sorted_metrics):
        i = 1
        for m in sorted_metrics:
            logger.info("\nRank: " + str(i) + "\n" +
                        "Metric name: " + m.metric_name + "\n" +
                        "Node name: " + m.node_name + "\n" +
                        "Pod name: " + str(m.pod_name) + "\n" +
                        "Resource type: " + str(m.resource_type) + "\n" +
                        "Average severity (over last %d seconds): %f" %
                          (AVERAGE_WINDOW, m.average) + "\n" +
                        "Correlation (over last %s seconds): %f, p-value: %.2g" %
                          (WINDOW, m.correlation, m.corr_p_value) + "\n" +
                        "Confidence score: " + str(m.confidence_score) + "\n")

            i += 1


if __name__ == "__main__":
    aa = AppAnalyzer(config)
    if len(sys.argv) > 1:
        aa.run(WINDOW * NANOSECONDS_PER_SECOND, INTERVAL * NANOSECONDS_PER_SECOND, DELAY_INTERVAL * NANOSECONDS_PER_SECOND)
    else:
        aa.loop_all_app_metrics(1511980830000000000, WINDOW * NANOSECONDS_PER_SECOND, INTERVAL * NANOSECONDS_PER_SECOND)
    #aa.loop_all_app_metrics(1513062600000000000, WINDOW * NANOSECONDS_PER_SECOND, INTERVAL * NANOSECONDS_PER_SECOND)
