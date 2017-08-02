from flask import Flask
from werkzeug.wsgi import DispatcherMiddleware
from api_service.app import app as api_service_app


app = DispatcherMiddleware(Flask(__name__), {
    "/api": api_service_app,
})
