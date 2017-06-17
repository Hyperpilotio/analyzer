import json
from parse import parse
from pathlib import Path
from flask import Flask, render_template, request, redirect, flash, url_for
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "5b52c330e091daea8979d94b3cbf6e4ff9f43fdf685787c8"
with open(Path(__file__).absolute().parent.parent / "config.json") as f:
    config = json.load(f)

mongo = MongoClient(host=config["mongoDB"]["url"], port=config["mongoDB"]["port"])
configdb = mongo.get_database(config["analyzer"]["configDB_name"])
configdb.authenticate(config["analyzer"]["mongoDB_user"], config["analyzer"]["mongoDB_password"])
metricdb = mongo.get_database(config["analyzer"]["metricDB_name"])
metricdb.authenticate(config["analyzer"]["mongoDB_user"], config["analyzer"]["mongoDB_password"])

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
        match = parse("slo-{name}", name)
        if match is not None:
            app_name = match["name"]
            val = float(value)
            update_result = configdb.applications.update_one(
                {"name": app_name},
                {"$set": {"slo.value": val}}
            )
            if update_result.modified_count > 0:
                updated.append(app_name)
    if updated:
        flash("Successfully updated SLO values for {}".format(", ".join(updated)))
    return redirect(url_for("index"))
