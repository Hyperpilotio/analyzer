import math
import time
import requests
import sys
import threading
import nanotime
import json
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
from state import apps as appstate
from state import results as resultstate

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
logger = get_logger(__name__, log_level=("ANALYZER", "LOGLEVEL"))

class DiagnosisTracker(object):
    def __init__(self, config):
        self.config = config
        self.apps = {}
        self.recover()

    def recover(self):
        # Find all apps with SLO and start diagnosis for them.
        all_apps = appstate.get_all_apps()
        for app in all_apps:
            if "slo" in app and app["state"] == "Active":
                self.run_new_app(app["app_id"], app)

    def stop_app(self, app_id):
        if app_id not in self.apps:
            logger.info("App id %s is not found in diagnosis tracker, skipping stop" % app_id)
            return

        analyzer, thread = self.apps[app_id]
        logger.info("Signaling app %s diagnosis loop to stop..." % app_id)
        analyzer.stop_loop()
        del(self.apps[app_id])

    def run_new_app(self, app_id, app_config):
        if app_id in self.apps:
            logger.info("App id %s is already running in diagnosis, skipping as we don't support update")
            return

        batch_window = WINDOW * NANOSECONDS_PER_SECOND
        sliding_interval = INTERVAL * NANOSECONDS_PER_SECOND
        delay_interval = DELAY_INTERVAL * NANOSECONDS_PER_SECOND
        logger.info("Starting diagnosis for app id %s, config: %s" % (app_id, str(app_config)))
        analyzer = AppAnalyzer(self.config, app_id, app_config, batch_window, sliding_interval, delay_interval)
        thread = threading.Thread(target=analyzer.run_loop)
        self.apps[app_id] = (analyzer, thread)
        thread.start()

# Diagnosis States
NO_APP_METRICS = 0
APP_HEALTHY = 1
METRICS_ALL_FILTERED = 2
APP_DIAGNOSED = 3

class DiagnosisResults(object):
    def __init__(self, state=0, problems=[], incident_doc=None, diagnosis_doc=None):
        self.state = state
        self.problems = problems
        self.incident_doc = incident_doc
        self.diagnosis_doc = diagnosis_doc

    def state_string(self):
        if self.state == NO_APP_METRICS:
            return "NO_APP_METRICS"
        elif self.state == APP_HEALTHY:
            return "APP_HEALTHY"
        elif self.state == METRICS_ALL_FILTERED:
            return "METRICS_ALL_FILTERED"
        elif self.state == APP_DIAGNOSED:
            return "APP_DIAGNOSED"

        return "Unknown"

    def write_results(self):
        for problem in self.problems:
            resultstate.create_problem(problem)

        if self.incident_doc:
            resultstate.create_incident(self.incident_doc)

        if self.diagnosis_doc:
            resultstate.create_diagnosis(self.diagnosis_doc)


