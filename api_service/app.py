from flask import Flask, jsonify, request
from .config import get_config
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
    return ensure_document_fund(profiling)


# TODO: change back to uuid
@app.route("/get-next-instance-types/<string:app_id>", methods=["POST"])
def get_next_instance_types(app_id):
    if BO.get_status(app_id)['Status'] == "Running":
        response = jsonify(error="Optimization process still running")
        response.status_code = 400
        return response
    body = request.get_json()
    BO.get_candidates(app_id, body)
    return jsonify({"Status": "Submited"})

# TODO: change back to uuid
@app.route("/get-optimizer-status/<string:app_id>")
def get_task_status(app_id):
    response = jsonify(BO.get_status(app_id))
    return response
