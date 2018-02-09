from flask import Flask
from werkzeug.wsgi import DispatcherMiddleware
from api_service.app import app as api_service_app
from api_service.ui import app as api_service_ui


app = DispatcherMiddleware(Flask(__name__), {
    "/api/v1": api_service_app,
    "/ui": api_service_ui
})
