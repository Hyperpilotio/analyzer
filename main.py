from flask import Flask, url_for
from werkzeug.wsgi import DispatcherMiddleware
from api_service.app import app as api_service_app

frontend_app = Flask(__name__)

index_html = """
<html>
<head>
</head>
<body>
  <div id="react-root"></div>
  <script src="%s"></script>
</body>
</html>
"""

@frontend_app.route("/")
def index():
    return index_html % url_for("static", filename="bundle.js")

app = DispatcherMiddleware(frontend_app, {
    "/api": api_service_app,
})

if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple("0.0.0.0", 5000, app)
