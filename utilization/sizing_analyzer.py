import json
import pandas as pd
import numpy as np
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
        self.data = data
        self.error = error

    def to_dict(self):
        return {
            "status": self.status,
            "error": self.error,
            "data": self.data
        }


class SizingAnalyzer(object):
    def __init__(self):
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
        print("-- Query influxdb and compute node cpu usage stats --\n")
        output_filter = "derivative(sum(value)) / " + str(sample_interval) + " as node_usage"
        tags_filter = "mode=~ /(user|system)/"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        group_by = "group by instance,time(" + str(sample_interval) + "s)"
        node_cpu_usage_query = ("SELECT %s FROM node_cpu WHERE %s AND %s %s" 
                               % (output_filter, tags_filter, time_filter, group_by))

        #print("CPU usage query:\n", node_cpu_usage_query)
        try:
            node_cpu_usage_dict = self.influx_client_input.query(node_cpu_usage_query)
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to read node_cpu measurement from InfluxDB" + str(e))

        node_cpu_summary = pd.DataFrame()
        for k, df in node_cpu_usage_dict.items():
            node_name = k[1][0][1]
            try:
                self.influx_client_output.write_points(df, "node_cpu_usage", {'instance': node_name})
            except Exception as e:
                return JobStatus(status=Status.DB_ERROR,
                                 error="Unable to write query result back to influxDB" + str(e))
            #TODO: Need to filter out abnormal values
            node_cpu_summary[node_name] = df.node_usage.describe(percentiles)
                
        #print("node cpu usage summary: ", node_cpu_summary)
        # store_summary_stats(node_cpu_summary)

        print("--- Compute sizing recommendation for node cpu ---\n")
        # node_cpu_sizes = compute_sizing_recommendation(node_cpu_summary)
        # store_sizing_recommenation(node_cpu_sizes)

        return JobStatus(status=Status.SUCCESS)

    def analyze_node_memory(self, start_time, end_time, percentiles):
        print("-- Query influxdb and compute node memory usage and active stats --\n")
        output_filter = "value/1024/1024/1024"
        time_filter = "time > %d AND time <= %d" % (start_time, end_time)
        group_by = "group by instance"

        try:
            node_mem_active_dict = self.influx_client_input.query(
                "SELECT %s FROM node_memory_Active WHERE %s %s" % 
                 (output_filter, time_filter, group_by))       
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch node_memory_Active from influxDB" + str(e))

        try:
            node_mem_total_dict = self.influx_client_input.query(
                "SELECT %s FROM node_memory_MemTotal WHERE %s %s" %
                 (output_filter, time_filter, group_by))
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch node_memory_MemTotal from influxDB: " + str(e))
        
        try:
            node_mem_free_dict = self.influx_client_input.query(
                "SELECT %s FROM node_memory_MemFree WHERE %s %s" %
                 (output_filter, time_filter, group_by))
        except Exception as e:
            return JobStatus(status=Status.DB_ERROR,
                             error="Unable to fetch node_memory_MemFree from influxDB: " + str(e))

        node_mem_summary = pd.DataFrame()
        for k, df_active in node_mem_active_dict.items():
            node_name = k[1][0][1]
            try:
                self.influx_client_output.write_points(df_active, "node_memory_active", {'instance': node_name})
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
                self.influx_client_output.write_points(df_usage, "node_memory_usage", {'instance': node_name})
            except Exception as e:
                return JobStatus(status=STATUS.DB_ERROR,
                                 error="Unable to write query result back to influxDB: " + str(e))
            node_mem_summary[node_name, 'usage'] = df_usage.value.describe(percentiles)
       
        #print("node memory usage summary: ", node_mem_summary)
        #store_summary_stats(node_mem_summary)
        
        print("--- Compute sizing recommendation for node memory ---\n")
        # node_mem_sizes = compute_sizing_recommendation(node_mem_summary)
        # store_sizing_recommenation(node_mem_sizes)

        return JobStatus(status=Status.SUCCESS)


    def analyze_container_cpu(self, start_time, end_time, sample_interval, percentiles):
        print("-- Query influxdb and compute container cpu usage stats --\n")
        print("--- Compute requests and limits for container cpu ---\n")

        return JobStatus(status=Status.SUCCESS)
        
    def analyze_container_memory(self, start_time, end_time, sample_interval, percentiles):
        print("-- Query influxdb and compute container memory usage and working set stats --\n")
        print("--- Compute requests and limits for container memory ---\n")

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
