import json
import traceback
import time
from uuid import uuid1

from flask import Flask, jsonify, request
from pymongo import DESCENDING
from pymongo.errors import InvalidOperation

from sizing_service.bayesian_optimizer_pool import BayesianOptimizerPool
from sizing_service.linear_regression import LinearRegression1
from diagnosis.app_analyzer import DiagnosisTracker
import api_service.util as util
from state import apps as appstate
from state import results as resultstate
from state import k8s_service as k8sservicestate
from config import get_config
from logger import get_logger

from .db import metricdb, resultdb

app = Flask(__name__)

app.json_encoder = util.JSONEncoderWithMongo
app.url_map.converters["objectid"] = util.ObjectIdConverter

my_config = get_config()
calibration_collection = my_config.get("ANALYZER", "CALIBRATION_COLLECTION")
profiling_collection = my_config.get("ANALYZER", "PROFILING_COLLECTION")
sizing_collection = my_config.get("ANALYZER", "SIZING_COLLECTION")
risks_collection = my_config.get("ANALYZER", "RISK_COLLECTION")
opportunities_collection = my_config.get("ANALYZER", "OPPORTUNITY_COLLECTION")

logger = get_logger(__name__, log_level=("APP", "LOGLEVEL"))

BOP = BayesianOptimizerPool()
APP_STATE = {"REGISTERED": "Registered",
             "UNREGISTERED": "Unregistered",
             "ACTIVE": "Active"}
FEATURE_NAME = {"INTERFERENCE": "interference_management",
                "BOTTLENECK": "bottleneck_management",
                "EFFICIENCY": "efficiency_management"}

DIAGNOSIS = DiagnosisTracker(my_config)

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
        result = appstate.create_app(app_json)
        response = jsonify(data=app_json)
        response.status_code = 200
        return response
    except InvalidOperation:
        return util.error_response(f"Could not create application {app_name}.", 404)


@app.route("/apps", methods=["GET"])
def get_all_apps():
    state_filter = request.args.get("state")
    if state_filter:
        all_apps = appstate.get_all_apps_by_state(state_filter)
    else:
        all_apps = appstate.get_all_apps()
    response = jsonify(data=all_apps)
    response.status_code = 200
    return response


@app.route("/apps/<string:app_id>", methods=["GET"])
def get_app_info_by_id(app_id):
    application = appstate.get_app_by_id(app_id)
    return util.ensure_document_found(application)


@app.route("/apps/info/<string:app_name>", methods=["GET"])
def get_app_info(app_name):
    application = appstate.get_app_by_name(app_name)
    return util.ensure_document_found(application)


@app.route("/apps/info/<string:app_name>/slo", methods=["GET"])
def get_app_slo_by_name(app_name):
    application = appstate.get_app_by_name(app_name)
    if application is None:
        return util.ensure_document_found(None)
    if "slo" not in application:
        return util.error_response(f"SLO is not found", 400)
    return util.ensure_document_found(application['slo'])


@app.route("/apps/<string:app_id>", methods=["PUT"])
def update_app(app_id):
    app_json = request.get_json()
    if "slo" in app_json:
        # TODO: Fix namespace prefix that's added by our snap collector
        metric_name = app_json["slo"]["metric"]["name"]
        app_json["slo"]["metric"]["name"] = "hyperpilot/prometheus/" + metric_name

    return util.update_and_return_doc(app_id, app_json)

@app.route("/apps/<string:app_id>", methods=["DELETE"])
def delete_app(app_id):
    # Method to keep app in internal system but with unregistered state.

    # Check for existence
    app = appstate.get_app_by_id(app_id)
    if not app:
        return util.error_response(f"Tried to delete app {app_id} but app not found.", 404)
    result = appstate.update_app(app_id, {"state": APP_STATE["UNREGISTERED"]})
    if result.modified_count > 0:
        return jsonify(status=200, deleted_id=app_id)
    return util.error_response(f"Could not delete app {app_id}.", 404)


@app.route("/apps/<string:app_id>/microservices", methods=["POST"])
def add_app_services(app_id):
    app_json = request.get_json()
    microservices = appstate.get_app_microservices(app_id)
    if microservices is not None:
        microservices.extend(ms for ms in app_json["microservices"]
                             if ms not in microservices)
        app_json["microservices"] = microservices
    return util.update_and_return_doc(app_id, app_json)


