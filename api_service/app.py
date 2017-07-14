from flask import Flask, jsonify, request
from config import get_config
from pymongo import DESCENDING
from .util import JSONEncoderWithMongo, ObjectIdConverter, ensure_document_found
from .db import configdb, metricdb
from analyzer.linear_regression import LinearRegression1
from analyzer.bayesian_optimizer_pool import BayesianOptimizerPool
from analyzer.util import get_calibration_dataframe, get_profiling_dataframe, get_radar_dataframe

app = Flask(__name__)

app.config.update(get_config())
app.json_encoder = JSONEncoderWithMongo
app.url_map.converters["objectid"] = ObjectIdConverter

BO = BayesianOptimizerPool.instance()


@app.route("/")
def index():
    return jsonify(status="ok")


@app.route("/apps")
def get_all_apps():
    return jsonify({ "apps": configdb.applications.find({}, {"name": 1}) })


@app.route("/apps/<objectid:app_id>/calibration")
def app_calibration(app_id):
    app = configdb.applications.find_one(app_id)
    if app is None:
        return ensure_document_found(None)

    cursor = metricdb.calibration.find(
        {"appName": app["name"]},
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


@app.route("/apps/<objectid:app_id>/profiling")
def app_profiling(app_id):
    app = configdb.applications.find_one(app_id)
    if app is None:
        return ensure_document_found(None)

    cursor = metricdb.profiling.find(
        {"appName": app["name"]},
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


@app.route("/available-apps")
def get_available_apps():
    return jsonify({
        collection: metricdb[collection].find(
            filter={"appName": {"$exists": 1}},
            projection={"appName": 1},
        )
        for collection in ("calibration", "profiling", "validation")
    })


@app.route("/single-app/services/<app_name>")
def services_json(app_name):
    app_config = configdb.applications.find_one(
        filter={"name": app_name},
        projection={"_id": 0, "name": 1, "serviceNames": 1},
    )
    return ensure_document_found(app_config, app="name", services="serviceNames")


@app.route("/single-app/profiling/<objectid:app_id>")
def profiling_json(app_id):
    profiling = metricdb.profiling.find_one(app_id)
    return ensure_document_found(profiling)


@app.route("/single-app/profiling-data/<objectid:app_id>")
def profiling_data(app_id):
    profiling = metricdb.profiling.find_one(app_id)
    data = get_profiling_dataframe(profiling)
    if data is not None:
        profiling["testResult"] = data
    return ensure_document_found(profiling)


@app.route("/single-app/calibration/<objectid:app_id>")
def calibration_json(app_id):
    calibration = metricdb.calibration.find_one(app_id)
    return ensure_document_found(calibration)


@app.route("/single-app/calibration-data/<objectid:app_id>")
def calibration_data(app_id):
    calibration = metricdb.calibration.find_one(app_id)
    data = get_calibration_dataframe(calibration)
    if data is not None:
        calibration["testResult"] = data
    return ensure_document_found(calibration)


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


@app.route("/radar-data/<objectid:app_id>")
def radar_data(app_id):
    profiling = metricdb.profiling.find_one(app_id)
    data = get_radar_dataframe(profiling)
    if data is not None:
        profiling['radarChartData'] = data
        del profiling['testResult']
    return ensure_document_found(profiling)


# TODO: change back to uuid
@app.route("/apps/<string:app_id>/suggest-instance-types", methods=["POST"])
def get_next_instance_types(app_id):
    if BO.get_status(app_id)['Status'] == "Running":
        response = jsonify(error="Optimization process still running")
        response.status_code = 400
        return response
    body = request.get_json()
    BO.get_candidates(app_id, body)
    return jsonify({"Status": "Submited"})

# TODO: change back to uuid


@app.route("/apps/<string:app_id>/get-optimizer-status/")
def get_task_status(app_id):
    response = jsonify(BO.get_status(app_id))
    return response
