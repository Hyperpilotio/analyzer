import json
import traceback
from uuid import uuid1

from flask import Flask, jsonify, request
from pymongo import DESCENDING
from pymongo.errors import InvalidOperation

from sizing_service.bayesian_optimizer_pool import BayesianOptimizerPool
from sizing_service.linear_regression import LinearRegression1
import api_service.util as util
from config import get_config
from logger import get_logger

from .db import configdb, metricdb

app = Flask(__name__)

app.json_encoder = util.JSONEncoderWithMongo
app.url_map.converters["objectid"] = util.ObjectIdConverter

my_config = get_config()
app_collection = my_config.get("ANALYZER", "APP_COLLECTION")
calibration_collection = my_config.get("ANALYZER", "CALIBRATION_COLLECTION")
profiling_collection = my_config.get("ANALYZER", "PROFILING_COLLECTION")
sizing_collection = my_config.get("ANALYZER", "SIZING_COLLECTION")
k8s_service_collection = my_config.get("ANALYZER", "K8S_SERVICE_COLLECTION")

logger = get_logger(__name__, log_level=("APP", "LOGLEVEL"))

BOP = BayesianOptimizerPool()
APP_STATE = {"REGISTERED": "Registered",
             "UNREGISTERED": "Unregistered",
             "ACTIVE": "Active"}


@app.route("/")
def index():
    return jsonify(status=200)


@app.route("/apps", methods=["POST"])
def create_application():
    app_json = request.get_json()

    try:
        app_name = app_json["name"]
    except KeyError:
        return util.error_response("App name not found in application json.", 400)

    if "type" not in app_json:
        return util.error_response("App type not found in application json.", 400)

    app_id = app_name + "-" + str(uuid1())
    app_json["app_id"] = app_id
    app_json["state"] = APP_STATE["REGISTERED"]

    try:
        result = configdb[app_collection].insert_one(app_json)
        response = jsonify(data=app_json)
        response.status_code = 200
        return response
    except InvalidOperation:
        return util.error_response(f"Could not create application {app_name}.", 404)


@app.route("/apps", methods=["GET"])
def get_all_apps():
    apps = configdb[app_collection].find()
    response = jsonify(data=apps)
    response.status_code = 200
    return response


@app.route("/deprecated/apps", methods=["GET"])
def _get_all_apps():
    with open(my_config.get("ANALYZER", "DEPLOY_JSON")) as f:
        deploy_json = json.load(f)
    apps = {}
    service_names = [
        task["deployment"]["metadata"]["name"]
        for task in deploy_json["kubernetes"]["taskDefinitions"]
        if task["deployment"]["metadata"].get("namespace") != "hyperpilot"
    ]
    for application in configdb[app_collection].find(
            {"serviceNames": {"$in": service_names}},
            {"name": 1, "serviceNames": 1}
    ):
        app_id = application.pop("_id")
        apps[str(app_id)] = application
    return jsonify(apps)


@app.route("/apps/<string:app_id>", methods=["GET"])
def get_app_info_by_id(app_id):
    application = configdb[app_collection].find_one({"app_id": app_id})
    return util.ensure_document_found(application)


@app.route("/apps/info/<string:app_name>", methods=["GET"])
def get_app_info(app_name):
    application = configdb[app_collection].find_one({"name": app_name})
    return util.ensure_document_found(application)


# @app.route("/apps/<string:app_name>/slo", methods=["GET"])
# def get_app_slo(app_name):
#     application = configdb[app_collection].find_one({"name": app_name})
#     return util.ensure_document_found(application, ['slo'])


@app.route("/apps/<string:app_id>", methods=["PUT"])
def update_app(app_id):
    app_json = request.get_json()
    return util.update_and_return_doc(app_id, app_json)


@app.route("/apps/<string:app_id>", methods=["DELETE"])
def delete_app(app_id):
    # Method to keep app in internal system but with unregistered state.

    # Check for existence
    app = configdb[app_collection].find_one({"app_id": app_id})
    if not app:
        return util.error_response(f"Tried to delete app {app_id} but app not found.", 404)
    result = configdb[app_collection].update_one(
        {"app_id": app_id},
        {"$set": {"state": APP_STATE["UNREGISTERED"]}}
    )
    if result.modified_count > 0:
        return jsonify(status=200, deleted_id=app_id)
    return util.error_response(f"Could not delete app {app_id}.", 404)


