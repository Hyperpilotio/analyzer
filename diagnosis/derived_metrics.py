from influxdb import DataFrameClient
import json
import pandas as pd
import math
import requests

from config import get_config

NANOSECONDS_PER_SECOND = 1000000000
SAMPLE_INTERVAL_SECOND = 5
config = get_config()

class ThresholdState(object):
    def __init__(self, window_seconds, threshold, sample_interval_seconds):
        '''
        e.g: window_seconds=30, threshold=10, sample_interval=5
        '''
        self.window = window_seconds * NANOSECONDS_PER_SECOND
        self.threshold = threshold
        self.sample_interval = sample_interval_seconds * NANOSECONDS_PER_SECOND
        self.values = []
        self.total_count = (self.window / self.sample_interval) - 1

    def compute_severity(self, threshold, value):
        return value - threshold

    def compute(self, new_time, new_value):
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
            return 0

        total = float(sum(p[1] for p in self.values))
        if total == 0.0:
            return 0

        severity_total = float(sum(p[2] for p in self.values if p[2] > 0))

        return 100. * (severity_total / total)

class MetricResult(object):
    def __init__(self, df, metric_name, resource_type, node_name, pod_name=None):
        self.df = df
        self.metric_name = metric_name
        self.node_name = node_name
        self.pod_name = pod_name
        self.resource_type = resource_type # e.g: network, cpu, memory
        self.confidence_score = 0.0 # will be updated by diagnosis
        self.average = 0.0
        self.correlation = 0.0

class MetricsResults(object):
    def __init__(self, is_derived=False):
        # for now, app and input data are either both raw or both derived.
        self.is_derived = is_derived
        self.app_metrics = None

        # { metric name -> { node name -> metric result } }
        self.node_metrics = {}

        # { derived metric name -> { node name -> { pod name -> metric result } } }
        self.container_metrics = {}

        self.influx_client = DataFrameClient(
            config.get("INFLUXDB", "HOST"),
            config.get("INFLUXDB", "PORT"),
            config.get("INFLUXDB", "USERNAME"),
            config.get("INFLUXDB", "PASSWORD"),
            config.get("INFLUXDB", "DERIVED_METRIC_DB_NAME"))
        self.influx_client.create_retention_policy('derived_metric_policy', '2w', 1, default=True)

    def set_app_metrics(self, app_metrics, metric_name):
        if self.is_derived:
            self.influx_client.write_points(app_metrics, metric_name)
        self.app_metrics = app_metrics

    def add_node_metric(self, metric_name, node_name, df, resource_type):
        if metric_name not in self.node_metrics:
            self.node_metrics[metric_name] = {}
        self.node_metrics[metric_name][node_name] = MetricResult(df, metric_name, resource_type, node_name)
        if self.is_derived:
            tags = {"node_name": node_name, "resource_type": resource_type}
            self.influx_client.write_points(df.interpolate(), metric_name, tags)

    def add_container_metric(self, metric_name, node_name, pod_name, df, resource_type):
        if metric_name not in self.container_metrics:
            self.container_metrics[metric_name] = {}

        nodes = self.container_metrics[metric_name]
        if node_name not in nodes:
            nodes[node_name] = {}

        nodes[node_name][pod_name] = MetricResult(df, metric_name, resource_type, node_name, pod_name)
        if self.is_derived:
            tags = {"node_name": node_name, "pod_name": pod_name, "resource_type": resource_type}
            self.influx_client.write_points(df.interpolate(), metric_name, tags)
        #self.container_metrics[metric_name] = nodes

    def add_metric(self, metric_name, is_container_metric, dfg, resource_type):
        for df in dfg:
            if is_container_metric:
                node_col = df[1]["nodename"]
                if len(node_col) > 0:
                    nodename = node_col[0]
                    self.add_container_metric(
                        metric_name, nodename, df[0], df[1], resource_type)
            else:
                self.add_node_metric(metric_name, df[0], df[1], resource_type)


