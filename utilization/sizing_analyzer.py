import json
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt

from influxdb import DataFrameClient

ANALYSIS_WINDOW_SECOND = 600
SAMPLE_INTERVAL_SECOND = 5
NANOSECONDS_PER_SECOND = 1000000000
PERCENTILES = [.5, .95, .99]

class Status():
    SUCCESS = "success"
    BAD_CONFIG = "bad_config"
    DB_ERROR = "db_error"

class JobStatus():
    def __init__(self, status, data=None, error=None):
        self.status = status
        self.error = error

    def to_dict(self):
        return {
            "status": self.status,
            "error": self.error,
        }

def get_daily_timepair(current_date):
    today = datetime.datetime.combine(current_date, datetime.datetime.min.time())
    yesterday = today + datetime.timedelta(days=-1)
    return yesterday.timestamp(), today.timestamp()

def node_cpu_job(config, job_config, current_date):
    analyzer = SizingAnalyzer(config)
    yesterday, today = get_daily_timepair(current_date)
    status = analyzer.analyze_node_cpu(yesterday, today, SAMPLE_INTERVAL_SECOND, PERCENTILES)
    print("Node cpu finished with status: " + str(status.to_dict()))
    return status.error

def node_memory_job(config, job_config, current_date):
    analyzer = SizingAnalyzer(config)
    yesterday, today = get_daily_timepair(current_date)
    status = analyzer.analyze_node_memory(yesterday, today, PERCENTILES)
    print("Node memory finished with status: " + str(status.to_dict()))
    return status.error

def container_cpu_job(config, job_config, current_date):
    analyzer = SizingAnalyzer(config)
    yesterday, today = get_daily_timepair(current_date)
    status = analyzer.analyze_container_cpu(yesterday, today, SAMPLE_INTERVAL_SECOND, PERCENTILES)
    print("Container cpu finished with status: " + str(status.to_dict()))
    return status.error

def container_memory_job(config, job_config, current_date):
    analyzer = SizingAnalyzer(config)
    yesterday, today = get_daily_timepair(current_date)
    status = analyzer.analyze_container_memory(yesterday, today, SAMPLE_INTERVAL_SECOND, PERCENTILES)
    print("Container memory finished with status: " + str(status.to_dict()))
    return status.error