@app.route("/apps/<string:app_id>/microservices", methods=["GET"])
def get_app_microservices(app_id):
    microservices = appstate.get_app_microservices(app_id)
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
    application = appstate.get_app_by_id(app_id)
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
    application = appstate.get_app_by_id(app_id)
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
    application = appstate.get_app_by_id(app_id)
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
    application = appstate.get_app_by_name(app_name)
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
    service = k8sservicestate.get_service(service_id)
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
        k8sservicestate.create_service(service_json)
        response = jsonify(data=service_id)
        response.status_code = 200
        return response
    except InvalidOperation as e:
        return util.error_response(f"Could not create service: " + str(e), 500)


@app.route("/apps/<string:app_id>/pods", methods=["GET"])
def get_pod_names(app_id):
    app = appstate.get_app_by_id(app_id)
    if app is None:
        return util.ensure_document_found(None)
    pod_names = []
    for microservice in app["microservices"]:
        service_id = microservice["service_id"]
        microservice_doc = k8sservicestate.get_service(service_id)
        if microservice_doc is None:
            return util.error_response("Microservice with id %s not found" %
                                       service_id, 400)
        pod_names += microservice_doc["pods"]
    return jsonify(pod_names)


@app.route("/apps/<string:app_id>/state", methods=["GET"])
def get_app_state(app_id):
    app = appstate.get_app_by_id(app_id)
    if app is None:
        return util.ensure_document_found(None)
    return util.ensure_document_found({"state": app["state"]})


@app.route("/apps/<string:app_id>/state", methods=["PUT"])
def update_app_state(app_id):
    app = appstate.get_app_by_id(app_id)
    if app is None:
        return util.ensure_document_found(None)

    state_json = request.get_json()
    state = state_json["state"]
    if state != APP_STATE["REGISTERED"] and state != APP_STATE["UNREGISTERED"] and state != APP_STATE["ACTIVE"]:
        return util.error_response(f"{state} is not valid state", 400)

    app["state"] = state

    updated_doc = appstate.update_and_get_app(app_id, app)
    if not updated_doc:
        return util.error_response(f"Could not update app {app_id}.", 404)

    # NOTE: Currently the UI is only calling this generic update API to update SLO and k8s objects.
    # Therefore we have to intercept here to start the diagnosis flow, since we need app SLO
    # to start it.
    # TODO: We should only try to start the diagnosis flow once, and also it's not gurantee we
    # have all the information we need already....
    if "slo" in updated_doc and updated_doc["state"] == APP_STATE["ACTIVE"]:
        DIAGNOSIS.run_new_app(app_id, updated_doc)

    result = jsonify(data=updated_doc)
    result.status_code = 200
    return result


@app.route("/apps/<string:app_id>/slo", methods=["GET"])
def get_app_slo(app_id):
    application = appstate.get_app_by_id(app_id)
    if application is None:
        return util.ensure_document_found(None)
    if "slo" not in application:
        return util.error_response(f"SLO is not found", 400)
    return util.ensure_document_found(application['slo'])


@app.route("/apps/<string:app_id>/slo", methods=["PUT"])
def update_app_slo(app_id):
    application = appstate.get_app_by_id(app_id)
    if application is None:
        return util.ensure_document_found(None)
    if "slo" not in application:
        return util.error_response(f"SLO is not added in application: {app_id}", 400)

    application['slo'] = request.get_json()
    return util.update_and_return_doc(app_id, application)


@app.route("/apps/<string:app_id>/slo", methods=["POST"])
def add_app_slo(app_id):
    application = appstate.get_app_by_id(app_id)
    if application is None:
        return util.ensure_document_found(None)
    if "slo" in application:
        return util.error_response(f"SLO already set", 400)

    slo = request.get_json()
    return util.update_and_return_doc(app_id, {"slo": slo})


# For test
# @app.route("/apps/<string:app_id>/slo", methods=["DELETE"])
# def delete_app_slo(app_id):
#     application = configdb[app_collection].find_one({"app_id": app_id})
#     if application is None:
#         return util.ensure_document_found(None)
#     if 'slo' not in application:
#         return util.error_response(f"SLO is not added in application: {app_id}", 400)
#
#     return util.update_and_return_doc(app_id, {"slo": ""}, unset=True)


@app.route("/apps/<string:app_id>/incidents", methods=["GET"])
def get_app_incidents(app_id):
    incidents = resultstate.get_last_app_incident(app_id)

    for doc in incidents:
        return util.ensure_document_found(doc)

    return util.ensure_document_found(None)


