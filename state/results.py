from pymongo import DESCENDING
from .db import resultdb

from config import get_config

config = get_config()

incidents_collection = config.get("ANALYZER", "INCIDENT_COLLECTION")
diagnosis_collection = config.get("ANALYZER", "DIAGNOSIS_COLLECTION")
problems_collection = config.get("ANALYZER", "PROBLEM_COLLECTION")

def create_diagnosis(diagnosis_json):
    resultdb[diagnosis_collection].insert_one(diagnosis_json)


def get_last_app_incident(app_id):
    return resultdb[incidents_collection]. \
        find({"app_id": app_id}, {"_id": 0}). \
        sort("timestamp", DESCENDING).limit(1)


def get_last_app_diagnosis(app_id):
    return resultdb[diagnosis_collection]. \
        find({"app_id": app_id}, {"_id": 0}). \
        sort("timestamp", DESCENDING).limit(1)


def get_incident_diagnosis(app_id, incident_id):
    return resultdb[diagnosis_collection].find_one(
            {"$and": [
                {"app_id": app_id},
                {"incident_id": incident_id}]},
            {"_id": 0})


def get_diagnosis_between_time(app_id, start_ts, end_ts):
    return resultdb[diagnosis_collection]. \
            find({"$and": [{"app_id": app_id},
                           {"timestamp": {"$gte": start_ts}},
                           {"timestamp": {"$lte": end_ts}}]},
                 {"_id": 0})


def get_problem(problem_id):
    return resultdb[problems_collection].find_one({"problem_id": problem_id}, {"_id": 0})


def create_problem(problem_json):
    resultdb[problems_collection].insert_one(problem_json)


def get_problems_between_time(start_ts, end_ts):
    return resultdb[problems_collection].find(
        {"$and": [
            {"timestamp": {"$gte": start_ts}},
            {"timestamp": {"$lte": end_ts}}]},
        {"_id": 0})
