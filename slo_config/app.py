import json
from configparser import ConfigParser
from parse import parse
from pathlib import Path
from flask import Flask, render_template, request, redirect, flash, url_for
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "5b52c330e091daea8979d94b3cbf6e4ff9f43fdf685787c8"
config = ConfigParser()
config.read(Path(__file__).resolve().parent.parent / "config.ini")

mongo = MongoClient(host=config["MONGODB"]["HOST"], port=config["MONGODB"].getint("PORT"))
configdb = mongo.get_database(config["ANALYZER"]["CONFIGDB_NAME"])
configdb.authenticate(config["MONGODB"]["USERNAME"], config["MONGODB"]["PASSWORD"])
metricdb = mongo.get_database(config["ANALYZER"]["METRICDB_NAME"])
metricdb.authenticate(config["MONGODB"]["USERNAME"], config["MONGODB"]["PASSWORD"])

@app.route("/")
def index():
    apps = list(configdb.applications.find())
    for app in apps:
        app["loadTester"] = json.dumps(app["loadTester"], indent=4)
    return render_template("index.html", apps=apps)


@app.route("/modify-slo", methods=["GET"])
def modification_form():
    return render_template("modification_form.html", apps=configdb.applications.find())

@app.route("/modify-slo", methods=["POST"])
def modify_slo():
    updated = []
    for name, value in request.form.items():
        match = parse("slo-{name}-{metric}", name)
        if match is not None:
            app_name = match["name"]
            metric = match["metric"]
            if metric == "value":
                try:
                    value = int(value)
                except ValueError:
                    value = float(value)
            update_result = configdb.applications.update_one(
                {"name": app_name},
                {"$set": {f"slo.{metric}": value}}
            )
            if update_result.modified_count > 0:
                updated.append(app_name)
    if updated:
        flash("Successfully updated SLO values for %s" % ", ".join(updated))
    return redirect(url_for("index"))
