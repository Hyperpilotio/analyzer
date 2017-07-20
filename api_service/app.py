from flask import Flask, jsonify, request
from pymongo import DESCENDING
from .config import get_config
from .util import (
    JSONEncoderWithMongo,
    ObjectIdConverter,
    ensure_document_found,
    shape_service_placement,
)
from .db import configdb, metricdb
from analyzer.linear_regression import LinearRegression1
from analyzer.util import (
    get_calibration_dataframe,
    get_profiling_dataframe,
    get_radar_dataframe,
)
import json

app = Flask(__name__)

app.config.update(get_config())
app.json_encoder = JSONEncoderWithMongo
app.url_map.converters["objectid"] = ObjectIdConverter


@app.route("/")
def index():
    return jsonify(status="ok")


@app.route("/cluster")
def cluster_service_placement():
    with open(app.config["ANALYZER"]["DEPLOY_JSON"]) as f:
        deploy_json = json.load(f)
    result = shape_service_placement(deploy_json)
    return jsonify(result)


@app.route("/cluster/recommended")
def recommended_service_placement():
    with open(app.config["ANALYZER"]["RECOMMENDED_DEPLOY_JSON"]) as f:
        deploy_json = json.load(f)
    result = shape_service_placement(deploy_json)
    return jsonify(result)


@app.route("/apps")
def get_all_apps():
    with open(app.config["ANALYZER"]["DEPLOY_JSON"]) as f:
        deploy_json = json.load(f)
    apps = {}
    service_names = [
        task["deployment"]["metadata"]["name"]
        for task in deploy_json["kubernetes"]["taskDefinitions"]
        if task["deployment"]["metadata"].get("namespace") != "hyperpilot"
    ]
    for application in configdb.applications.find(
        {"serviceNames": {"$in": service_names}},
        {"name": 1, "serviceNames": 1}
    ):
        app_id = application.pop("_id")
        apps[str(app_id)] = application
    return jsonify(apps)


@app.route("/apps/<objectid:app_id>")
def get_app_info(app_id):
    application = configdb.applications.find_one(app_id, {"_id": 0})
    return ensure_document_found(application)


@app.route("/apps/<objectid:app_id>/calibration")
def app_calibration(app_id):
    application = configdb.applications.find_one(app_id)
    if app is None:
        return ensure_document_found(None)

    cursor = metricdb.calibration.find(
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
    application = configdb.applications.find_one(app_id)
    if app is None:
        return ensure_document_found(None)

    cursor = metricdb.profiling.find(
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
    application = configdb.applications.find_one(app_id)
    if application is None:
        return ensure_document_found(None)

    cursor = metricdb.profiling.find(
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