class SizingAnalyzer(object):
    def __init__(self, config):
        self.config = config

        influx_host = "localhost"
        influx_port = 8086
        influx_user = "root"
        influx_password = "root"
        input_db_name = "prometheus"
        output_db_name = "hyperpilot"
        result_db_name = "resultdb" # in MongoDB

        self.influx_client_input = DataFrameClient(
            influx_host,
            influx_port,
            influx_user,
            influx_password,
            input_db_name)

        self.influx_client_output = DataFrameClient(
            influx_host,
            influx_port,
            influx_user,
            influx_password,
            output_db_name)

    def analyze_node_cpu(self, start_time, end_time, sample_interval, percentiles):
        print("-- [node_cpu] Query influxdb for raw metrics data --")
        output_filter = "derivative(sum(value)) / " + str(sample_interval) + " as node_usage"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        tags_filter = "AND mode=~ /(user|system)/"
        group_tags = "instance,time(" + str(sample_interval) + "s)"
        metric_name = "node_cpu"
        node_cpu_usage_query = ("SELECT %s FROM %s WHERE %s %s GROUP BY %s"
                               % (output_filter, metric_name, time_filter, tags_filter, group_tags))

        #print("CPU usage query:\n", node_cpu_usage_query)
        try:
            node_cpu_usage_dict = self.influx_client_input.query(node_cpu_usage_query)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: " % (metric_name, str(e)))

        print("-- [node_cpu] Compute summary stats --")
        node_cpu_summary = pd.DataFrame()
        for k, df in node_cpu_usage_dict.items():
            node_name = k[1][0][1]
            try:
                self.influx_client_output.write_points(
                    df, "node_cpu_usage", {'instance': node_name})
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            #TODO: Need to filter out abnormal values
            node_cpu_summary[node_name] = df.node_usage.describe(percentiles)

        #print("node cpu usage summary: ", node_cpu_summary)
        # store_summary_stats(node_cpu_summary)

        print("-- [node_cpu] Compute sizing recommendation --")
        # node_cpu_sizes = compute_sizing_recommendation(node_cpu_summary)
        # store_sizing_recommenation(node_cpu_sizes)

        return JobStatus(status=Status.SUCCESS)


    def analyze_node_memory(self, start_time, end_time, percentiles):
        print("-- [node_memory] Query influxdb for raw metrics data --")
        output_filter = "value/1024/1024/1024"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        group_tags = "instance"

        metric_name = "node_memory_Active"
        try:
            node_mem_active_dict = self.influx_client_input.query(
                "SELECT %s FROM %s WHERE %s GROUP BY %s" %
                 (output_filter, metric_name, time_filter, group_tags))
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: " % (metric_name, str(e)))

        metric_name = "node_memory_MemTotal"
        try:
            node_mem_total_dict = self.influx_client_input.query(
                "SELECT %s FROM %s WHERE %s GROUP BY %s" %
                 (output_filter, metric_name, time_filter, group_tags))
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name, str(e)))

        metric_name = "node_memory_MemFree"
        try:
            node_mem_free_dict = self.influx_client_input.query(
                "SELECT %s FROM %s WHERE %s GROUP BY %s" %
                 (output_filter, metric_name, time_filter, group_tags))
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name, str(e)))

        print("-- [node_memory] Compute summary stats --")
        node_mem_summary = pd.DataFrame()
        for k, df_active in node_mem_active_dict.items():
            node_name = k[1][0][1]
            try:
                self.influx_client_output.write_points(
                    df_active, "node_memory_active", {'instance': node_name})
            except Exception as e:
                return JobStatus(status=STATUS.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            node_mem_summary[node_name, 'active'] = df_active.value.describe(percentiles)

        for k in node_mem_total_dict.keys():
            node_name = k[1][0][1]
            df_total = node_mem_total_dict[k]
            k_free = ('node_memory_MemFree', (('instance', node_name),))
            df_free = node_mem_free_dict[k_free]

            df_usage = df_total - df_free
            try:
                self.influx_client_output.write_points(
                    df_usage, "node_memory_usage", {'instance': node_name})
            except Exception as e:
                return JobStatus(status=STATUS.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            node_mem_summary[node_name, 'usage'] = df_usage.value.describe(percentiles)

        #print("node memory usage summary: ", node_mem_summary)
        #store_summary_stats(node_mem_summary)

        print("-- [node_memory] Compute sizing recommendation --")
        # node_mem_sizes = compute_sizing_recommendation(node_mem_summary)
        # store_sizing_recommenation(node_mem_sizes)

        return JobStatus(status=Status.SUCCESS)


    def analyze_container_cpu(self, start_time, end_time, sample_interval, percentiles):
        print("-- [container_cpu] Query influxdb for raw metrics data --")
        print("-- [container_cpu] Compute summary stats --")
        print("-- [container_cpu] Compute requests and limits --")

        return JobStatus(status=Status.SUCCESS)

    def analyze_container_memory(self, start_time, end_time, sample_interval, percentiles):
        print("-- [container_memory] Query influxdb for raw metrics data --")
        output_filter = "max(value)/1024/1024/1024 as value"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        tags_filter = "AND image!=''"
        group_tags = "image,time(" + str(sample_interval) + "s)"

        metric_name = "container_memory_working_set_bytes"
        try:
            container_mem_active_dict = self.influx_client_input.query(
                "SELECT %s FROM %s WHERE %s %s GROUP BY %s" %
                 (output_filter, metric_name, time_filter, tags_filter, group_tags))
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name, str(e)))

        metric_name = "container_memory_usage_bytes"
        try:
            container_mem_usage_dict = self.influx_client_input.query(
                "SELECT %s FROM %s WHERE %s %s GROUP BY %s" %
                 (output_filter, metric_name, time_filter, tags_filter, group_tags))
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name, str(e)))

        print("-- [container_memory] Compute summary stats --")
        container_mem_summary = pd.DataFrame()
        for k, df_active in container_mem_active_dict.items():
            image_name = k[1][0][1]
            df_active = df_active.dropna()
            try:
                self.influx_client_output.write_points(
                    df_active, "container_memory_active", {'image': image_name})
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            container_mem_summary[image_name, 'active'] = df_active.value.describe(percentiles)

        for k, df_usage in container_mem_usage_dict.items():
            image_name = k[1][0][1]
            df_usage = df_usage.dropna()
            try:
                self.influx_client_output.write_points(
                    df_usage, "container_memory_usage", {'image': image_name})
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            container_mem_summary[image_name, 'usage'] = df_usage.value.describe(percentiles)

        print("-- [container_memory] Compute requests and limits --")

        return JobStatus(status=Status.SUCCESS)


if __name__ == "__main__":
    sa = SizingAnalyzer()
    end_time = 1517016459493000000
    start_time = end_time - ANALYSIS_WINDOW_SECOND * NANOSECONDS_PER_SECOND

    job = sa.analyze_node_cpu(start_time, end_time, SAMPLE_INTERVAL_SECOND, PERCENTILES)
    print(job.to_dict())
    job = sa.analyze_node_memory(start_time, end_time, PERCENTILES)
    print(job.to_dict())
    job = sa.analyze_container_cpu(start_time, end_time, SAMPLE_INTERVAL_SECOND, PERCENTILES)
    print(job.to_dict())
    job = sa.analyze_container_memory(start_time, end_time, SAMPLE_INTERVAL_SECOND, PERCENTILES)
    print(job.to_dict())
