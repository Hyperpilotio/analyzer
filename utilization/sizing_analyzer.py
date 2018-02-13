import json
import ast
import math
import pandas as pd
import numpy as np
import datetime

from influxdb import DataFrameClient

from api_service.db import resultdb
from logger import get_logger
from config import get_config

NANOSECONDS_PER_SECOND = 1000000000

class Status():
    SUCCESS = "success"
    BAD_CONFIG = "bad_config"
    DB_ERROR = "db_error"

class JobStatus():
    def __init__(self, status, data=None, error=None):
        self.status = status
        self.error = error
        self.data = data

    def to_dict(self):
        return {
            "status": self.status,
            "error": self.error,
            "data": self.data
        }

def get_daily_timepair(current_date):
    today = datetime.datetime.combine(current_date, datetime.datetime.min.time())
    yesterday = today + datetime.timedelta(days=-1)
    return yesterday.timestamp() * NANOSECONDS_PER_SECOND, today.timestamp() * NANOSECONDS_PER_SECOND

def node_cpu_job(config, job_config, current_date):
    analyzer = SizingAnalyzer(config)
    yesterday, today = get_daily_timepair(current_date)
    status = analyzer.analyze_node_cpu(yesterday, today)
    print("Node cpu finished with status: " + str(status.to_dict()))
    return status.error

def node_memory_job(config, job_config, current_date):
    analyzer = SizingAnalyzer(config)
    yesterday, today = get_daily_timepair(current_date)
    status = analyzer.analyze_node_memory(yesterday, today)
    print("Node memory finished with status: " + str(status.to_dict()))
    return status.error

def container_cpu_job(config, job_config, current_date):
    analyzer = SizingAnalyzer(config)
    yesterday, today = get_daily_timepair(current_date)
    status = analyzer.analyze_container_cpu(yesterday, today)
    print("Container cpu finished with status: " + str(status.to_dict()))
    return status.error

def container_memory_job(config, job_config, current_date):
    analyzer = SizingAnalyzer(config)
    yesterday, today = get_daily_timepair(current_date)
    status = analyzer.analyze_container_memory(yesterday, today)
    print("Container memory finished with status: " + str(status.to_dict()))
    return status.error