@app.route("/problems", methods=["POST"])
def add_problem():
    problem_json = request.get_json()
    if problem_json is None:
        return util.error_response(f"No body found in request", 400)
    if "problem_id" not in problem_json:
        return util.error_response(f"problem id is not found", 400)
    problem_id = problem_json["problem_id"]
    problem = resultstate.get_problem(problem_id)

    if problem is not None:
        return util.error_response(f"problem with id {problem_id} already exist", 400)
    try:
        resultstate.create_problem(problem_json)
    except InvalidOperation:
        return util.error_response(f"Could not create problem {problem_id}.", 400)

    return util.ensure_document_found({"problem_id": problem_id})


@app.route("/problems/<string:problem_id>", methods=["GET"])
def get_problems(problem_id):
    problem = resultstate.get_problem(problem_id)
    return util.ensure_document_found(problem)


@app.route("/problems", methods=["GET"])
def get_problems_interval():
    req = request.get_json()
    if req is None or ("start_time" not in req or "end_time" not in req):
        end_ts = round(time.time()) * 1000000000
        start_ts = end_ts - 5 * 60 * 1000000000
    else:
        start_ts = req["start_time"]
        end_ts = req["end_time"]

    if end_ts < start_ts:
        return util.error_response(f"end_time is before start_time", 400)

    problems = resultstate.get_problems_between_time(start_ts, end_ts)
    return util.ensure_document_found(problems)


@app.route("/apps/<string:app_id>/diagnosis", methods=["POST"])
def add_diagnosis(app_id):
    diagnosis_json = request.get_json()
    if diagnoses_json is None:
        return util.error_response(f"No body found in request", 400)
    if "incident_id" not in diagnosis_json:
        return util.error_response(f"incident id is not found", 400)

    incident_id = diagnosis_json["incident_id"]
    diagnosis = resultstate.get_incident_diagnosis(app_id, incident_id)

    if diagnosis is not None:
        return util.error_response(f"diagnosis of app ({app_id}) with incident ({incident_id}) already exist", 400)
    try:
        resultstate.create_diagnosis(diagnosis_json)
    except InvalidOperation:
        return util.error_response(
            f"Could not create diagnosis of app id ({app_id}) with incident ({incident_id}) already exist", 400)
    return util.ensure_document_found({"app_id": app_id, "incident_id": incident_id})


@app.route("/apps/<string:app_id>/diagnosis", methods=["GET"])
def get_app_diagnosis(app_id):
    request_json = request.get_json()

    query_type = check_diagnosis_input(request_json)
    if query_type == 0:
        # query by name
        diagnosis = resultstate.get_last_app_diagnosis(app_Id)
        if diagnosis.count() == 0:
            return util.ensure_document_found(None)
    elif query_type == 1:
        # query by name & incident_id
        diagnosis = resultstate.get_incident_diagnosis(app_id, request_json["incident_id"])
    elif query_type == 2:
        # query by name & interval
        start_ts = request_json["start_time"]
        end_ts = request_json["end_time"]
        if end_ts < start_ts:
            return util.error_response(f"end_time is before the start_time", 400)
        diagnosis = resultstate.get_diagnosis_between_time(app_id, start_ts, end_ts)
    return util.ensure_document_found(diagnosis)


# return 0: query by app_name
# return 1: query by app_name & incident_id
# return 2: query by app_name & time interval
def check_diagnosis_input(request_json):
    if "incident_id" in request_json:
        return 1
    if "start_time" in request_json and "end_time" in request_json:
        return 2
    return 0


@app.route("/apps/<string:app_id>/management_features", methods=["GET"])
def get_app_all_features(app_id):
    application = appstate.get_app_by_id(app_id)
    if application is None:
        return util.ensure_document_found(None)
    if "management_features" not in application:
        return util.error_response(f"management_features are not found", 400)
    return util.ensure_document_found(application['management_features'])


@app.route("/apps/<string:app_id>/management_features/<string:feature_name>", methods=["GET"])
def get_app_one_feature(app_id, feature_name):
    application = appstate.get_app_by_id(app_id)
    if application is None:
        return util.ensure_document_found(None)
    if feature_name != FEATURE_NAME["INTERFERENCE"] and feature_name != FEATURE_NAME["BOTTLENECK"] and feature_name != \
            FEATURE_NAME["EFFICIENCY"]:
        return util.error_response(f"{feature_name} is not valid feature name", 400)
    if "management_features" not in application:
        return util.error_response(f"management_features is not exist", 400)

    for idx, feature in enumerate(application['management_features']):
        if feature["name"] == feature_name:
            break
        else:
            idx = -1
    if idx == -1:
        return util.error_response(f'{feature_name} is not found', 400)
    else:
        return util.ensure_document_found(feature)


