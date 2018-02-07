from config import get_config
from logger import get_logger

from .db import jobdb

config = get_config()

job_collection = config.get("JOBS", "JOB_COLLECTION")

def get_job_state(job_name):
    return jobdb[job_collection].find({"job_name": job_name})

def get_job_states():
    return jobdb[job_collection].find()

def save_job_state(job_name, job_state):
    jobdb[job_collection].update_one({"job_name": job_name}, {"$set": job_state}, True)
