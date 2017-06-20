from flask import Flask, jsonify, request
from .config import get_config
from .util import JSONEncoderWithMongo, ObjectIdConverter
from .db import configdb, metricdb
from . import models


app = Flask(__name__)

app.config.update(get_config())
app.json_encoder = JSONEncoderWithMongo
app.url_map.converters["objectid"] = ObjectIdConverter


@app.route("/")
def index():
    return jsonify(status="ok")

@app.route("/available-apps")
def get_available_apps():
    return jsonify({
        collection: metricdb[collection].find({
            "appName": {"$exists": 1}},
            {"appName": 1},
        )
        for collection in ("calibration", "profiling", "validation")
    })

@app.route("/single-app/services/<app_name>")
def services_json(app_name):
    app = configdb.applications.find_one(
        filter={"name": app_name},
        projection={"_id": 0, "name": 1, "serviceNames": 1},
    )
    return jsonify(app=app["name"], services=app["serviceNames"])

@app.route("/single-app/profiling/<objectid:app_id>")
def profiling_json(app_id):
    app = metricdb.profiling.find_one(app_id)
    return jsonify(app)

@app.route("/single-app/calibration/<objectid:app_id>")
def calibration_json(app_id):
    app = metricdb.calibration.find_one(app_id)
    return jsonify(app)

@app.route("/cross-app/predict", methods=["POST"])
def predict():
    body = request.get_json()
    if body.get("model") == "LinearRegression1":
        model = models.LinearRegression1(num_dims=3)
        result = model.fit(None, None).predict(body["app_1"], body["app_2"])
        return jsonify(result.to_dict())
    else:
        response = jsonify(error="Model not found")
        response.status_code = 404
        return response