class AppAnalyzer(object):
    def __init__(self, config, app_id, app_config, batch_window, sliding_interval, delay_interval):
        # Maps all currently running app name to threads
        self.config = config
        self.stop = False
        self.app_id = app_id
        self.app_config = app_config
        self.batch_window = batch_window
        self.sliding_interval = sliding_interval
        self.delay_interval = delay_interval
        self.metrics_consumer = MetricsConsumer(
            self.app_config["slo"],
            self.config.get("ANALYZER", "DERIVED_SLO_CONFIG"),
            self.config.get("ANALYZER", "DERIVED_METRICS_CONFIG"))
        self.features_selector = FeaturesSelector(config)
        self.diagnosis_generator = DiagnosisGenerator(config, app_config)
        influx_host = config.get("INFLUXDB", "HOST")
        influx_port = config.get("INFLUXDB", "PORT")
        influx_db = config.get("INFLUXDB", "RESULT_DB_NAME")
        self.influx_client = InfluxDBClient(
            influx_host,
            influx_port,
            config.get("INFLUXDB", "USERNAME"),
            config.get("INFLUXDB", "PASSWORD"),
            influx_db)
        self.influx_client.create_database(influx_db)
        self.influx_client.create_retention_policy('result_policy', '3w', 1, default=True)

    def diagnosis_cycle(self, start_time, end_time):
        results = DiagnosisResults()
        app_metric = self.metrics_consumer.get_app_metric(start_time, end_time, is_derived=True)
        if app_metric is None:
            logger.info("No app metric found, exiting diagnosis...")
            return results
        window = int(config.get("ANALYZER", "AVERAGE_WINDOW_SECOND")) * NANOSECONDS_PER_SECOND
        window_start = to_datetime(end_time - window, unit="ns")
        app_metric_mean = app_metric.loc[app_metric.index >= window_start].mean()
        if app_metric_mean["value"] < DIAGNOSIS_THRESHOLD:
            logger.info("Derived app metric mean: %f below threshold %f; skipping diagnosis..." %
                        (app_metric_mean["value"], DIAGNOSIS_THRESHOLD))
            results.state = APP_HEALTHY
            return results

        logger.info("Derived app metric mean: %f above threshold %f; starting diagnosis..." %
                    (app_metric_mean["value"], DIAGNOSIS_THRESHOLD))

        logger.debug("Getting derived metrics with app metric %s for app_id %s" % (app_metric, self.app_id))
        derived_metrics = self.metrics_consumer.get_derived_metrics(start_time, end_time,
                                                                            app_metric)
        logger.debug("Derived metrics completed for app_id %s" % self.app_id)

        # TODO: Capture actually running nodes by querying operator.
        # For now, Get all running nodes from node metrics map.
        first_node_metric = next(iter(derived_metrics.node_metrics.keys()))
        nodes = list(derived_metrics.node_metrics[first_node_metric].keys())

        app_name = self.app_config["name"]
        incident_id = "incident" + "-" + str(uuid1())
        incident_doc = {"incident_id": incident_id,
                        "app_id": self.app_id,
                        "type": self.metrics_consumer.incident_type,
                        "labels": {"app_name": app_name},
                        "metric": self.metrics_consumer.incident_metric,
                        "threshold": self.metrics_consumer.incident_threshold,
                        "severity": app_metric_mean["value"],
                        "timestamp": end_time,
                        "state": "Active"}
        logger.debug("Creating incident %s" % str(incident_doc))
        results.incident_doc = incident_doc

        logger.debug("Feature selector starting to process derived metrics..")
        filtered_metrics = self.features_selector.process_metrics(derived_metrics)
        if not filtered_metrics:
            logger.info("All %d features have been filtered." % self.features_selector.num_features)
            results.state = METRICS_ALL_FILTERED
            return results

        logger.debug("Writing filtered metrics results...")
        self.write_results(filtered_metrics, end_time, self.app_id, app_name, self.metrics_consumer.deployment_id)
        logger.debug("Filtered metrics writing completed")

        # Sort top k derived metrics based on conficent score
        sorted_metrics = sorted(filtered_metrics, key=lambda x: self.convert_nan(
            x.confidence_score), reverse=True)[:10]
        logger.info("Top related metrics for incident %s for application %s:" %
                    (incident_id, app_name))
        self.print_sorted_metrics(sorted_metrics)

        # Identify top problems and generate diagnosis result
        logger.info("\nStart generating diagnosis for incident %s for application %s:" %
                    (incident_id, app_name))
        problems, diagnosis_doc = self.diagnosis_generator.process_features(
            sorted_metrics, nodes, self.app_id, app_name, incident_id, end_time)

        results.problems = problems
        results.diagnosis_doc = diagnosis_doc
        results.state = APP_DIAGNOSED

        logger.debug("Diagnosis generation completed")
        return results

    def now_nano(self):
        return nanotime.now().nanoseconds()

    def stop_loop(self):
        self.stop = True

    def run_loop(self):
        logger.info("Starting live diagnosis run for application %s" % self.app_id)
        app_last_incident = None
        while self.stop != True:
            end_time =  self.now_nano() - self.delay_interval
            start_time = end_time - self.batch_window
            logger.info("Diagnosis cycle start: %f, end: %f", start_time, end_time)
            start_run_time = self.now_nano()
            diagnosis_results = self.diagnosis_cycle(start_time, end_time)
            if diagnosis_results.state == APP_DIAGNOSED:
                if app_last_incident:
                    logger.info("Skipping writing diagnosis results as app is diaganoised already.")
                else:
                    app_last_incident = diagnosis_results.incident_doc
                    diagnosis_results.write_results()
            else:
                if app_last_incident:
                    app_last_incident["state"] = "Resolved"
                    if resultstate.update_incident(app_last_incident["incident_id"], app_last_incident) == False:
                        logger.info("Unable to set app's last incident to resolve state")

                app_last_incident = None

            diagnosis_time = self.now_nano() - start_run_time
            logger.info("Diagnosis cycle took %s with result state %s" % (diagnosis_time, diagnosis_results.state_string()))
            sleep_time = ((self.sliding_interval - diagnosis_time) * 1.) / (NANOSECONDS_PER_SECOND * 1.)
            if sleep_time > 0.:
                logger.info("Sleeping for %f before next cycle" % sleep_time)
                time.sleep(sleep_time)

        logger.info("Diagnosis loop exiting for app id %s" % self.app_id)

    def loop_all_app_metrics(self, end_time):
        it = 1
        app_name = config.get("ANALYZER", "APP_NAME")
        while True:
            start_time = end_time - self.batch_window
            logger.info("\nIteration %d - Processing metrics from start: %d, to end: %d" %
                  (it, start_time, end_time))
            results = self.diagnosis_cycle(start_time, end_time)
            if results.state < METRICS_ALL_FILTERED:
                sliding_interval = INTERVAL * NANOSECONDS_PER_SECOND
                end_time += sliding_interval
                it += 1
                continue

            results.write_results()
            sliding_interval = INTERVAL * NANOSECONDS_PER_SECOND
            end_time += sliding_interval
            it += 1

    def convert_nan(self, value):
        if math.isnan(value):
            return 0.0
        return value

    def write_results(self, metrics, end_time, app_id, app_name, deployment_id):
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
            tags["app_id"] = app_id
            tags["app_name"] = app_name
            tags["deployment_id"] = deployment_id
            tags["resource_type"] = metric.resource_type
            tags["node_name"] = metric.node_name
            tags["pod_name"] = metric.pod_name
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
    with open("workloads/tech-demo-app.json") as f:
        aa = AppAnalyzer(config, "tech-demo", json.load(f), WINDOW * NANOSECONDS_PER_SECOND, INTERVAL * NANOSECONDS_PER_SECOND, DELAY_INTERVAL * NANOSECONDS_PER_SECOND)
        aa.loop_all_app_metrics(1513271903332233880)
    #aa.loop_all_app_metrics(1513062600000000000, WINDOW * NANOSECONDS_PER_SECOND, INTERVAL * NANOSECONDS_PER_SECOND)
