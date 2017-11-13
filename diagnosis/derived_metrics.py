
from influxdb import DataFrameClient
import json

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

    def compute(self, new_time, new_value):
        if self.last_was_hit and len(self.hits) > 0:
            for new_time-self.hits[len(self.hits)-1] >= 2 * self.sample_interval:
                filled_hit_time = self.hits[len(self.hits)-1] + self.sample_interval
                self.hits.append(filled_hit_time)

        # TODO: Check bound type and see if we should check data to be higher or lower than threshold.
        if new_value >= self.threshold:
            self.hits.append(new_time)
            last_was_hit = True
        else:
            last_was_hit = False

        window_begin_time = new_time - window
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
                "localhost"
                8086,
                "root",
                "root",
                "snapaverage")
            self.container_metrics_prefix = {'/intel/docker/' => "docker_id"}

    def get_derived_metrics(self, start_time, end_time):
        for metric_config in self.config:
            metric_source = metric_config["metric_name"]
            metric_type = metric_config["type"]
            threshold = metric_config["threshold"]
            raw_metrics = self.influx_client.query("SELECT * FROM \"%s\" WHERE time >= %d AND time <= %d" % (metric_source, start_time, end_time))
            node_thresholds = {}
            for metric in raw_metrics[metric_source].index:
                # TODO: First check which node this metric is from, and then use the right threshold state.
                # TODO: Later check for container metrics.
                node_name = metric["nodename"]
                if node_name not in node_thresholds:
                    state = ThresholdState(metric_config["observation_window"], threshold["value"], threshold["type"], 5000000000)
                    node_thresholds[node_name] = state

                state = node_thresholds[node_name]
                new_value = state.compute(metric.timestamp() * 1000000000, metric.value())

            # TODO: Return a map of nodes, and values is a list of dataframes
