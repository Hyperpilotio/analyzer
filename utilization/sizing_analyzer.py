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
        self.resultdb = resultdb
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
        group_tags = self.config.get("UTILIZATION", "NODE_GROUP_TAGS")
        group_by_tags = group_tags + ",time(1ms)"

        metric_name = "node_cpu"
        try:
            node_cpu_usage_dict = self.query_influx_metric(
                metric_name, output_filter, time_filter, tags_filter, group_by_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        self.logger.info("-- [node_cpu] Compute summary stats --")
        node_cpu_summary = pd.DataFrame()
        new_metric = "node_cpu_usage"
        for k, df in node_cpu_usage_dict.items():
            group_key = dict((x, y) for x, y in k[1])
            #df.drop(df.index[(df.usage > MAX_CORES) | (df.usage < 0)], inplace=True)
            try:
                self.influx_client_output.write_points(df, new_metric, group_key)
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result for %s to influxDB: %s" %
                                 (new_metric, str(e)))
            node_key = "instance="+group_key['instance']
            node_cpu_summary[node_key, self.base_metric] = df.usage.describe(
                self.percentiles).drop(['count','std', 'min'])

        node_cpu_summary.rename(
            index={'50%': "median", '95%': "p95", '99%': "p99"}, inplace=True)
        self.logger.debug("Computed node cpu usage summary:\n %s" % node_cpu_summary.to_json())

        self.logger.info("-- [node_cpu] Query influxdb for current node configs --")
        metric_name = "machine_cpu_cores"
        try:
            node_cpu_size_dict = self.query_influx_metric(
                metric_name, "value", time_filter, "", group_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))
        current_cpu_sizes = self.get_node_sizes(node_cpu_size_dict, "node_cpu_size")
        self.logger.info("Current node cpu sizes (in #cores):\n %s" % current_cpu_sizes)

        self.logger.info("-- [node_cpu] Compute sizing recommendation --")
        recommended_cpu_sizes = self.recommend_node_sizes(node_cpu_summary)
        self.logger.info("Recommended node cpu sizes (in #cores):\n %s" % recommended_cpu_sizes)

        self.logger.info("-- [node_cpu] Store analysis results in mongodb --")
        results = self.construct_analysis_results(
            "cpu", node_cpu_summary, recommended_cpu_sizes, current_cpu_sizes)
        sizing_result_doc = {
                "object_type": "node",
                "resource": "cpu",
                "unit": "cores",
                "start_time": start_time,
                "end_time": end_time,
                "labels": group_tags.split(","),
                "config": {},
                "results": results
        }
        try:
            self.store_analysis_results(sizing_result_doc)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

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

        metric_name_active = "node_memory_Active"
        try:
            node_mem_active_dict = self.query_influx_metric(
                metric_name_active, output_filter, time_filter, "", group_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        metric_name_total = "node_memory_MemTotal"
        try:
            node_mem_total_dict = self.query_influx_metric(
                metric_name_total, output_filter, time_filter, "", group_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        metric_name_free = "node_memory_MemFree"
        try:
            node_mem_free_dict = self.query_influx_metric(
                metric_name_free, output_filter, time_filter, "", group_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        self.logger.info("-- [node_memory] Compute summary stats --")
        node_mem_summary = pd.DataFrame()
        new_metric = "node_memory_active"
        for k, df_active in node_mem_active_dict.items():
            group_key = dict((x, y) for x, y in k[1])
            try:
                self.influx_client_output.write_points(
                    df_active, new_metric, group_key)
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result for %s to influxDB: %s" %
                                 (new_metric, str(e)))
            node_key = "instance=" + group_key['instance']
            node_mem_summary[node_key, 'active'] = df_active.value.describe(
                self.percentiles).drop(['count','std', 'min'])

        new_metric = "node_memory_usage"
        for k in node_mem_total_dict.keys():
            group_key = dict((x, y) for x, y in k[1])
            df_total = node_mem_total_dict[k]
            k_free = (metric_name_free, k[1])
            df_free = node_mem_free_dict[k_free]

            df_usage = df_total - df_free
            try:
                self.influx_client_output.write_points(
                    df_usage, new_metric, group_key)
            except Exception as e:
                return JobStatus(status=Ststus.DB_ERROR,
                                 error="Unable to write query result for %s to influxDB: %s" %
                                 (new_metric, str(e)))
            node_key = "instance=" + group_key['instance']
            node_mem_summary[node_key, 'usage'] = df_usage.value.describe(
                self.percentiles).drop(['count','std', 'min'])

        node_mem_summary.rename(
            index={'50%': "median", '95%': "p95", '99%': "p99"}, inplace=True)
        self.logger.debug("Computed node memory usage summary:\n %s" % node_mem_summary.to_json())

        self.logger.info("-- [node_memory] Query influxdb for current node configs --")
        try:
            node_mem_size_dict = self.query_influx_metric(
                "machine_memory_bytes", output_filter, time_filter, "", group_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))
        current_mem_sizes = self.get_node_sizes(node_mem_size_dict, "node_memory_size")
        self.logger.info("Current node memory sizes (in GB):\n %s" % current_mem_sizes)

        self.logger.info("-- [node_memory] Compute sizing recommendation --")
        recommended_mem_sizes = self.recommend_node_sizes(node_mem_summary)
        self.logger.info("Recommended node memory sizes (in GB):\n %s" % recommended_mem_sizes)

        self.logger.info("-- [node_memory] Store analysis results in mongodb --")
        results = self.construct_analysis_results(
            "memory", node_mem_summary, recommended_mem_sizes, current_mem_sizes)
        sizing_result_doc = {
                "object_type": "node",
                "resource": "memory",
                "unit": "GB",
                "start_time": start_time,
                "end_time": end_time,
                "labels": group_tags.split(","),
                "config": {},
                "results": results
        }

        try:
            self.store_analysis_results(sizing_result_doc)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

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
        group_tags = self.config.get("UTILIZATION", "CONTAINER_GROUP_TAGS")
        group_by_tags = group_tags + ",pod_name,time(1ms)"

        metric_name_usr = "container_cpu_user_seconds_total"
        try:
            container_cpu_user_dict = self.query_influx_metric(
                metric_name_usr, output_filter, time_filter, tags_filter, group_by_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        metric_name_sys = "container_cpu_system_seconds_total"
        try:
            container_cpu_sys_dict = self.query_influx_metric(
                metric_name_sys, output_filter, time_filter, tags_filter, group_by_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        self.logger.info("-- [container_cpu] Compute summary stats --")
        df_usage = pd.DataFrame()
        container_cpu_usage_dict = {}
        for k_user, df_user in container_cpu_user_dict.items():
            group_key = k_user[1]
            df_sys = container_cpu_sys_dict[(metric_name_sys, group_key)]
            df_usage = (df_user + df_sys).astype('float32')

            if group_key not in container_cpu_usage_dict.keys():
                container_cpu_usage_dict[group_key] = df_usage
            else:
                df_comb = pd.merge_asof(container_cpu_usage_dict[group_key], df_usage,
                                        left_index=True, right_index=True,
                                        suffixes=('_1', '_2'), direction='nearest')
                container_cpu_usage_dict[group_key].usage = df_comb[['usage_1', 'usage_2']].max(axis=1)

        container_cpu_summary = pd.DataFrame()
        output_metric = "container_cpu_usage"
        for k, df_usage in container_cpu_usage_dict.items():
            group_key = dict((x, y) for x, y in k)
            df_usage = df_usage.dropna()
            try:
                self.influx_client_output.write_points(df_usage, output_metric, group_key)
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result for %s to influxDB: %s" %
                                 (output_metric, str(e)))
            image_key = "image=" + group_key['image']
            container_cpu_summary[image_key, self.base_metric] = df_usage.usage.describe(
                self.percentiles).drop(['count','std', 'min'])

        container_cpu_summary.rename(
            index={'50%': "median", '95%': "p95", '99%': "p99"}, inplace=True)
        self.logger.debug("Computed container cpu usage summary:\n %s" % container_cpu_summary.to_json())

        self.logger.info("-- [container_cpu] Query influxdb for current requests and limits --")
        output_filter = "sum(value) as value"
        group_by_tags = group_tags + ",pod_name,time(5s)"
        try:
            cpu_quota_dict = self.query_influx_metric(
                "container_spec_cpu_quota", output_filter, time_filter, tags_filter, group_by_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        try:
            cpu_period_dict = self.query_influx_metric(
                "container_spec_cpu_period", output_filter, time_filter, tags_filter, group_by_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        output_metric = "container_cpu_settings"
        try:
            current_cpu_settings = self.get_container_cpu_settings(
                cpu_quota_dict, cpu_period_dict, output_metric)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))
        self.logger.info("Current container cpu settings (in #cores):\n %s" %
                         current_cpu_settings)

        self.logger.info("-- [container_cpu] Compute requests and limits --")
        recommended_cpu_settings = self.recommend_container_cpu_settings(container_cpu_summary)
        self.logger.info("Recommended container cpu settings (in #cores):\n %s" %
                         recommended_cpu_settings)

        self.logger.info("-- [container_cpu] Store analysis results in mongodb --")
        results = self.construct_analysis_results(
            "cpu", container_cpu_summary, recommended_cpu_settings, current_cpu_settings)
        sizing_result_doc = {
                "object_type": "container",
                "resource": "cpu",
                "unit": "cores",
                "start_time": start_time,
                "end_time": end_time,
                "labels": group_tags.split(","),
                "config": {},
                "results": results
        }

        try:
            self.store_analysis_results(sizing_result_doc)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

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
        group_tags = self.config.get("UTILIZATION", "CONTAINER_GROUP_TAGS")
        group_by_tags = group_tags + ",time(5s)"

        metric_name = "container_memory_working_set_bytes"
        try:
            container_mem_active_dict = self.query_influx_metric(
                metric_name, output_filter, time_filter, tags_filter, group_by_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        metric_name = "container_memory_usage_bytes"
        try:
            container_mem_usage_dict = self.query_influx_metric(
                metric_name, output_filter, time_filter, tags_filter, group_by_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        self.logger.info("-- [container_memory] Compute summary stats --")
        container_mem_summary = pd.DataFrame()
        output_metric = "container_memory_active"
        for k, df_active in container_mem_active_dict.items():
            group_key = dict((x, y) for x, y in k[1])
            df_active = df_active.dropna()
            try:
                self.influx_client_output.write_points(df_active, output_metric, group_key)
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result for %s to influxDB: %s" %
                                 (output_metric, str(e)))
            image_key = "image=" + group_key['image']
            container_mem_summary[image_key, 'active'] = df_active.value.describe(
                self.percentiles).drop(['count','std', 'min'])

        output_metric = "container_memory_usage"
        for k, df_usage in container_mem_usage_dict.items():
            group_key = dict((x, y) for x, y in k[1])
            df_usage = df_usage.dropna()
            try:
                self.influx_client_output.write_points(df_usage, output_metric, group_key)
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result for %s to influxDB: %s" %
                                 (output_metric, str(e)))
            image_key = "image=" + group_key['image']
            container_mem_summary[image_key, 'usage'] = df_usage.value.describe(
                self.percentiles).drop(['count','std', 'min'])

        container_mem_summary.rename(
            index={'50%': "median", '95%': "p95", '99%': "p99"}, inplace=True)
        self.logger.debug("Computed container memory usage summary:\n %s" % 
                          container_mem_summary.to_json())

        self.logger.info("-- [container_memory] Query influxdb for current requests and limits --")
        try:
            mem_settings_dict = self.query_influx_metric(
                "container_spec_memory_limit_bytes", output_filter, time_filter, tags_filter, group_by_tags)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        output_metric = "container_mem_settings"
        try:
            current_mem_settings = self.get_container_mem_settings(mem_settings_dict, output_metric)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))
        self.logger.info("Current container memory settings (in MB):\n %s" %
                         current_mem_settings)

        self.logger.info("-- [container_memory] Compute requests and limits --")
        recommended_mem_settings = self.recommend_container_mem_settings(container_mem_summary)
        self.logger.info("Recommended container memory settings (in MB):\n %s" %
                         recommended_mem_settings)

        self.logger.info("-- [container_memory] Store analysis results in mongodb --")
        this_config = {
            "stat_type": self.stat_type,
            "scaling_factor": self.scaling_factor,
            "base_metric": self.base_metric
        }
        results = self.construct_analysis_results(
            "memory", container_mem_summary, recommended_mem_settings, current_mem_settings)
        sizing_result_doc = {
                "object_type": "container",
                "resource": "memory",
                "unit": "MB",
                "start_time": start_time,
                "end_time": end_time,
                "labels": group_tags.split(","),
                "config": {},
                "results": results
        }
        try:
            self.store_analysis_results(sizing_result_doc)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR, error=str(e))

        return JobStatus(status=Status.SUCCESS,
                         data=sizing_result_doc)


    def query_influx_metric(self, metric_name, output_filter, time_filter, tags_filter, group_by_tags):
        try:
            influx_query = "SELECT %s FROM %s WHERE %s %s GROUP BY %s" % \
                           (output_filter, metric_name, time_filter, tags_filter, group_by_tags)
            self.logger.debug("Running influxDB read query: %s" % influx_query)
            metric_dict = self.influx_client_input.query(influx_query)
        except Exception as e:
            err_msg = "Unable to fetch %s from influxDB: %s" % (metric_name, str(e))
            self.logger.error(err_msg)
            raise Exception(err_msg)

        return metric_dict

    def get_node_sizes(self, node_size_dict, output_name):
        current_sizes = {}

        for k, df in node_size_dict.items():
            group_key = dict((x, y) for x, y in k[1])
            #label_key = tuple(x+"="+y for x, y in k[1])
            try:
                self.influx_client_output.write_points(df, output_name, group_key)
            except Exception as e:
                err_msg = ("Unable to write query result for %s to influxDB: %s" % (output_name, str(e)))
                self.logger.error(err_msg)
                raise Exception(err_msg)

            node_key = "instance="+group_key['instance']
            current_sizes[node_key] = {
                'size': math.ceil(df.loc[df.index[len(df)-1], 'value'])
            }

        return current_sizes

    def get_container_cpu_settings(self, cpu_quota_dict, cpu_period_dict, output_name):
        current_settings = {}

        metric_name_period = list(cpu_period_dict.keys())[0][0]

        df_settings = pd.DataFrame()
        container_cpu_limit_dict = {}
        for k_quota, df_quota in cpu_quota_dict.items():
            group_key = k_quota[1]
            df_period = cpu_period_dict[(metric_name_period, group_key)]
            df_limit = df_quota.divide(df_period).dropna()

            if group_key not in container_cpu_limit_dict.keys():
                container_cpu_limit_dict[group_key] = df_limit
            else:
                df_comb = pd.merge_asof(container_cpu_limit_dict[group_key], df_limit,
                                        left_index=True, right_index=True,
                                        suffixes=('_1', '_2'), direction='nearest')
                container_cpu_limit_dict[group_key] = df_comb[['value_1', 'value_2']].min(axis=1)

        for k, df in container_cpu_limit_dict.items():
            group_key = dict((x, y) for x, y in k)
            try:
                self.influx_client_output.write_points(df, output_name, group_key)
            except Exception as e:
                err_msg = ("Unable to write query result for %s to influxDB: %s" % (output_name, str(e)))
                self.logger.error(err_msg)
                raise Exception(err_msg)

            container_key = "image="+group_key['image']
            current_settings[container_key] = {
                'requests': 0,
                'limits': math.ceil(df.loc[df.index[len(df)-1], 'value']*100)/float(100)
            }

        return current_settings

    def get_container_mem_settings(self, mem_settings_dict, output_name):
        current_settings = {}

        for k, df in mem_settings_dict.items():
            group_key = dict((x, y) for x, y in k[1])
            try:
                self.influx_client_output.write_points(df.dropna(), output_name, group_key)
            except Exception as e:
                err_msg = ("Unable to write query result for %s to influxDB: %s" % (output_name, str(e)))
                self.logger.error(err_msg)
                raise Exception(err_msg)

            container_key = "image="+group_key['image']
            current_settings[container_key] = {
                'requests': 0,
                'limits': math.ceil(df.loc[df.index[len(df)-1], 'value'])
            }

        return current_settings

    def recommend_node_sizes(self, node_summary):
        node_sizes = {}

        for column in node_summary:
            col_keys = node_summary[column].name
            group_key = col_keys[0]
            metric_type = col_keys[1]
            if metric_type == self.base_metric:
                node_sizes[group_key] = {
                    'size': math.ceil(node_summary[column][self.stat_type] * self.scaling_factor)
                }

        return node_sizes

    def recommend_container_cpu_settings(self, container_cpu_summary):
        container_cpu_settings = {}

        for column in container_cpu_summary:
            col_keys = container_cpu_summary[column].name
            group_key = col_keys[0]
            limit_value = max(float(self.config.get("UTILIZATION","MIN_CPU_LIMITS")), math.ceil(
                container_cpu_summary[column][self.stat_type]*self.scaling_factor*100)/100.0)
            container_cpu_settings[group_key] = {
                "requests": math.ceil(container_cpu_summary[column][self.stat_type]*100)/float(100),
                "limits": limit_value
            }

        return container_cpu_settings

    def recommend_container_mem_settings(self, container_mem_summary):
        container_mem_settings = {}

        for column in container_mem_summary:
            col_keys = container_mem_summary[column].name
            group_key = col_keys[0]
            if group_key not in container_mem_settings:
                container_mem_settings[group_key] = {'requests': 0, 'limits': 0}
            metric_type = col_keys[1]
            if metric_type == 'active':
                requests = math.ceil(container_mem_summary[column][self.stat_type])
                container_mem_settings[group_key]['requests'] = requests
            else: # metric_type = 'usage'
                limits = math.ceil(container_mem_summary[column][self.stat_type] * self.scaling_factor)
                container_mem_settings[group_key]['limits'] = limits

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

            if label_key not in current_settings.keys():
                current_settings[label_key] = {'requests': 0, 'limit': 0}

            results.append({
                "label_values": label_values,
                "summary_stats": summary_stats[label_key],
                "current_settings": current_settings[label_key],
                "recommended_settings": recommended_settings[label_key]
            })

        return results

    def store_analysis_results(self, sizing_result_doc):
        sizing_result_doc["config"] = {
            "stat_type": self.stat_type,
            "scaling_factor": self.scaling_factor,
            "base_metric": self.base_metric
        }

        try:
            self.resultdb[self.results_collection].insert_one(sizing_result_doc)
        except Exception as e:
            self.logger.error("Unable to store sizing result doc in MongoDB: %s" % str(sizing_result_doc))
            raise Exception("Unable to store sizing result doc in MongoDB: " + str(e))


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
