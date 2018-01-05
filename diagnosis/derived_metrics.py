from influxdb import DataFrameClient
import json
import pandas as pd
import math
import requests
import logging

from config import get_config

config = get_config()
SAMPLE_INTERVAL = int(config.get("ANALYZER", "SAMPLE_INTERVAL_SECOND"))
NANOSECONDS_PER_SECOND = 1000000000
END_TIME = 1511980800000000000
WINDOW = 300

class WindowState(object):
    def __init__(self, window_seconds, threshold, sample_interval_seconds):
        '''
        e.g: window_seconds=30, threshold=10, sample_interval=5
        '''
        self.window = window_seconds * NANOSECONDS_PER_SECOND
        self.threshold = threshold
        self.sample_interval = sample_interval_seconds * NANOSECONDS_PER_SECOND
        self.values = []
        self.total_count = self.window / self.sample_interval

    def compute_severity(self, threshold, value):
        return max(value - threshold, 0.0)

    def compute_derived_value(self, new_time, new_value,
                compute_type=config.get("ANALYZER", "SEVERITY_COMPUTE_TYPE")):
        if math.isnan(new_value):
            new_value = 0.
        if len(self.values) > 0:
            while new_time - self.values[len(self.values) - 1][0] >= 2 * self.sample_interval:
                last_value = self.values[len(self.values) - 1]
                filled_time = last_value[0] + self.sample_interval
                self.values.append((filled_time, last_value[1], last_value[2]))

        severity = self.compute_severity(self.threshold, new_value)
        self.values.append((new_time, new_value, severity))

        window_begin_time = new_time - self.window + 1
        last_good_idx = -1
        idx = -1
        for time, value, severity in self.values:
            idx += 1
            if time >= window_begin_time:
                last_good_idx = idx
                break

        if last_good_idx != -1:
            self.values = self.values[last_good_idx:]

        if len(self.values) < self.total_count:
            return 0.0

        total = float(sum(p[1] for p in self.values))
        if total == 0.0:
            return 0.0

        severity_total = float(sum(p[2] for p in self.values))

        # derived metric value is percentage of area-above-threshold to total-area
        if compute_type == "AREA":
            return 100. * (severity_total / total)
        else:
            num_severe = len([p for p in self.values if p[2] > 0.0])
            return 100. * (num_severe/len(self.values))

class MetricResult(object):
    def __init__(self, df, raw_metric_name, metric_name, resource_type, node_name,
                 observation_window, threshold, threshold_type,
                 threshold_unit, pod_name=None):
        self.df = df
        self.metric_name = metric_name
        self.raw_metric_name = raw_metric_name
        self.node_name = node_name
        self.pod_name = pod_name
        self.resource_type = resource_type # e.g: network, cpu, memory
        self.observation_window = observation_window
        self.confidence_score = 0.0 # will be updated by diagnosis
        self.average = 0.0
        self.correlation = 0.0
        self.corr_p_value = 0.0
        self.threshold = threshold
        self.threshold_type = threshold_type
        self.threshold_unit = threshold_unit

class MetricsResults(object):
    def __init__(self, influx_client, is_derived=False):
        # for now, app and input data are either both raw or both derived.
        self.is_derived = is_derived
        self.app_metric = None
        self.deployment_id = ''

        # { metric name -> { node name -> metric result } }
        self.node_metrics = {}

        # { derived metric name -> { node name -> { pod name -> metric result } } }
        self.container_metrics = {}

        self.influx_client = influx_client

    def set_app_metric(self, app_metric, metric_name):
        if self.is_derived:
            self.influx_client.write_points(app_metric, metric_name)
        self.app_metric = app_metric

    def add_node_metric(self, raw_metric_name, metric_name, node_name, df, resource_type,
                        observation_window, threshold, threshold_type,
                        threshold_unit):
        if metric_name not in self.node_metrics:
            self.node_metrics[metric_name] = {}

        result = MetricResult(df, raw_metric_name, metric_name, resource_type, \
                              node_name, observation_window, \
                              threshold, threshold_type, threshold_unit)
        self.node_metrics[metric_name][node_name] = result

        if self.is_derived:
            tags = {"resource_type": resource_type, "deployment_id": self.deployment_id}
            self.influx_client.write_points(df.interpolate(), metric_name, tags)

    def add_container_metric(self, raw_metric_name, metric_name, node_name, pod_name, df,
                             resource_type, observation_window, threshold,
                             threshold_type, threshold_unit):
        if metric_name not in self.container_metrics:
            self.container_metrics[metric_name] = {}

        nodes = self.container_metrics[metric_name]
        if node_name not in nodes:
            nodes[node_name] = {}

        nodes[node_name][pod_name] = MetricResult(df, raw_metric_name,
                metric_name, resource_type, node_name, observation_window,
                threshold, threshold_type, threshold_unit, pod_name)
        if self.is_derived:
            tags = {"resource_type": resource_type, "deployment_id": self.deployment_id}
            self.influx_client.write_points(df.interpolate(), metric_name, tags)

    def add_metric(self, raw_metric_name, metric_name, is_container_metric, dfg, resource_type,
                  observation_window, threshold, threshold_type, threshold_unit):
        for df in dfg:
            if is_container_metric:
                node_col = df[1]["nodename"]
                if len(node_col) > 0:
                    nodename = node_col[0]
                    self.add_container_metric(raw_metric_name,
                        metric_name, nodename, df[0], df[1], resource_type,
                        observation_window, threshold, threshold_type,
                        threshold_unit)
            else:
                self.add_node_metric(raw_metric_name, metric_name, df[0], df[1], resource_type,
                                     observation_window, threshold, threshold_type,
                                     threshold_unit)