@app.route("/apps/<string:app_id>/microservices", methods=["POST"])
def add_app_services(app_id):
    app_json = request.get_json()
    microservices = util.get_app_microservices(app_id)
    if microservices is not None:
        microservices.extend(ms for ms in app_json["microservices"]
                             if ms not in microservices)
        app_json["microservices"] = microservices
    return util.update_and_return_doc(app_id, app_json)


@app.route("/apps/<string:app_id>/microservices", methods=["GET"])
def get_app_microservices(app_id):
    microservices = util.get_app_microservices(app_id)
    if microservices is not None:
        response = jsonify(data=microservices)
        response.status_code = 200
        return response
    return util.error_response("Could not find application microservices.", 404)


# app.route("/apps/<string:app_name>/diagnosis")
# def get_app_slo(app_name):
#    application = configdb[app_collection].find_one({"name": app_name})
#    if application is None:
#        response = jsonify({"status": "bad_request",
#                            "error": "Target application not found"})
#        return response
#
#    result = {'state': "normal", 'incidents': "", 'risks': "", 'opportunities': ""}
#
#    return jsonify(result)


@app.route("/apps/<objectid:app_id>/calibration")
def app_calibration(app_id):
    application = configdb[app_collection].find_one(app_id)
    if app is None:
        return util.ensure_document_found(None)

    cursor = metricdb[calibration_collection].find(
        {"appName": application["name"]},
        {"appName": 0, "_id": 0},
    ).sort("_id", DESCENDING).limit(1)
    try:
        calibration = next(cursor)
        data = util.get_calibration_dataframe(calibration)
        del calibration["testResult"]
        calibration["results"] = data
        return jsonify(calibration)
    except StopIteration:
        return util.ensure_document_found(None)


@app.route("/apps/<objectid:app_id>/services/<service_name>/profiling")
def service_profiling(app_id, service_name):
    application = configdb[app_collection].find_one(app_id)
    if app is None:
        return util.ensure_document_found(None)

    cursor = metricdb[profiling_collection].find(
        {"appName": application["name"], "serviceInTest": service_name},
        {"appName": 0, "_id": 0},
    ).sort("_id", DESCENDING).limit(1)
    try:
        profiling = next(cursor)
        data = util.get_profiling_dataframe(profiling)
        del profiling["testResult"]
        profiling["results"] = data
        return jsonify(profiling)
    except StopIteration:
        return util.ensure_document_found(None)


@app.route("/apps/<objectid:app_id>/services/<service_name>/interference")
def interference_scores(app_id, service_name):
    application = configdb[app_collection].find_one(app_id)
    if application is None:
        return util.ensure_document_found(None)

    cursor = metricdb[profiling_collection].find(
        {"appName": application["name"], "serviceInTest": service_name}
    ).sort("_id", DESCENDING).limit(1)
    try:
        profiling = next(cursor)
        data = util.get_radar_dataframe(profiling)
        del profiling["testResult"]
        return jsonify(data)
    except StopIteration:
        return util.ensure_document_found(None)


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


@app.route("/apps/<string:session_id>/suggest-instance-types", methods=["POST"])
def get_next_instance_types(session_id):
    request_body = request.get_json()
    app_name = request_body['appName']

    # check if the target app exists in the configdb
    application = configdb[app_collection].find_one({"name": app_name})
    if application is None:
        response = jsonify({"status": "bad_request",
                            "error": "Target application not found"})
        return response

    # TODO: This causes the candidate list to be filtered twice - needs improvement
    if BOP.get_status(session_id).status == Status.RUNNING:
        response = jsonify({"status": "bad_request",
                            "error": "Optimization process still running"})
        return response

    logger.info(
        f"Starting a new sizing session {session_id} for app {app_name}")
    try:
        response = jsonify(BOP.get_candidates(
            session_id, request_body).to_dict())
    except Exception as e:
        logger.error(traceback.format_exc())
        response = jsonify({"status": "server_error",
                            "error": "Error in getting candidates from the sizing service: " + str(e)})

    return response


@app.route("/apps/<string:session_id>/get-optimizer-status")
def get_task_status(session_id):
    try:
        response = jsonify(BOP.get_status(session_id).to_dict())
    except Exception as e:
        logger.error(traceback.format_exc())
        response = jsonify({"status": "server_error",
                            "error": str(e)})
    return response


