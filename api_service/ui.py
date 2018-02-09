from flask import Flask, jsonify, request, got_request_exception, render_template
from flask_table import Table, Col
from api_service.analyzer import Analyzer
import api_service.util as util

app = Flask(__name__, template_folder="templates")

app.json_encoder = util.JSONEncoderWithMongo
app.url_map.converters["objectid"] = util.ObjectIdConverter

class JobsTable(Table):
    job_name = Col('Name')
    job_module = Col('Module')
    job_function = Col('Function')
    schedule_at = Col('Schedule At')
    created_at = Col('Created At')
    running_at = Col('Running At')
    finished_at = Col('Finished At')
    status = Col('Status')
    last_error = Col('Error')

@app.route("/jobs", methods=["GET"])
def get_jobs():
    job_states = Analyzer().jobs.get_job_states()
    jobs_table = JobsTable(job_states)
    return render_template("jobs.html", jobs_table=jobs_table)