class MetricsConsumer(object):
    def __init__(self, app_slo, app_config_file, config_file, app_id):
        with open(config_file) as json_data:
            self.config = json.load(json_data)

        with open(app_config_file) as json_data:
            self.app_metric_config = json.load(json_data)

        if "metric" in app_slo:
            self.app_metric_config["metric"] = app_slo["metric"]

        if "threshold" in app_slo:
            self.app_metric_config["threshold"] = app_slo["threshold"]

        self.group_keys = {"intel/docker": "io.kubernetes.pod.name"}
        self.default_group_key = "nodename"
        influx_host = config.get("INFLUXDB", "HOST")
        influx_port = config.get("INFLUXDB", "PORT")
        influx_user = config.get("INFLUXDB", "USERNAME")
        influx_password = config.get("INFLUXDB", "PASSWORD")
        self.influx_client = DataFrameClient(
            influx_host,
            influx_port,
            influx_user,
            influx_password,
            config.get("INFLUXDB", "RAW_DB_NAME"))
        self.app_influx_client = DataFrameClient(
            influx_host,
            influx_port,
            influx_user,
            influx_password,
            config.get("INFLUXDB", "APP_DB_NAME"))
        self.deployment_id = ''

        derived_db = config.get("INFLUXDB", "DERIVED_METRIC_DB_NAME")
        self.derived_influx_client = DataFrameClient(
            influx_host,
            influx_port,
            influx_user,
            influx_password,
            derived_db)
        self.derived_influx_client.create_database(derived_db)
        self.derived_influx_client.create_retention_policy('derived_metric_policy', '5w', 1, default=True)
        self.logger = logging.getLogger(app_id)

    def get_app_threshold(self):
        threshold_config = self.app_metric_config["threshold"]
        value = float(threshold_config["value"])
        unit = threshold_config["unit"]
        # We app is measured in seconds
        if unit == "ms":
            value = value / 1000.
        return value

    def get_app_metric(self, start_time, end_time, is_derived=True):
        self.logger.info("Start processing app metric with app_metric_config %s" % self.app_metric_config)
        metric_name = self.app_metric_config["metric"]["name"]
        aggregation = self.app_metric_config["analysis"]["aggregation"]
        self.incident_type = self.app_metric_config["type"]
        self.incident_metric = self.app_metric_config["metric"]
        self.incident_threshold = self.app_metric_config["threshold"]

        time_filter = "WHERE time >= %d AND time <= %d" % (start_time, end_time)
        app_metric_query = (
            "SELECT time, %s(value) as value FROM \"%s\" %s" %
             (aggregation, metric_name, time_filter))

        if "tags" in self.app_metric_config["metric"]:
            tags = self.app_metric_config["metric"]["tags"]
            tags_filter = " AND " .join(["\"%s\"='%s'" % (tag["key"], tag["value"]) for tag in tags])
            app_metric_query += (" AND %s" % (tags_filter))

        app_metric_query += (" GROUP BY time(%ds) fill(none)" %
                             (SAMPLE_INTERVAL))
        self.logger.debug("app_metric_query = %s" %(app_metric_query))
        df = self.app_influx_client.query(app_metric_query)
        self.logger.debug("App metric query completed")
        if metric_name not in df:
            return None

        if is_derived == False:
            return df[metric_name]

        if df[metric_name] is not None:
            slo_state = WindowState(
                self.app_metric_config["analysis"]["observation_window_sec"],
                self.get_app_threshold(),
                SAMPLE_INTERVAL,
            )
            df[metric_name]["value"] = df[metric_name].apply(
                lambda row: slo_state.compute_derived_value(
                    row.name.value,
                    row.value
                ),
                axis=1,
            )
        return df[metric_name]

    def get_raw_metrics(self, start_time, end_time, app_metric=None):
        metrics_result = MetricsResults(self.derived_influx_client, is_derived=False)
        if app_metric is not None:
            metrics_result.set_app_metric(app_metric,
                                          self.app_metric_config["metric"]["name"])
        time_filter = "WHERE time >= %d AND time <= %d" % (start_time, end_time)

        for metric_config in self.config:
            metric_source = str(metric_config["metric_name"])
            group_name = self.default_group_key
            is_container_metric = False
            for k, v in self.group_keys.items():
                if k in metric_source:
                    group_name = v
                    is_container_metric = True
                    break

            if metric_source.startswith("/"):
                metric_source = metric_source[1:]

            # construct tags_filter if needed for this metric
            tags_filter = None
            if "tags" in metric_config:
                tags = metric_config["tags"]
                tags_filter = " AND " .join(["\"%s\"='%s'" % (k, v) for k, v in tags.items()])

            raw_metrics_query = ("SELECT * FROM \"%s\" %s" %
                                 (metric_source, time_filter))
            if tags_filter:
                raw_metrics_query += (" AND %s" % (tags_filter))
            raw_metrics = self.influx_client.query(raw_metrics_query)
            metrics_thresholds = {}
            raw_metrics_len = len(raw_metrics)
            if raw_metrics_len == 0:
                self.logger.info("Unable to find data for %s, skipping this metric..." %
                      (metric_source))
                continue

            for metric_group_name in raw_metrics[metric_source][group_name].unique():
                if not metric_group_name or metric_group_name == "":
                    self.logger.info("Unable to find %s in metric %s" %
                          (metric_group_name, metric_source))
                    continue

            df = raw_metrics[metric_source]
            dfg = df.groupby(group_name)
            metrics_result.add_metric(
                metric_source, metric_source, is_container_metric, dfg,
                metric_config["resource"], metric_config["analysis"]["observation_window_sec"],
                metric_config["threshold"]["value"], metric_config["threshold"]["type"],
                metric_config["threshold"]["unit"])
            return metrics_result


    def get_derived_metrics(self, start_time, end_time, app_metric=None):
        derived_metrics_result = MetricsResults(self.derived_influx_client, is_derived=True)
        if app_metric is not None:
            derived_metrics_result.set_app_metric(app_metric,
                self.app_metric_config["metric"]["name"] + "/" +
                self.app_metric_config["type"])
        node_metric_keys = "value,nodename,deploymentId"
        container_metric_keys = "value,\"io.kubernetes.pod.name\",nodename,deploymentId"
        time_filter = "WHERE time > %d AND time <= %d" % (start_time, end_time)

        self.logger.info("Start processing infrastructure metrics")
        for metric_config in self.config:
            metric_source = str(metric_config["metric_name"])
            group_name = self.default_group_key
            is_container_metric = False
            for k, v in self.group_keys.items():
                if k in metric_source:
                    group_name = v
                    is_container_metric = True
                    break

            metric_type = metric_config["type"]
            new_metric_name = metric_source + "/" + metric_type
            if metric_source.startswith("/"):
                metric_source = metric_source[1:]

            # construct tags_filter if needed for this metric
            tags_filter = None
            if "tags" in metric_config:
                tags = metric_config["tags"]
                tags_filter = " AND " .join(["\"%s\"='%s'" % (k, v) for k, v in tags.items()])

            # fetch raw metric values from influxdb
            raw_metrics = None
            if is_container_metric:
                raw_metrics_query = ("SELECT %s FROM \"%s\" %s" %
                    (container_metric_keys, metric_source, time_filter))
            else:
                raw_metrics_query = ("SELECT %s FROM \"%s\" %s" %
                    (node_metric_keys, metric_source, time_filter))
            if tags_filter:
                raw_metrics_query += (" AND %s" % (tags_filter))
            self.logger.debug("raw metrics for derived metrics query = %s" % (raw_metrics_query))
            raw_metrics = self.influx_client.query(raw_metrics_query)
            self.logger.debug("raw metrics query completed")
            if len(raw_metrics) == 0:
                self.logger.info("Unable to find data for %s; skipping this metric..." %
                      (metric_source))
                continue
            metric_df = raw_metrics[metric_source]
            metric_group_states = {}
            self.deployment_id = metric_df.loc[:,"deploymentId"][0]
            # fetch normalizer metric values if normalization is needed
            normalizer_metrics = None
            if "normalizer" in metric_config:
                normalizer = str(metric_config["normalizer"])
                new_metric_name = metric_source + "_normalized/" + metric_type
                if normalizer.startswith("/"):
                    normalizer = normalizer[1:]

                if is_container_metric:
                    normalizer_metrics_query = ("SELECT %s FROM \"%s\" %s" %
                        (container_metric_keys, normalizer, time_filter))
                else:
                    normalizer_metrics_query = ("SELECT %s FROM \"%s\" %s" %
                        (node_metric_keys, normalizer, time_filter))
                if tags_filter:
                    normalizer_metrics_query += (" AND %s" % (tags_filter))
                self.logger.debug("normalizer metrics query = %s" % (normalizer_metrics_query))
                normalizer_metrics = self.influx_client.query(normalizer_metrics_query)
                if len(normalizer_metrics) == 0:
                    self.logger.info("Unable to find data for normalizer %s; skipping metric %s..." %
                          (normalizer, metric_source))
                    continue
                normalizer_df = normalizer_metrics[normalizer]
                if normalizer_df["value"].max() == 0:
                    self.logger.info("All zero values in normalizer %s, skipping metric %s..." %
                          (normalizer, metric_source))
                    continue

            self.logger.debug("Converting raw metric %s\n  into derived metric %s" %
                  (metric_source, new_metric_name))

            # process metric values for each group
            # metric_group_name = nodename for node metrics, pod.name for container metrics
            for metric_group_name in raw_metrics[metric_source][group_name].unique():
                if not metric_group_name or metric_group_name == "":
                    self.logger.info("Unable to find %s in metric %s" %
                          (metric_group_name, metric_source))
                    continue
                if metric_group_name not in metric_group_states:
                    new_state = WindowState(
                        metric_config["observation_window_sec"],
                        metric_config["threshold"]["value"],
                        SAMPLE_INTERVAL,
                    )
                    metric_group_states[metric_group_name] = new_state

                metric_group_ind = metric_df.loc[
                    metric_df[group_name] == metric_group_name].index

                # perform normalization if needed for raw metrics in each group
                if normalizer_metrics:
                    normalizer_group_ind = normalizer_df.loc[
                            normalizer_df[group_name] == metric_group_name].index

                    if normalizer_df.loc[normalizer_group_ind,"value"].max() == 0:
                        self.logger.debug("Normalizer metric has all zeros for group %s; " %
                              (metric_group_name) +
                              "dropping this group from the raw metric...")
                        metric_df = metric_df.drop(metric_group_ind)
                        continue

                    if len(normalizer_group_ind) != len(metric_group_ind):
                        self.logger.warning("Normalizer does not have equal length as raw metric; " +
                              "adjusting...")
                        minlen = min(len(metric_group_ind), len(normalizer_group_ind))
                        metric_group_ind = metric_group_ind[:minlen]
                        normalizer_group_ind = normalizer_group_ind[:minlen]

                    metric_df.loc[metric_group_ind,"value"] = (
                        metric_df.loc[metric_group_ind,"value"] /
                        normalizer_df.loc[normalizer_group_ind,"value"].data
                    )

                # compute derived metric values using configured threshold info
                self.logger.debug("raw metric before applying threshold for group %s" % (metric_group_name))
                self.logger.debug(metric_df.loc[metric_group_ind,[group_name,"value"]].to_string(index=False))
                metric_df.loc[metric_group_ind,"value"] = metric_df.loc[metric_group_ind].apply(
                    lambda row: metric_group_states[row[group_name]].compute_derived_value(
                        row.name.value,
                        row.value
                        ),
                    axis=1,
                )
                self.logger.debug("derived metric after applying threshold for group %s" % (metric_group_name))
                self.logger.debug(metric_df.loc[metric_group_ind,[group_name,"value"]].to_string(index=False))

            metric_dfg = metric_df.groupby(group_name)
            derived_metrics_result.add_metric(
                metric_source, new_metric_name, is_container_metric, metric_dfg,
                metric_config["resource"], metric_config["observation_window_sec"],
                metric_config["threshold"]["value"], metric_config["threshold"]["type"],
                metric_config["threshold"]["unit"])

        return derived_metrics_result


if __name__ == '__main__':
    dm = MetricsConsumer(
            config.get("ANALYZER", "DERIVED_SLO_CONFIG"),
            config.get("ANALYZER", "DERIVED_METRIC_TEST_CONFIG"),
            "test_app_id")
    #derived_result = dm.get_derived_metrics(-9223372036854775806, 9223372036854775806)
    derived_result = dm.get_derived_metrics(END_TIME - WINDOW * NANOSECONDS_PER_SECOND, END_TIME)
    dm.logger.info("Derived Container metrics:")
    dm.logger.info(derived_result.container_metrics)
    dm.logger.info("Derived node metrics:")
    dm.logger.info(derived_result.node_metrics)
    dm.logger.info("Derived SLO metric:")
    dm.logger.info(derived_result.app_metric)
