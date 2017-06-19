from flask import Flask, jsonify
from .config import get_config
from .db import configdb, metricdb


app = Flask(__name__)

app.config.update(get_config())


@app.route("/")
def index():
    return jsonify(status="ok")


@app.route("/single-app/services/<app_name>")
def services_json(app_name):
    app = configdb.applications.find_one({"name": app_name})
    return jsonify(app=app["name"], services=app["serviceNames"])
