from pymongo import DESCENDING
from .db import resultdb

from config import get_config

config = get_config()

incidents_collection = config.get("ANALYZER", "INCIDENT_COLLECTION")
diagnosis_collection = config.get("ANALYZER", "DIAGNOSIS_COLLECTION")

def get_last_app_incident(app_id):
    return resultdb[incidents_collection]. \
        find({"app_id": app_id}, {"_id": 0}). \
        sort("timestamp", DESCENDING).limit(1)

def get_last_app_diagnosis(app_id):
    return resultdb[diagnosis_collection]. \
        find({"app_id": app_id}, {"_id": 0}). \
        sort("timestamp", DESCENDING).limit(1)

def get_incident_diagnosis(app_id, incident_id):
    return resultdb[diagnoses_collection].find_one(
            {"$and": [
                {"app_id": app_id},
                {"incident_id": incident_id}]},
            {"_id": 0})