class MetricsConsumer(object):
    def __init__(self, app_config_file, config_file):
        with open(config_file) as json_data:
            self.config = json.load(json_data)

        with open(app_config_file) as json_data:
            self.app_metric_config = json.load(json_data)

        self.group_keys = {"intel/docker": "io.kubernetes.pod.name"}
        self.default_group_key = "nodename"
        influx_host = config.get("INFLUXDB", "HOST")
        influx_port = config.get("INFLUXDB", "PORT")
        influx_user = config.get("INFLUXDB", "USERNAME")
        influx_password = config.get("INFLUXDB", "PASSWORD")
        requests.post("http://%s:%s/query" % (influx_host, influx_port),
                params="q=CREATE DATABASE %s" % config.get("INFLUXDB", "DERIVED_METRIC_DB_NAME"))
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

    def get_app_metrics(self, start_time, end_time):
        metric_name = self.app_metric_config["metric_name"]
        summary = self.app_metric_config["summary"]
        aggregation = self.app_metric_config["aggregation"]
        query = "SELECT time, %s(value) as value FROM \"%s\" WHERE summary = '%s' AND time >= %d AND time <= %d GROUP BY time(%ds) fill(none)" \
                % (aggregation, metric_name, summary, start_time, end_time, SAMPLE_INTERVAL_SECOND)
        df = self.app_influx_client.query(query)
        if metric_name not in df:
            return None

        return df[metric_name]

    def get_raw_metrics(self, start_time, end_time):
        metrics_result = MetricsResults(is_derived=False)

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
                print("Unable to find data for %s, skipping..." %
                      (metric_source))
                continue

            for metric_group_name in raw_metrics[metric_source][group_name].unique():
                if not metric_group_name or metric_group_name == "":
                    print("Unable to find %s in metric %s" %
                          (metric_group_name, metric_source))
                    continue

            df = raw_metrics[metric_source]
            dfg = df.groupby(group_name)
            metrics_result.add_metric(
                metric_source, is_container_metric, dfg, metric_config["resource"])

            app_metrics = self.get_app_metrics(start_time, end_time)
            metrics_result.set_app_metrics(app_metrics, self.app_metric_config["metric_name"])
            return metrics_result

    # Convert NaN to 0.
    def convert_value(self, row):
        value = row["value"]
        if math.isnan(value):
            value = 0.
        return value

    def get_derived_metrics(self, start_time, end_time):
        derived_metrics_result = MetricsResults(is_derived=True)

        node_metric_keys = "value,nodename"
        container_metric_keys = "value,\"io.kubernetes.pod.name\",nodename"
        time_filter = "WHERE time >= %d AND time <= %d" % (start_time, end_time)

        print("Start processing infrastructure metrics")
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
            threshold = metric_config["threshold"]
            if metric_source.startswith("/"):
                metric_source = metric_source[1:]

            # construct tags_filter if needed for this metric
            tags_filter = None
            if "tags" in metric_config:
                tags = metric_config["tags"]
                tags_filter = " AND " .join(["\"%s\"='%s'" % (k, v) for k, v in tags.items()])

            normalizer_metrics = None
            if "normalizer" in metric_config:
                normalizer = str(metric_config["normalizer"])
                new_metric_name = metric_source + "_percent/" + metric_type
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
                #print("normalizer metrics query = %s" % (normalizer_metrics_query))
                normalizer_metrics = self.influx_client.query(normalizer_metrics_query)
                if len(normalizer_metrics) == 0:
                    print("Unable to find data for %s, skipping..." %
                          (normalizer))

            if is_container_metric:
                raw_metrics_query = ("SELECT %s FROM \"%s\" %s" %
                    (container_metric_keys, metric_source, time_filter))
            else:
                raw_metrics_query = ("SELECT %s FROM \"%s\" %s" %
                    (node_metric_keys, metric_source, time_filter))
            if tags_filter:
                raw_metrics_query += (" AND %s" % (tags_filter))
            #print("raw metrics query = %s" % (raw_metrics_query))
            raw_metrics = self.influx_client.query(raw_metrics_query)
            metrics_thresholds = {}
            raw_metrics_len = len(raw_metrics)
            if raw_metrics_len == 0:
                print("Unable to find data for %s, skipping..." %
                      (metric_source))
                continue
            elif normalizer_metrics and len(normalizer_metrics) != raw_metrics_len:
                print("Normalizer metrics do not have equal length as raw metrics")
                continue

            #print("Deriving data from %s into %s" %
            #      (metric_source, new_metric_name))

            # perform normalization and threshold checking for raw metrics in each group
            # metric_group_name = nodename for node metrics, pod.name for container metrics
            metric_df = raw_metrics[metric_source]
            for metric_group_name in raw_metrics[metric_source][group_name].unique():
                if not metric_group_name or metric_group_name == "":
                    print("Unable to find %s in metric %s" %
                          (metric_group_name, metric_source))
                    continue
                if metric_group_name not in metrics_thresholds:
                    state = ThresholdState(
                        metric_config["observation_window_sec"],
                        threshold["value"],
                        SAMPLE_INTERVAL_SECOND,
                    )
                    metrics_thresholds[metric_group_name] = state

                if normalizer_metrics:
                    # TODO: check for zeros in the normalizer_values
                    metric_group_ind = (metric_df[group_name] == metric_group_name)
                    normalizer_df = normalizer_metrics[normalizer]
                    normalizer_group_ind = (normalizer_df[group_name] == metric_group_name)

                    metric_df.loc[metric_group_ind,"value"] = (
                        100. * metric_df[metric_group_ind]["value"] /
                        normalizer_df[normalizer_group_ind]["value"].data)

            metric_df["value"] = metric_df.apply(
                lambda row: metrics_thresholds[row[group_name]].compute(row.name.value, self.convert_value(row)),
                axis=1,
            )

            metric_dfg = metric_df.groupby(group_name)
            derived_metrics_result.add_metric(
                new_metric_name, is_container_metric, metric_dfg, metric_config["resource"])

        print("Start processing app metrics")
        app_metrics = self.get_app_metrics(start_time, end_time)
        if app_metrics is not None:
            app_state = ThresholdState(
                self.app_metric_config["observation_window_sec"],
                self.app_metric_config["threshold"]["value"],
                SAMPLE_INTERVAL_SECOND,
            )
            app_metrics["value"] = app_metrics.apply(
                lambda row: app_state.compute(
                    row.name.value,
                    self.convert_value(row)
                ),
                axis=1,
            )
            derived_metrics_result.set_app_metrics(app_metrics, self.app_metric_config["metric_name"])

        return derived_metrics_result


if __name__ == '__main__':
    dm = MetricsConsumer(
            config.get("ANALYZER", "DERIVED_SLO_CONFIG"),
            config.get("ANALYZER", "DERIVED_METRIC_CONFIG"))
    #derived_result = dm.get_derived_metrics(-9223372036854775806, 9223372036854775806)
    derived_result = dm.get_derived_metrics(1510967911000482000, 1510967911000482000+300000000000)
    print("Derived Container metrics:")
    print(derived_result.container_metrics)
    print("Derived node metrics:")
    print(derived_result.node_metrics)
    print("Derived SLO metric:")
    print(derived_result.app_metrics)
