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
            # TODO: Get container_metrics_prefix
            # self.container_metrics_prefix = {'/intel/docker/' => "docker_id"}

    def get_derived_metrics(self, start_time, end_time):
        derived_metrics_nodes = {}
        for metric_config in self.config:
            metric_source = str(metric_config["metric_name"])
            metric_type = metric_config["type"]
            threshold = metric_config["threshold"]
            if metric_source.startswith("/"):
                metric_source = metric_source[1:]

            node_thresholds = {}
            raw_metrics = self.influx_client.query(
                "SELECT * FROM \"%s\" WHERE time >= %d AND time <= %d" % (metric_source, start_time, end_time))
            if len(raw_metrics) > 0:
                print("Find data for %s" % (metric_source))
                # TODO: First check which node this metric is from, and then use the right threshold state.
                # TODO: Later check for container metrics.
                for node_name in raw_metrics[metric_source]["nodename"].unique():
                    if not node_name or node_name == "":
                        print("Node name not found in metric %s", metric_source)
                        continue
                    if node_name not in node_thresholds:
                        state = ThresholdState(
                            metric_config["observation_window"], threshold["value"], threshold["type"], 5000000000)
                        node_thresholds[node_name] = state
                    if node_name not in derived_metrics_nodes:
                        derived_metrics_nodes[node_name] = []

                df = raw_metrics[metric_source]
                df["derived_metric_value"] = df.apply(
                    lambda row: node_thresholds[row["nodename"]].compute(
                        row.name.value,
                        row["value"]
                    ),
                    axis=1,
                )
                df = df.reset_index().rename(columns={"index": "time"})
                df = df.sort_values(["nodename", "time"])
                print(df[["nodename", "time", "value", "derived_metric_value"]])

                # TODO filter df data by nodename, and append to
                # derived_metrics_nodes
            else:
                print("Unable to find data for %s, skipping..." %
                      (metric_source))

            # TODO: Return a map of nodes, and values is a list of dataframes
            return derived_metrics_nodes


if __name__ == '__main__':
    nodeAnalyzer = DerivedMetrics("./derived_metrics_config.json")
    result = nodeAnalyzer.get_derived_metrics(
        -9223372036854775806, 9223372036854775806)
    print(result)