@app.route("/apps/<string:app_id>/management_features/<string:feature_name>", methods=["PUT"])
def update_app_features(app_id, feature_name):
    application = appstate.get_app_by_id(app_id)
    if application is None:
        return util.ensure_document_found(None)
    if feature_name != FEATURE_NAME["INTERFERENCE"] and feature_name != FEATURE_NAME["BOTTLENECK"] and feature_name != \
            FEATURE_NAME["EFFICIENCY"]:
        return util.error_response(f"{feature_name} is not valid feature name", 400)
    if "management_features" not in application:
        return util.error_response(f"management features do not exist in application {app_id}", 400)

    new_feature = request.get_json()
    if "name" not in new_feature:
        return util.error_response(f"name field is not exist in update feature", 400)
    new_feature_name = new_feature["name"]
    if new_feature_name != feature_name:
        return util.error_response(f"Input json does not have the correct feature name", 400)

    for idx, feature in enumerate(application['management_features']):
        if feature["name"] == feature_name:
            break
        else:
            idx = -1
    if idx == -1:
        application['management_features'].append(new_feature)
    else:
        application['management_features'][idx] = new_feature
    return util.update_and_return_doc(app_id, application)


@app.route("/apps/<string:app_id>/management_features", methods=["POST"])
def add_app_features(app_id):
    application = appstate.get_app_by_id(app_id)
    if application is None:
        return util.ensure_document_found(None)
    if "management_features" in application:
        return util.error_response(f"management features already exist in application {app_id}", 400)

    features = request.get_json()
    return util.update_and_return_doc(app_id, {"management_features": features})


@app.route("/risks", methods=["POST"])
def add_risks():
    req = request.get_json()
    if req is None:
        return util.error_response(f"risk data is no available", 400)
    if "id" not in req:
        return util.error_response(f"risk id is not found", 400)
    risks = resultdb[risks_collection].find_one(
        {"id": req["id"]},
        {"_id": 0}
    )
    risk_id = req["id"]
    if risks is not None:
        return util.error_response(f"risk with id {risk_id} already exist", 400)
    try:
        resultdb[risks_collection].insert_one(req)
        return util.ensure_document_found({"risk_id": risk_id})
    except InvalidOperation:
        return util.error_response(f"Could not create risk {risk_id}.", 400)


@app.route("/risks", methods=["GET"])
def get_risks():
    req = request.get_json()
    if req is None or ("start_time" not in req or "end_time" not in req):
        end_ts = round(time.time()) * 1000000000
        start_ts = end_ts - 5 * 60 * 1000000000
    else:
        start_ts = req["start_time"]
        end_ts = req["end_time"]

    if end_ts < start_ts:
        return util.error_response(f"end_time is before the start_time", 400)

    risks = resultdb[risks_collection]. \
        find({"$and": [{"timestamp": {"$gte": start_ts}},
                       {"timestamp": {"$lte": end_ts}}]},
             {"_id": 0}
             )
    return util.ensure_document_found(risks)


@app.route("/opportunities", methods=["POST"])
def add_opportunities():
    opportunity_json = request.get_json()
    if opportunity_json is None:
        return util.error_response(f"opportunities data is no available", 400)
    if "id" not in opportunity_json:
        return util.error_response(f"opportunity id is not found", 400)

    opportunities = resultdb[opportunities_collection].find_one(
        {"id": opportunity_json["id"]},
        {"_id": 0}
    )
    opportunity_id = opportunity_json["id"]

    if opportunities is not None:
        return util.error_response(f"opportunity with id {opportunity_id} already exist", 400)
    try:
        resultdb[opportunities_collection].insert_one(opportunity_json)
        return util.ensure_document_found({"opportunity_id": opportunity_id})
    except InvalidOperation:
        return util.error_response(f"Could not create opportunity {opportunity_id}.", 400)
    return util.ensure_document_found(None)


@app.route("/opportunities", methods=["GET"])
def get_opportunities():
    req = request.get_json()
    if req is None or ("start_time" not in req or "end_time" not in req):
        end_ts = round(time.time()) * 1000000000
        start_ts = end_ts - 5 * 60 * 1000000000
    else:
        start_ts = req["start_time"]
        end_ts = req["end_time"]

    if end_ts < start_ts:
        return util.error_response(f"end_time is before the start_time", 400)
    opportunities = resultdb[opportunities_collection]. \
        find({"$and": [{"timestamp": {"$gte": start_ts}},
                       {"timestamp": {"$lte": end_ts}}]},
             {"_id": 0}
             )
    return util.ensure_document_found(opportunities)
