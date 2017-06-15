import json
from pathlib import Path
from flask import Flask, render_template
from pymongo import MongoClient

app = Flask(__name__)
with open(Path(__file__).absolute().parent.parent / "config.json") as f:
    config = json.load(f)

mongo = MongoClient(host=config["mongoDB"]["url"], port=config["mongoDB"]["port"])
configdb = mongo.get_database(config["analyzer"]["configDB_name"])
configdb.authenticate(config["analyzer"]["mongoDB_user"], config["analyzer"]["mongoDB_password"])
metricdb = mongo.get_database(config["analyzer"]["metricDB_name"])
metricdb.authenticate(config["analyzer"]["mongoDB_user"], config["analyzer"]["mongoDB_password"])

@app.route("/")
def index():
    return render_template("index.html", apps=configdb.applications.find())