class SizingAnalyzer(object):
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(__name__, log_level=("UTILIZATION", "LOGLEVEL"))

        self.percentiles = ast.literal_eval(config.get("UTILIZATION", "PERCENTILES"))
        self.stat_type = config.get("UTILIZATION", "DEFAULT_STAT_TYPE")
        self.scaling_factor = float(self.config.get("UTILIZATION", "DEFAULT_SCALING_FACTOR"))

        influx_host = config.get("INFLUXDB", "HOST")
        influx_port = config.get("INFLUXDB", "PORT")
        influx_user = config.get("INFLUXDB", "USERNAME")
        influx_password = config.get("INFLUXDB", "PASSWORD")
        input_db = config.get("INFLUXDB", "SIZING_INPUT_DB_NAME")
        output_db = config.get("INFLUXDB", "SIZING_OUTPUT_DB_NAME")
        self.results_collection = config.get("UTILIZATION", "SIZING_RESULTS_COLLECTION")

        self.influx_client_input = DataFrameClient(
            influx_host,
            influx_port,
            influx_user,
            influx_password,
            input_db)

        self.influx_client_output = DataFrameClient(
            influx_host,
            influx_port,
            influx_user,
            influx_password,
            output_db)
        self.influx_client_output.create_database(output_db)
        self.influx_client_output.create_retention_policy('sizing_result_policy', '4w', 1, default=True)


    def analyze_node_cpu(self, start_time, end_time, stat_type=None, scaling_factor=None):
        if stat_type is not None:
            self.stat_type = stat_type

        if scaling_factor is not None:
            self.scaling_factor = scaling_factor

        self.base_metric = 'usage'

        self.logger.info("-- [node_cpu] Query influxdb for raw metrics data --")
        output_filter = "derivative(sum(value), 1s) as usage"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        tags_filter = "AND mode=~ /(user|system)/"
        group_tags = self.config.get("UTILIZATION", "NODE_GROUP_TAGS") + ",time(1ms)"

        metric_name = "node_cpu"
        try:
            cpu_query = "SELECT %s FROM %s WHERE %s %s GROUP BY %s" % \
                        (output_filter, metric_name, time_filter, tags_filter, group_tags)
            self.logger.debug("Running query for node cpu: %s" % cpu_query)
            node_cpu_usage_dict = self.influx_client_input.query(cpu_query)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name, str(e)))

        self.logger.info("-- [node_cpu] Compute summary stats --")
        node_cpu_summary = pd.DataFrame()
        for k, df in node_cpu_usage_dict.items():
            node_name = k[1][0][1]
            #df.drop(df.index[(df.usage > MAX_CORES) | (df.usage < 0)], inplace=True)
            try:
                self.influx_client_output.write_points(
                    df, "node_cpu_usage", {'instance': node_name})
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            node_key = "instance="+node_name
            node_cpu_summary[node_key, self.base_metric] = df.usage.describe(
                self.percentiles).drop(['count','std', 'min'])

        node_cpu_summary.rename(
            index={'50%': "median", '95%': "p95", '99%': "p99"}, inplace=True)
        node_cpu_summary = node_cpu_summary
        self.logger.info("Computed node cpu usage summary:\n %s" % node_cpu_summary.to_json())

        self.logger.info("-- [node_cpu] Query influxdb for current node configs --")

        self.logger.info("-- [node_cpu] Compute sizing recommendation --")
        recommended_cpu_sizes = self.compute_node_sizing_recommendation(node_cpu_summary)
        self.logger.debug("Recommended node cpu sizes:\n %s" % recommended_cpu_sizes)

        self.logger.info("-- [node_cpu] Store analysis results in mongodb --")
        this_config = {
            "stat_type": self.stat_type,
            "scaling_factor": self.scaling_factor,
            "base_metric": self.base_metric
        }
        #TODO: Need to replace this with a query
        current_sizes = recommended_cpu_sizes
        results = self.construct_analysis_results(
            "cpu", node_cpu_summary, recommended_cpu_sizes, current_sizes)
        sizing_result_doc = {
                "object_type": "node",
                "resource": "cpu",
                "unit": "cores",
                "start_time": start_time,
                "end_time": end_time,
                "labels": self.config.get("UTILIZATION", "NODE_GROUP_TAGS").split(","),
                "config": this_config,
                "results": results
        }

        try:
            resultdb[self.results_collection].insert_one(sizing_result_doc)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to write analysis results to MongoDB: " + str(e))

        return JobStatus(status=Status.SUCCESS,
                         data=sizing_result_doc)


    def analyze_node_memory(self, start_time, end_time, stat_type=None, scaling_factor=None, base_metric=None):
        if stat_type is not None:
            self.stat_type = stat_type

        if scaling_factor is not None:
            self.scaling_factor = scaling_factor

        if base_metric is not None:
            self.base_metric = base_metric
        else:
            self.base_metric = self.config.get("UTILIZATION", "MEMORY_BASE_METRIC")

        self.logger.info("-- [node_memory] Query influxdb for raw metrics data --")
        output_filter = "value/1024/1024/1024"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        group_tags = self.config.get("UTILIZATION", "NODE_GROUP_TAGS")

        metric_name = "node_memory_Active"
        try:
            mem_active_query = "SELECT %s FROM %s WHERE %s GROUP BY %s" % \
                 (output_filter, metric_name, time_filter, group_tags)
            self.logger.debug("Running node memory query: %s" % mem_active_query)
            node_mem_active_dict = self.influx_client_input.query(mem_active_query)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: " % (metric_name, str(e)))

        metric_name = "node_memory_MemTotal"
        try:
            mem_total_query = "SELECT %s FROM %s WHERE %s GROUP BY %s" % \
                 (output_filter, metric_name, time_filter, group_tags)
            self.logger.debug("Running node total memory query: %s" % mem_total_query)
            node_mem_total_dict = self.influx_client_input.query(mem_total_query)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name, str(e)))

        metric_name_free = "node_memory_MemFree"
        try:
            mem_free_query = "SELECT %s FROM %s WHERE %s GROUP BY %s" % \
                 (output_filter, metric_name_free, time_filter, group_tags)
            self.logger.debug("Running node memory free query: %s" % mem_free_query)
            node_mem_free_dict = self.influx_client_input.query(mem_free_query)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name_free, str(e)))

        self.logger.info("-- [node_memory] Compute summary stats --")
        node_mem_summary = pd.DataFrame()
        for k, df_active in node_mem_active_dict.items():
            node_name = k[1][0][1]
            try:
                self.influx_client_output.write_points(
                    df_active, "node_memory_active", {'instance': node_name})
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            node_key = "instance="+node_name
            node_mem_summary[node_key, 'active'] = df_active.value.describe(
                self.percentiles).drop(['count','std', 'min'])

        for k in node_mem_total_dict.keys():
            node_name = k[1][0][1]
            df_total = node_mem_total_dict[k]
            k_free = (metric_name_free, (('instance', node_name),))
            df_free = node_mem_free_dict[k_free]

            df_usage = df_total - df_free
            try:
                self.influx_client_output.write_points(
                    df_usage, "node_memory_usage", {'instance': node_name})
            except Exception as e:
                return JobStatus(status=Ststus.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            node_key = "instance="+node_name
            node_mem_summary[node_key, 'usage'] = df_usage.value.describe(
                self.percentiles).drop(['count','std', 'min'])

        node_mem_summary.rename(
            index={'50%': "median", '95%': "p95", '99%': "p99"}, inplace=True)
        self.logger.info("Computed node memory usage summary:\n %s" % node_mem_summary.to_json())

        self.logger.info("-- [node_memory] Query influxdb for current node configs --")

        self.logger.info("-- [node_memory] Compute sizing recommendation --")
        recommended_mem_sizes = self.compute_node_sizing_recommendation(node_mem_summary)
        self.logger.debug("Recommended node memory sizes:\n %s" %str(recommended_mem_sizes))

        self.logger.info("-- [node_memory] Store analysis results in mongodb --")
        this_config = {
            "stat_type": self.stat_type,
            "scaling_factor": self.scaling_factor,
            "base_metric": self.base_metric
        }
        #TODO: Need to replace this with a query
        current_sizes = recommended_mem_sizes
        results = self.construct_analysis_results(
            "memory", node_mem_summary, recommended_mem_sizes, current_sizes)
        sizing_result_doc = {
                "object_type": "node",
                "resource": "memory",
                "unit": "GB",
                "start_time": start_time,
                "end_time": end_time,
                "labels": self.config.get("UTILIZATION", "NODE_GROUP_TAGS").split(","),
                "config": this_config,
                "results": results
        }

        try:
            resultdb[self.results_collection].insert_one(sizing_result_doc)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to write analysis results to MongoDB: " + str(e))

        return JobStatus(status=Status.SUCCESS,
                         data=sizing_result_doc)


    def analyze_container_cpu(self, start_time, end_time, stat_type=None, scaling_factor=None):
        if stat_type is not None:
            self.stat_type = stat_type

        if scaling_factor is not None:
            self.scaling_factor = scaling_factor

        self.base_metric = 'usage'

        self.logger.info("-- [container_cpu] Query influxdb for raw metrics data --")
        output_filter = "derivative(sum(value), 1s) as usage"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        tags_filter = "AND image!=''"
        group_tags = self.config.get("UTILIZATION", "CONTAINER_GROUP_TAGS") + ",pod_name,time(1ms)"

        metric_name = "container_cpu_user_seconds_total"
        try:
            container_cpu_user_query = "SELECT %s FROM %s WHERE %s %s GROUP BY %s" % \
                 (output_filter, metric_name, time_filter, tags_filter, group_tags)
            self.logger.debug("Running container cpu query: " + container_cpu_user_query)
            container_cpu_user_dict = self.influx_client_input.query(container_cpu_user_query)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name, str(e)))

        metric_name_sys = "container_cpu_system_seconds_total"
        try:
            container_cpu_sys_query = "SELECT %s FROM %s WHERE %s %s GROUP BY %s" % \
                 (output_filter, metric_name_sys, time_filter, tags_filter, group_tags)
            self.logger.debug("Running container cpu sys query: " + container_cpu_sys_query)
            container_cpu_sys_dict = self.influx_client_input.query(container_cpu_sys_query)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name_sys, str(e)))

        self.logger.info("-- [container_cpu] Compute summary stats --")
        df_usage = pd.DataFrame()
        container_cpu_usage_dict = {}
        for k_user, df_user in container_cpu_user_dict.items():
            image_name = k_user[1][0][1]
            pod_name = k_user[1][1][1]
            k_sys = (metric_name_sys, (('image', image_name), ('pod_name', pod_name)))
            df_sys = container_cpu_sys_dict[k_sys]
            df_usage = (df_user + df_sys).astype('float32')

            if image_name not in container_cpu_usage_dict.keys():
                container_cpu_usage_dict[image_name] = df_usage
            else:
                df_comb = pd.merge_asof(container_cpu_usage_dict[image_name], df_usage,
                                        left_index=True, right_index=True,
                                        suffixes=('_1', '_2'), direction='nearest')
                container_cpu_usage_dict[image_name].usage = df_comb[['usage_1', 'usage_2']].max(axis=1)

        container_cpu_summary = pd.DataFrame()
        for image_name, df_usage in container_cpu_usage_dict.items():
            df_usage = df_usage.dropna()
            try:
                self.influx_client_output.write_points(
                    df_usage, "container_cpu_usage", {'image': image_name})
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            image_key = "image=" + image_name
            container_cpu_summary[image_key, self.base_metric] = df_usage.usage.describe(
                self.percentiles).drop(['count','std', 'min'])

        container_cpu_summary.rename(
            index={'50%': "median", '95%': "p95", '99%': "p99"}, inplace=True)
        self.logger.info("Computed container cpu usage summary:\n %s" % container_cpu_summary.to_json())

        self.logger.info("-- [container_cpu] Query influxdb for current requests and limits --")

        self.logger.info("-- [container_cpu] Compute requests and limits --")
        recommended_cpu_settings = self.compute_container_cpu_settings(container_cpu_summary)
        self.logger.debug("Recommended container cpu settingss:\n %s" % str(recommended_cpu_settings))

        self.logger.info("-- [container_cpu] Store analysis results in mongodb --")
        this_config = {
            "stat_type": self.stat_type,
            "scaling_factor": self.scaling_factor,
            "base_metric": self.base_metric
        }
        #TODO: Need to replace this with a query
        current_settings = recommended_cpu_settings
        results = self.construct_analysis_results(
            "cpu", container_cpu_summary, recommended_cpu_settings, current_settings)
        sizing_result_doc = {
                "object_type": "container",
                "resource": "cpu",
                "unit": "cores",
                "start_time": start_time,
                "end_time": end_time,
                "labels": self.config.get("UTILIZATION", "CONTAINER_GROUP_TAGS").split(","),
                "config": this_config,
                "results": results
        }

        try:
            resultdb[self.results_collection].insert_one(sizing_result_doc)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to write analysis results to MongoDB: " + str(e))

        return JobStatus(status=Status.SUCCESS,
                         data=sizing_result_doc)


    def analyze_container_memory(self, start_time, end_time, stat_type=None, scaling_factor=None, base_metric=None):
        if stat_type is not None:
            self.stat_type = stat_type

        if scaling_factor is not None:
            self.scaling_factor = scaling_factor

        if base_metric is not None:
            self.base_metric = base_metric
        else:
            self.base_metric = self.config.get("UTILIZATION", "MEMORY_BASE_METRIC")

        self.logger.info("-- [container_memory] Query influxdb for raw metrics data --")
        output_filter = "max(value)/1024/1024 as value"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        tags_filter = "AND image!=''"
        group_tags = self.config.get("UTILIZATION", "CONTAINER_GROUP_TAGS") + ",time(5s)"

        metric_name = "container_memory_working_set_bytes"
        try:
            container_mem_active_query = "SELECT %s FROM %s WHERE %s %s GROUP BY %s" % \
                 (output_filter, metric_name, time_filter, tags_filter, group_tags)
            self.logger.debug("Running container memory active query: " + container_mem_active_query)
            container_mem_active_dict = self.influx_client_input.query(container_mem_active_query)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name, str(e)))

        metric_name = "container_memory_usage_bytes"
        try:
            container_mem_usage_query = "SELECT %s FROM %s WHERE %s %s GROUP BY %s" % \
                 (output_filter, metric_name, time_filter, tags_filter, group_tags)
            self.logger.debug("Running container memory usage query: " + container_mem_usage_query)
            container_mem_usage_dict = self.influx_client_input.query(container_mem_usage_query)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name, str(e)))

        self.logger.info("-- [container_memory] Compute summary stats --")
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
            image_key = "image=" + image_name
            container_mem_summary[image_key, 'active'] = df_active.value.describe(
                self.percentiles).drop(['count','std', 'min'])

        for k, df_usage in container_mem_usage_dict.items():
            image_name = k[1][0][1]
            df_usage = df_usage.dropna()
            try:
                self.influx_client_output.write_points(
                    df_usage, "container_memory_usage", {'image': image_name})
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            image_key = "image=" + image_name
            container_mem_summary[image_key, 'usage'] = df_usage.value.describe(
                self.percentiles).drop(['count','std', 'min'])

        container_mem_summary.rename(
            index={'50%': "median", '95%': "p95", '99%': "p99"}, inplace=True)
        self.logger.info("Computed container memory usage summary:\n %s" % container_mem_summary.to_json())

        self.logger.info("-- [container_memory] Query influxdb for current requests and limits --")

        self.logger.info("-- [container_memory] Compute requests and limits --")
        recommended_mem_settings = self.compute_container_mem_settings(container_mem_summary)
        self.logger.debug("Recommended container memory settings:\n %s" % str(recommended_mem_settings))

        self.logger.info("-- [container_memory] Store analysis results in mongodb --")
        this_config = {
            "stat_type": self.stat_type,
            "scaling_factor": self.scaling_factor,
            "base_metric": self.base_metric
        }
        #TODO: Need to replace this with a query
        current_settings = recommended_mem_settings
        results = self.construct_analysis_results(
            "memory", container_mem_summary, recommended_mem_settings, current_settings)
        sizing_result_doc = {
                "object_type": "container",
                "resource": "memory",
                "unit": "MB",
                "start_time": start_time,
                "end_time": end_time,
                "labels": self.config.get("UTILIZATION", "CONTAINER_GROUP_TAGS").split(","),
                "config": this_config,
                "results": results
        }

        try:
            resultdb[self.results_collection].insert_one(sizing_result_doc)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to write analysis results to MongoDB: " + str(e))

        return JobStatus(status=Status.SUCCESS,
                         data=sizing_result_doc)


    def compute_node_sizing_recommendation(self, node_summary):
        node_sizes = {}

        for column in node_summary:
            col_keys = node_summary[column].name
            node_key = col_keys[0]
            metric_type = col_keys[1]
            if metric_type == self.base_metric:
                node_sizes[node_key] = {
                    "size": math.ceil(node_summary[column][self.stat_type] * self.scaling_factor)
                }

        return node_sizes

    def compute_container_cpu_settings(self, container_cpu_summary):
        container_cpu_settings = {}

        for column in container_cpu_summary:
            col_keys = container_cpu_summary[column].name
            container_key = col_keys[0]
            container_cpu_settings[container_key] = {
                "requests": math.ceil(container_cpu_summary[column][self.stat_type]*100)/float(100),
                "limits": math.ceil(container_cpu_summary[column][self.stat_type]*self.scaling_factor*100)/100.0
            }

        return container_cpu_settings

    def compute_container_mem_settings(self, container_mem_summary):
        container_mem_settings = {}

        for column in container_mem_summary:
            col_keys = container_mem_summary[column].name
            container_key = col_keys[0]
            metric_type = col_keys[1]
            if metric_type == 'active':
                requests = math.ceil(container_mem_summary[column][self.stat_type])
                if container_key not in container_mem_settings:
                    container_mem_settings[container_key] = {'requests': requests}
                else:
                    container_mem_settings[container_key]['requests'] = requests
            else: # metric_type = 'usage'
                limits = math.ceil(container_mem_summary[column][self.stat_type] * self.scaling_factor)
                if container_key not in container_mem_settings:
                    container_mem_settings[container_key] = {'limits': limits}
                else:
                    container_mem_settings[container_key]['limits'] = limits

        return container_mem_settings

    def construct_analysis_results(self, resource_type, usage_summary, recommended_settings, current_settings):
        summary_stats = {}
        results = []

        for column in usage_summary:
            col_keys = usage_summary[column].name
            label_key = col_keys[0]
            metric_type = col_keys[1]
            summary_type = resource_type + "_" + metric_type
            if label_key not in summary_stats:
                summary_stats[label_key] = {summary_type: usage_summary[column].to_dict()}
            else:
                summary_stats[label_key][summary_type] = usage_summary[column].to_dict()

        for label_key in summary_stats:
            label_values = {}
            for label in label_key.split(","):
                label_pair = label.split("=")
                label_values[label_pair[0]] = label_pair[1]

            results.append({
                "label_values": label_values,
                "summary_stats": summary_stats[label_key],
                "current_settings": current_settings[label_key],
                "recommended_settings": recommended_settings[label_key]
            })

        return results


if __name__ == "__main__":
    config = get_config()
    sa = SizingAnalyzer(config)
    end_time = 1517016459493000000
    ANALYSIS_WINDOW_SECOND = 300
    start_time = end_time - ANALYSIS_WINDOW_SECOND * NANOSECONDS_PER_SECOND

    status = sa.analyze_node_cpu(start_time, end_time)
    print("Node cpu finished with status: " + str(status.to_dict()))
    status = sa.analyze_node_memory(start_time, end_time)
    print("Node memory finished with status: " + str(status.to_dict()))
    status = sa.analyze_container_cpu(start_time, end_time)
    print("Container cpu finished with status: " + str(status.to_dict()))
    status = sa.analyze_container_memory(start_time, end_time)
    print("Container memory finished with status: " + str(status.to_dict()))
