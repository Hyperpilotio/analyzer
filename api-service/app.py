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
    app = configdb.applications.find_one({"name": app_name})
    return jsonify(app=app["name"], services=app["serviceNames"])

@app.route("/cross-app/predict", methods=["POST"])
def predict():
    body = request.get_json()
    if body["model"] == "LinearRegression1":
        model = models.LinearRegression1(num_dims=3)
        result = model.fit(None, None).predict(body["app_1"], body["app_2"])
        return jsonify(result.to_dict())
    else:
        abort(make_response(jsonify(error="Model not found")), 404)
