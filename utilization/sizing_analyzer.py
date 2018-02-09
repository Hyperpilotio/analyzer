import json
import ast
import pandas as pd
import numpy as np
import datetime
from influxdb import DataFrameClient

from config import get_config
from logger import get_logger

config = get_config()


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
    return yesterday.timestamp(), today.timestamp()

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
        self.logger = get_logger(__name__, log_level=("JOBS", "LOGLEVEL"))

        self.percentiles = ast.literal_eval(config.get("UTILIZATION", "PERCENTILES"))
        self.stat_type = config.get("UTILIZATION", "DEFAULT_STAT")
        
        #influx_host = config.get("INFLUXDB", "HOST")
        influx_host = "localhost"
        influx_port = config.get("INFLUXDB", "PORT")
        influx_user = config.get("INFLUXDB", "USERNAME")
        influx_password = config.get("INFLUXDB", "PASSWORD")
        input_db = config.get("INFLUXDB", "SIZING_INPUT_DB_NAME")
        output_db = config.get("INFLUXDB", "SIZING_OUTPUT_DB_NAME")
        mongo_result_db = config.get("MONGODB", "RESULT_DB_NAME")

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


    def analyze_node_cpu(self, start_time, end_time):
        print("-- [node_cpu] Query influxdb for raw metrics data --")
        output_filter = "derivative(sum(value), 1s) as usage"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        tags_filter = "AND mode=~ /(user|system)/"
        group_tags = "instance,time(1ms)"

        metric_name = "node_cpu"
        try:
            node_cpu_usage_dict = self.influx_client_input.query(
                "SELECT %s FROM %s WHERE %s %s GROUP BY %s" %
                 (output_filter, metric_name, time_filter, tags_filter, group_tags))
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: " % (metric_name, str(e)))

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
            node_cpu_summary[node_name] = df.usage.describe(self.percentiles)

        #print("node cpu usage summary: ", node_cpu_summary)

        self.logger.info("-- [node_cpu] Query influxdb for current node configs --")

        self.logger.info("-- [node_cpu] Compute sizing recommendation --")
        # node_cpu_sizes = compute_sizing_recommendation(node_cpu_summary, stat_type)

        self.logger.info("-- [node_cpu] Store analysis results in mongodb --")
        # store_analysis_result(node_cpu_summary, node_cpu_sizes)

        return JobStatus(status=Status.SUCCESS)


    def analyze_node_memory(self, start_time, end_time):
        self.logger.info("-- [node_memory] Query influxdb for raw metrics data --")
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

        metric_name_free = "node_memory_MemFree"
        try:
            node_mem_free_dict = self.influx_client_input.query(
                "SELECT %s FROM %s WHERE %s GROUP BY %s" %
                 (output_filter, metric_name_free, time_filter, group_tags))
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
            node_mem_summary[node_name, 'active'] = df_active.value.describe(self.percentiles)

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
            node_mem_summary[node_name, 'usage'] = df_usage.value.describe(self.percentiles)

        #print("node memory usage summary: ", node_mem_summary)

        self.logger.info("-- [node_memory] Query influxdb for current node configs --")

        self.logger.info("-- [node_memory] Compute sizing recommendation --")
        # node_mem_sizes = compute_sizing_recommendation(node_mem_summary, stat_type)

        self.logger.info("-- [node_memory] Store analysis results in mongodb --")
        # store_analysis_result(node_mem_summary, node_mem_sizes)

        return JobStatus(status=Status.SUCCESS)


    def analyze_container_cpu(self, start_time, end_time):
        self.logger.info("-- [container_cpu] Query influxdb for raw metrics data --")
        output_filter = "derivative(sum(value), 1s) as usage"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        tags_filter = "AND image!=''"
        group_tags = "image,pod_name,time(1ms)"

        metric_name = "container_cpu_user_seconds_total"
        try:
            container_cpu_user_dict = self.influx_client_input.query(
                "SELECT %s FROM %s WHERE %s %s GROUP BY %s" %
                 (output_filter, metric_name, time_filter, tags_filter, group_tags))
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch %s from influxDB: %s" % (metric_name, str(e)))

        metric_name_sys = "container_cpu_system_seconds_total"
        try:
            container_cpu_sys_dict = self.influx_client_input.query(
                "SELECT %s FROM %s WHERE %s %s GROUP BY %s" %
                 (output_filter, metric_name_sys, time_filter, tags_filter, group_tags))
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
                col_max = np.maximum(container_cpu_usage_dict[image_name].as_matrix(), df_usage.as_matrix())
                container_cpu_usage_dict[image_name].loc[:,'usage'] = col_max

        container_cpu_summary = pd.DataFrame()
        for image_name, df_usage in container_cpu_usage_dict.items():
            df_usage = df_usage.dropna()
            try:
                self.influx_client_output.write_points(
                    df_usage, "container_cpu_usage", {'image': image_name})
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            container_cpu_summary[image_name] = df_usage.usage.describe(self.percentiles)

        #print("container cpu usage summary: ", container_cpu_summary)

        self.logger.info("-- [container_cpu] Query influxdb for current requests and limits --")

        self.logger.info("-- [container_cpu] Compute requests and limits --")
        # container_cpu_settings = compute_sizing_recommendation(container_cpu_summary, stat_type)

        self.logger.info("-- [container_cpu] Store analysis results in mongodb --")
        # store_analysis_result(container_cpu_summary, container_cpu_settings)

        return JobStatus(status=Status.SUCCESS)


    def analyze_container_memory(self, start_time, end_time):
        self.logger.info("-- [container_memory] Query influxdb for raw metrics data --")
        output_filter = "max(value)/1024/1024 as value"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        tags_filter = "AND image!=''"
        group_tags = "image,time(5s)"

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
            container_mem_summary[image_name, 'active'] = df_active.value.describe(self.percentiles)

        for k, df_usage in container_mem_usage_dict.items():
            image_name = k[1][0][1]
            df_usage = df_usage.dropna()
            try:
                self.influx_client_output.write_points(
                    df_usage, "container_memory_usage", {'image': image_name})
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            container_mem_summary[image_name, 'usage'] = df_usage.value.describe(self.percentiles)

        #print("container memory usage summary: ", container_mem_summary)

        self.logger.info("-- [container_memory] Query influxdb for current requests and limits --")

        self.logger.info("-- [container_memory] Compute requests and limits --")
        # container_mem_settings = compute_sizing_recommendation(container_mem_summary, stat_type)

        self.logger.info("-- [container_memory] Store analysis results in mongodb --")
        # store_analysis_result(container_mem_summary, container_mem_settings)

        return JobStatus(status=Status.SUCCESS)


if __name__ == "__main__":
    sa = SizingAnalyzer(config)
    end_time = 1517016459493000000
    ANALYSIS_WINDOW_SECOND = 300
    NANOSECONDS_PER_SECOND = 1000000000
    start_time = end_time - ANALYSIS_WINDOW_SECOND * NANOSECONDS_PER_SECOND

    job = sa.analyze_node_cpu(start_time, end_time)
    print(job.to_dict())
    job = sa.analyze_node_memory(start_time, end_time)
    print(job.to_dict())
    job = sa.analyze_container_cpu(start_time, end_time)
    print(job.to_dict())
    job = sa.analyze_container_memory(start_time, end_time)
    print(job.to_dict())
