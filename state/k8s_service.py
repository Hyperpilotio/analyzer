from config import get_config

from .db import configdb

config = get_config()

k8s_service_collection = config.get("ANALYZER", "K8S_SERVICE_COLLECTION")

def get_service(service_id):
    return configdb[k8s_service_collection].find_one({"service_id": service_id})

def create_service(service_json):
    configdb[k8s_service_collection].insert_one(service_json)
