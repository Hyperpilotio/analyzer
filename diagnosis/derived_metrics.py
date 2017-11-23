from influxdb import DataFrameClient
import json
import pandas as pd
import math

NANOSECONDS_PER_SECOND = 1000000000
SAMPLE_INTERVAL_SECOND = 5

class ThresholdState(object):
    def __init__(self, window_seconds, threshold, bound_type, sample_interval_seconds):
        '''
        e.g: window_seconds=30, threshold=10, bound_type=UB, sample_interval=5
        '''
        self.window = window_seconds * NANOSECONDS_PER_SECOND
        self.threshold = threshold
        self.bound_type = bound_type
        self.sample_interval = sample_interval_seconds * NANOSECONDS_PER_SECOND
        self.last_was_hit = False
        self.hits = []
        self.total_count = self.window / self.sample_interval

    def compare_value(self, bound_type, threshold, value):
        if bound_type == "UB":
            return value - threshold >= 0
        else:
            return value - threshold <= 0

    def compute(self, new_time, new_value):
        if self.last_was_hit and len(self.hits) > 0:
            if new_time - self.hits[len(self.hits) - 1] >= 2 * self.sample_interval:
                filled_hit_time = self.hits[len(
                    self.hits) - 1] + self.sample_interval
                self.hits.append(filled_hit_time)

        if self.compare_value(self.bound_type, self.threshold, new_value):
            self.hits.append(new_time)
            self.last_was_hit = True
        else:
            self.last_was_hit = False

        window_begin_time = new_time - self.window + 1
        last_good_idx = len(self.hits)
        idx = -1
        for hit in self.hits:
            idx += 1
            if hit >= window_begin_time:
                last_good_idx = idx
                break

        self.hits = self.hits[last_good_idx:]

        return 100. * (float(len(self.hits)) / float(self.total_count))

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
    def __init__(self):
        self.app_metrics = None

        # { metric name -> { node name -> metric result } }
        self.node_metrics = {}

        # { derived metric name -> { node name -> { pod name -> metric result } } }
        self.container_metrics = {}

    def set_app_metrics(self, app_metrics):
        self.app_metrics = app_metrics

    def add_node_metric(self, metric_name, node_name, df, resource_type):
        if metric_name not in self.node_metrics:
            self.node_metrics[metric_name] = {}

        self.node_metrics[metric_name][node_name] = MetricResult(df, metric_name, resource_type, node_name)

    def add_container_metric(self, metric_name, node_name, pod_name, df, resource_type):
        if metric_name not in self.container_metrics:
            self.container_metrics[metric_name] = {}

        nodes = self.container_metrics[metric_name]
        if node_name not in nodes:
            nodes[node_name] = {}

        nodes[node_name][pod_name] = MetricResult(df, metric_name, resource_type, node_name, pod_name)
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
        # TODO(tnachen): influx connection based on config
        self.influx_client = DataFrameClient(
            "localhost",
            8086,
            "root",
            "root",
            "snapaverage")
        self.app_influx_client = DataFrameClient(
            "localhost",
            8086,
            "root",
            "root",
            "snap")

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
        metrics_result = MetricsResults()
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

            raw_metrics_query = ("SELECT * FROM \"%s\" "
                "WHERE time >= %d "
                "AND time <= %d" % (metric_source, start_time, end_time))
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
            metrics_result.set_app_metrics(app_metrics)
            return metrics_result

    # Convert NaN to 0.
    def convert_value(self, row):
        value = row["value"]
        if math.isnan(value):
            value = 0.
        return value

    def get_derived_metrics(self, start_time, end_time):
        derived_metrics_result = MetricsResults()

        node_metric_keys = "value,nodename,source"
        container_metric_keys = "value,\"docker_id\",\"io.kubernetes.container.name\",\"io.kubernetes.pod.name\",nodename,source"
        time_filter = " WHERE time >= %d AND time <= %d" % (start_time, end_time)

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
            normalizer_node_map = {}
            normalizer = ""
            if "normalizer" in metric_config:
                normalizer = str(metric_config["normalizer"])
                if normalizer.startswith("/"):
                    normalizer = normalizer[1:]
                normalizer_metrics_query = ("SELECT * FROM \"%s\" "
                    "WHERE time >= %d "
                    "AND time <= %d" % (normalizer, start_time, end_time))
                if tags_filter:
                    normalizer_metrics_query += (" AND %s" % (tags_filter))
                normalizer_metrics = self.influx_client.query(normalizer_metrics_query)
                normalizer_metrics_len = len(normalizer_metrics)
                if normalizer_metrics_len == 0:
                    print("Unable to find data for %s, skipping..." %
                          (normalizer))
                else:
                    normalizer_df = normalizer_metrics[normalizer]
                    normalizer_dfg = normalizer_df.groupby("nodename").first()
                    for node_name in normalizer_dfg.value.index:
                        if 1 in normalizer_dfg.value:
                            normalizer_node_map[node_name] = normalizer_dfg.value[1]

            if is_container_metric:
                raw_metrics_query = ("SELECT %s FROM \"%s\""
                    % (container_metric_keys, metric_source))
            else:
                raw_metrics_query = ("SELECT %s FROM \"%s\" "
                    % (node_metric_keys, metric_source))
            raw_metrics_query += time_filter
            if tags_filter:
                raw_metrics_query += (" AND %s" % (tags_filter))
            print("raw metrics query = %s" % (raw_metrics_query))
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

            print("Deriving data from %s into %s" %
                  (metric_source, new_metric_name))
            # TODO: Later check for container metrics.
            for metric_group_name in raw_metrics[metric_source][group_name].unique():
                if not metric_group_name or metric_group_name == "":
                    print("Unable to find %s in metric %s" %
                          (metric_group_name, metric_source))
                    continue
                if metric_group_name not in metrics_thresholds:
                    state = ThresholdState(
                        metric_config["observation_window_sec"],
                        threshold["value"],
                        threshold["type"],
                        SAMPLE_INTERVAL_SECOND,
                    )
                    metrics_thresholds[metric_group_name] = state

            df = raw_metrics[metric_source]
            if len(normalizer_node_map) > 0:
                new_metric_name = metric_source + "_percent/" + metric_type
                total = df[group_name].map(normalizer_node_map)
                df["value"] = 100. * df["value"] / total

            df["value"] = df.apply(
                lambda row: metrics_thresholds[row[group_name]].compute(row.name.value, self.convert_value(row)),
                axis=1,
            )

            dfg = df.groupby(group_name)
            derived_metrics_result.add_metric(
                new_metric_name, is_container_metric, dfg, metric_config["resource"])

        print("Processing app metrics")
        app_metrics = self.get_app_metrics(start_time, end_time)
        if app_metrics is not None:
            app_state = ThresholdState(
                self.app_metric_config["observation_window_sec"],
                self.app_metric_config["threshold"]["value"],
                self.app_metric_config["threshold"]["type"],
                SAMPLE_INTERVAL_SECOND,
            )
            app_metrics["value"] = app_metrics.apply(
                lambda row: app_state.compute(
                    row.name.value,
                    self.convert_value(row)
                ),
                axis=1,
            )
            derived_metrics_result.set_app_metrics(app_metrics)

        return derived_metrics_result


if __name__ == '__main__':
    dm = MetricsConsumer("./derived_slo_metric_config.json", "./derived_metrics_config.json")
    derived_result = dm.get_derived_metrics(-9223372036854775806, 9223372036854775806)
    print("Derived Container metrics:")
    print(derived_result.container_metrics)
    print("Derived node metrics:")
    print(derived_result.node_metrics)
    print("Derived SLO metric:")
    print(derived_result.app_metrics)
