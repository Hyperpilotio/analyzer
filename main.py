from flask import Flask, url_for, request, abort, render_template_string
from werkzeug.wsgi import DispatcherMiddleware
from api_service.app import app as api_service_app
import json

main_app = Flask(__name__, static_folder="frontend/dist")

index_html = """
<html>
<head>
  <title>HyperPilot Analyzer</title>
  {% if "css" in webpack_stats %}
  <link rel="stylesheet" href="{{
    url_for("static", filename=webpack_stats["css"])
  }}" />
  {% endif %}
</head>
<body>
  <div id="react-root"></div>
  <script src="{{
    url_for("static", filename=webpack_stats["main"])
  }}"></script>
</body>
</html>
"""

@main_app.before_request
def before_request_hook():
    if request.path == "/dist/stats.json":
        abort(404)

@main_app.route("/", defaults={"path": ""})
@main_app.route("/<path:path>")
def index(path):
    with open("frontend/dist/stats.json") as f:
        webpack_stats = json.load(f)
    return render_template_string(index_html, webpack_stats=webpack_stats)

application = DispatcherMiddleware(main_app, {
    "/api": api_service_app,
})

if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple("0.0.0.0", 5000, application)
