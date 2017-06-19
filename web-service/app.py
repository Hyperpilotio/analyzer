from flask import Flask, jsonify
from .config import get_config
from .util import JSONEncoderWithMongo
from .db import configdb, metricdb


app = Flask(__name__)

app.config.update(get_config())
app.json_encoder = JSONEncoderWithMongo


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
