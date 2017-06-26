from flask import Flask, url_for
from werkzeug.wsgi import DispatcherMiddleware
from api_service.app import app as api_service_app

main_app = Flask(__name__, static_folder="frontend/dist")

index_html = """
<html>
<head>
  <title>HyperPilot Analyzer</title>
</head>
<body>
  <div id="react-root"></div>
  <script src="%s"></script>
</body>
</html>
"""

@main_app.route("/", defaults={"path": ""})
@main_app.route("/<path:path>")
def index(path):
    return index_html % url_for("static", filename="bundle.js")

application = DispatcherMiddleware(main_app, {
    "/api": api_service_app,
})

if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple("0.0.0.0", 5000, application)
