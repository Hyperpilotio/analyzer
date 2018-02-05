from config import get_config
from logger import get_logger

from .db import jobdb

config = get_config()

job_collection = config.get("JOBS", "JOB_COLLECTION")

def get_job_status(job_name):
    return jobdb[job_collection].find({"job_name": job_name})

def save_job_status(job_name, job_status):
    jobdb[job_collection].update_one({"job_name": job_name}, {"$set": job_status}, True)