# @app.route("/modify-slo", methods=["GET"])
# def modification_form():
#     return render_template("modification_form.html", apps=configdb.applications.find())
#
#
# @app.route("/modify-slo", methods=["POST"])
# def modify_slo():
#     updated = []
#     for name, value in request.form.items():
#         match = parse("slo-{name}-{metric}", name)
#         if match is not None:
#             app_name = match["name"]
#             metric = match["metric"]
#             if metric == "value":
#                 try:
#                     value = int(value)
#                 except ValueError:
#                     value = float(value)
#             update_result = configdb.applications.update_one(
#                 {"name": app_name},
#                 {"$set": {f"slo.{metric}": value}}
#             )
#             if update_result.modified_count > 0:
#                 updated.append(app_name)
#     if updated:
#         flash("Successfully updated SLO values for %s" % ", ".join(updated))
#     return redirect(url_for("index"))


@app.route("/cluster")
def cluster_service_placement():
    with open(my_config.get("ANALYZER", "DEPLOY_JSON")) as f:
        deploy_json = json.load(f)
    result = util.shape_service_placement(deploy_json)
    return jsonify(result)


@app.route("/cluster/recommended")
def recommended_service_placement():
    with open(my_config.get("ANALYZER", "RECOMMENDED_DEPLOY_JSON")) as f:
        deploy_json = json.load(f)
    result = util.shape_service_placement(deploy_json)
    return jsonify(result)


@app.route("/k8s_services/<string:service_id>", methods=["GET"])
def get_k8s_service(service_id):
    service = configdb[k8s_service_collection].find_one({"service_id": service_id})
    service.pop("_id")
    return util.ensure_document_found(service)


@app.route("/k8s_services", methods=["POST"])
def create_k8s_service():
    service_json = request.get_json()
    # TODO: Pick a better service id name
    service_id = "service-" + str(uuid1())
    service_json["service_id"] = service_id
    # TODO: Validate the json?
    try:
        result = configdb[k8s_service_collection].insert_one(service_json)
        response = jsonify(data=service_id)
        response.status_code = 200
        return response
    except InvalidOperation as e:
        return util.error_response(f"Could not create service: " + str(e), 500)


@app.route("/apps/<string:app_id>/state", methods=["GET"])
def get_app_state(app_id):
    app = configdb[app_collection].find_one({"app_id": app_id})
    if app is None:
        return util.ensure_document_found(None)
    response = jsonify({"state": app["state"]})
    return response


@app.route("/apps/<string:app_id>/state", methods=["PUT"])
def update_app_state(app_id):
    app = configdb[app_collection].find_one({"app_id": app_id})
    if app is None:
        return util.ensure_document_found(None)

    state_json = request.get_json()
    state = state_json["state"]
    if state != APP_STATE["REGISTERED"] and state != APP_STATE["UNREGISTERED"] and state != APP_STATE["ACTIVE"]:
        return util.error_response(f"{state} is not valid state", 400)
    app["state"] = state

    return util.update_and_return_doc(app_id, app)


@app.route("/apps/<string:app_id>/slo", methods=["GET"])
def get_app_slo(app_id):
    application = configdb[app_collection].find_one({"app_id": app_id})
    if application is None:
        return util.ensure_document_found(None)

    try:
        response = jsonify(SLO=application['slo'])
    except KeyError:
        return util.error_response(f"SLO is not found", 400)
    else:
        response.status_code = 200
        return response


@app.route("/apps/<string:app_id>/slo", methods=["PUT"])
def update_app_slo(app_id):
    application = configdb[app_collection].find_one({"app_id": app_id})
    if application is None:
        return util.ensure_document_found(None)

    try:
        application['slo']
    except KeyError:
        return util.error_response(f"SLO is not added in application: {app_id}", 400)

    try:
        new_slo_json = request.get_json()["SLO"]
    except KeyError:
        return util.error_response(f"SLO is not found in new data", 400)

    application['slo'] = new_slo_json
    return util.update_and_return_doc(app_id, application)


@app.route("/apps/<string:app_id>/slo", methods=["POST"])
def add_app_slo(app_id):
    application = configdb[app_collection].find_one({"app_id": app_id})
    if application is None:
        return util.ensure_document_found(None)

    if "slo" in application:
        return util.error_response(f"SLO already set", 400)

    state_json = request.get_json()
    try:
        slo = state_json["SLO"]
    except KeyError:
        return util.error_response(f"SLO is not found in new data", 400)

    return util.update_and_return_doc(app_id, {"slo": slo})


@app.route("/apps/<string:app_id>/slo", methods=["DELETE"])
def delete_app_slo(app_id):
    application = configdb[app_collection].find_one({"app_id": app_id})
    if application is None:
        return util.ensure_document_found(None)

    try:
        application['slo']
    except KeyError:
        return util.error_response(f"SLO is not added in application: {app_id}", 400)

    return util.update_and_return_doc(app_id, {"slo": ""}, unset=True)
