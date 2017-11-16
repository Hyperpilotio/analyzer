from influxdb import DataFrameClient
import json
import pandas as pd


class ThresholdState(object):
    def __init__(self, window, threshold, bound_type, sample_interval):
        '''
        e.g: window=30000000000, threshold=10, bound_type=UB, sample_interval=5000000000
        '''
        self.window = window
        self.threshold = threshold
        self.bound_type = bound_type
        self.sample_interval = sample_interval
        self.last_was_hit = False
        self.hits = []
        self.total_count = window / sample_interval

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

        window_begin_time = new_time - self.window
        last_good_idx = len(self.hits)
        idx = -1
        for hit in self.hits:
            idx += 1
            if hit >= window_begin_time:
                last_good_idx = idx
                break

        self.hits = self.hits[last_good_idx:]

        return float(len(self.hits)) / float(self.total_count)


class DerivedMetricsResults(object):
    def __init__(self, node_metrics=None, container_metrics=None):
        # { derived metric name -> { node name -> data frame } }
        self.node_metrics = {}

        # { derived metric name -> { node name -> container id -> data frame } }
        self.container_metrics = {}

    def add_node_metric(self, metric_name, node_name, df):
        if metric_name not in self.node_metrics:
            self.node_metrics[metric_name] = {}

        self.node_metrics[metric_name][node_name] = df

    def add_container_metric(self, metric_name, node_name, container_id, df):
        if metric_name not in self.container_metrics:
            self.container_metrics[metric_name] = {}

        nodes = self.container_metrics[metric_name]
        if node_name not in nodes:
            nodes[node_name] = {}

        nodes[node_name][container_id] = df

    def add_derived_metric(self, metric_name, is_container_metric, dfg):
        for d in dfg:
            if is_container_metric:
                nodename = d[1]["nodename"][1]
                self.add_container_metric(
                    metric_name, nodename, d[0], d[1])
            else:
                self.add_node_metric(metric_name, d[0], d[1])


class DerivedMetrics(object):
    def __init__(self, config_file):
        with open(config_file) as json_data:
            self.config = json.load(json_data)
            self.influx_client = DataFrameClient(
                "localhost",
                8086,
                "root",
                "root",
                "snapaverage")
            self.group_keys = {"/intel/docker": "docker_id"}
            self.default_group_key = "nodename"

    def get_derived_metrics(self, start_time, end_time):
        derived_metrics_result = DerivedMetricsResults()
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

            normalizer_metrics = None
            normalizer_node_map = {}
            normalizer = ""
            if "normalizer" in metric_config:
                normalizer = str(metric_config["normalizer"])
                if normalizer.startswith("/"):
                    normalizer = normalizer[1:]
                normalizer_metrics = self.influx_client.query(
                    "SELECT * FROM \"%s\" "
                    "WHERE time >= %d "
                    "AND time <= %d" % (normalizer, start_time, end_time))
                normalizer_metrics_len = len(normalizer_metrics)
                if normalizer_metrics_len == 0:
                    print("Unable to find data for %s, skipping..." %
                          (normalizer))
                else:
                    normalizer_df = normalizer_metrics[normalizer]
                    normalizer_dfg = normalizer_df.groupby("nodename").first()
                    for node_name in normalizer_dfg.value.index:
                        normalizer_node_map[node_name] = normalizer_dfg.value[1]

            raw_metrics = self.influx_client.query(
                "SELECT * FROM \"%s\" "
                "WHERE time >= %d "
                "AND time <= %d" % (metric_source, start_time, end_time))
            metrics_thresholds = {}
            raw_metrics_len = len(raw_metrics)
            if raw_metrics_len == 0:
                print("Unable to find data for %s, skipping..." %
                      (metric_source))
                continue
            elif normalizer_metrics and len(normalizer_metrics) != raw_metrics_len:
                print("Normalizer metric is not equal length to raw metrics")
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
                        metric_config["observation_window"],
                        threshold["value"],
                        threshold["type"],
                        5000000000,
                    )
                    metrics_thresholds[metric_group_name] = state

            df = raw_metrics[metric_source]
            normalizer_df = df.copy()
            df["value"] = df.apply(
                lambda row: metrics_thresholds[row[group_name]].compute(
                    row.name.value,
                    row["value"]
                ),
                axis=1,
            )

            dfg = df.groupby(group_name)
            derived_metrics_result.add_derived_metric(
                new_metric_name, is_container_metric, dfg)

            if len(normalizer_node_map) > 0:
                new_normalizer_name = metric_source + "_percent/" + metric_type
                total = normalizer_df[group_name].map(normalizer_node_map)
                normalizer_df["value"] = 100. * normalizer_df["value"] / total

                normalizer_dfg = normalizer_df.groupby(group_name)
                derived_metrics_result.add_derived_metric(
                    new_normalizer_name, is_container_metric, normalizer_dfg)

        return derived_metrics_result


if __name__ == '__main__':
    nodeAnalyzer = DerivedMetrics("./derived_metrics_config.json")
    result = nodeAnalyzer.get_derived_metrics(
        -9223372036854775806, 9223372036854775806)
    print(result)
