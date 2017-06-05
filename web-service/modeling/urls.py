from django.conf.urls import url
from . import views

urlpatterns = [
    # predict Cross-App Interference Score matrix of two applications
    url(r'^predict_app2app/$', views.predict_app2app, name='predict_app2app')
]
