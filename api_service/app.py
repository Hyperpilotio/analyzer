import json
import sys
import traceback
from flask import Flask, jsonify, request
from pymongo import DESCENDING

from sizing_service.bayesian_optimizer_pool import BayesianOptimizerPool
from sizing_service.session_worker_pool import Status, SessionStatus
from sizing_service.linear_regression import LinearRegression1
from sizing_service.util import (get_calibration_dataframe, get_profiling_dataframe,
                           get_radar_dataframe)
from config import get_config
from logger import get_logger

from .db import configdb, metricdb
from .util import (JSONEncoderWithMongo, ObjectIdConverter,
                   ensure_document_found, shape_service_placement)

app = Flask(__name__)

app.json_encoder = JSONEncoderWithMongo
app.url_map.converters["objectid"] = ObjectIdConverter

my_config = get_config()
app_collection = my_config.get("ANALYZER", "APP_COLLECTION")
calibration_collection = my_config.get("ANALYZER", "CALIBRATION_COLLECTION")
profiling_collection = my_config.get("ANALYZER", "PROFILING_COLLECTION")
sizing_collection = my_config.get("ANALYZER", "SIZING_COLLECTION")

logger = get_logger(__name__, log_level=("APP", "LOGLEVEL"))

BOP = BayesianOptimizerPool()

@app.route("/")
def index():
    return jsonify(status="ok")


@app.route("/cluster")
def cluster_service_placement():
    with open(my_config.get("ANALYZER", "DEPLOY_JSON")) as f:
        deploy_json = json.load(f)
    result = shape_service_placement(deploy_json)
    return jsonify(result)


@app.route("/cluster/recommended")
def recommended_service_placement():
    with open(my_config.get("ANALYZER", "RECOMMENDED_DEPLOY_JSON")) as f:
        deploy_json = json.load(f)
    result = shape_service_placement(deploy_json)
    return jsonify(result)


@app.route("/apps")
def get_all_apps():
    with open(my_config.get("ANALYZER", "DEPLOY_JSON")) as f:
        deploy_json = json.load(f)
    apps = {}
    service_names = [
        task["deployment"]["metadata"]["name"]
        for task in deploy_json["kubernetes"]["taskDefinitions"]
        if task["deployment"]["metadata"].get("namespace") != "hyperpilot"
    ]
    for application in configdb[app_collection].find(
        {"serviceNames": {"$in": service_names}},
        {"name": 1, "serviceNames": 1}
    ):
        app_id = application.pop("_id")
        apps[str(app_id)] = application
    return jsonify(apps)


@app.route("/apps/<string:app_name>")
def get_app_info(app_id):
    application = configdb[app_collection].find_one({"name": app_name})
    return ensure_document_found(application)


@app.route("/apps/<string:app_name>/slo")
def get_app_slo(app_name):
    application = configdb[app_collection].find_one({"name": app_name})
    return ensure_document_found(application, ['slo'])


#@app.route("/apps/<string:app_name>/diagnosis")
#def get_app_slo(app_name):
#    application = configdb[app_collection].find_one({"name": app_name})
#    if application is None:
#        response = jsonify({"status": "bad_request",
#                            "error": "Target application not found"})
#        return response
#
#    result = {'state': "normal", 'incidents': "", 'risks': "", 'opportunities': ""}
#
#    return jsonify(result)


@app.route("/apps/<objectid:app_id>/calibration")
def app_calibration(app_id):
    application = configdb[app_collection].find_one(app_id)
    if app is None:
        return ensure_document_found(None)

    cursor = metricdb[calibration_collection].find(
        {"appName": application["name"]},
        {"appName": 0, "_id": 0},
    ).sort("_id", DESCENDING).limit(1)
    try:
        calibration = next(cursor)
        data = get_calibration_dataframe(calibration)
        del calibration["testResult"]
        calibration["results"] = data
        return jsonify(calibration)
    except StopIteration:
        return ensure_document_found(None)


@app.route("/apps/<objectid:app_id>/services/<service_name>/profiling")
def service_profiling(app_id, service_name):
    application = configdb[app_collection].find_one(app_id)
    if app is None:
        return ensure_document_found(None)

    cursor = metricdb[profiling_collection].find(
        {"appName": application["name"], "serviceInTest": service_name},
        {"appName": 0, "_id": 0},
    ).sort("_id", DESCENDING).limit(1)
    try:
        profiling = next(cursor)
        data = get_profiling_dataframe(profiling)
        del profiling["testResult"]
        profiling["results"] = data
        return jsonify(profiling)
    except StopIteration:
        return ensure_document_found(None)


@app.route("/apps/<objectid:app_id>/services/<service_name>/interference")
def interference_scores(app_id, service_name):
    application = configdb[app_collection].find_one(app_id)
    if application is None:
        return ensure_document_found(None)

    cursor = metricdb[profiling_collection].find(
        {"appName": application["name"], "serviceInTest": service_name}
    ).sort("_id", DESCENDING).limit(1)
    try:
        profiling = next(cursor)
        data = get_radar_dataframe(profiling)
        del profiling["testResult"]
        return jsonify(data)
    except StopIteration:
        return ensure_document_found(None)


@app.route("/cross-app/predict", methods=["POST"])
def predict():
    body = request.get_json()
    if body.get("model") == "LinearRegression1":
        model = LinearRegression1(numDims=3)
        result = model.fit(None, None).predict(
            body.get("app1"),
            body.get("app2"),
            body.get("collection")
        )
        return jsonify(result.to_dict())
    else:
        response = jsonify(error="Model not found")
        response.status_code = 404
        return response


@app.route("/apps/<string:session_id>/suggest-instance-types", methods=["POST"])
def get_next_instance_types(session_id):
    request_body = request.get_json()
    app_name = request_body['appName']

    # check if the target app exists in the configdb
    application = configdb[app_collection].find_one({"name": app_name})
    if application is None:
        response = jsonify({"status": "bad_request",
                            "error": "Target application not found"})
        return response

    # TODO: This causes the candidate list to be filtered twice - needs improvement
    if BOP.get_status(session_id).status == Status.RUNNING:
        response = jsonify({"status": "bad_request",
                            "error": "Optimization process still running"})
        return response

    logger.info(f"Starting a new sizing session {session_id} for app {app_name}")
    try:
        response = jsonify(BOP.get_candidates(session_id, request_body).to_dict())
    except Exception as e:
        logger.error(traceback.format_exc())
        response = jsonify({"status": "server_error",
                            "error":"Error in getting candidates from the sizing service: " + str(e)})

    return response


@app.route("/apps/<string:session_id>/get-optimizer-status")
def get_task_status(session_id):
    try:
        response = jsonify(BOP.get_status(session_id).to_dict())
    except Exception as e:
        logger.error(traceback.format_exc())
        response = jsonify({"status": "server_error",
                            "error": str(e)})
    return response
