from flask import Flask, jsonify
from configparser import ConfigParser
from pathlib import Path


app = Flask(__name__)

config = ConfigParser()
config.read(Path(__file__).absolute().parent.parent / "config.ini")
app.config.update(config)


@app.route("/")
def index():
    return jsonify(status="ok")
