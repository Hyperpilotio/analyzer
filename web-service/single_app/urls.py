from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^calibration/(?P<app_id>[-\w]+)$',
        views.calibration, name='calibration'),
    url(r'^profiling/(?P<app_id>[-\w]+)$',
        views.profiling, name='profiling'),
    url(r'^services_json/(?P<app_name>[-\w]+)$',
        views.services_json, name='services_json'),
    url(r'^calibration_json/(?P<app_id>[-\w]+)$',
        views.calibration_json, name='calibration_json'),
    url(r'^profiling_json/(?P<app_id>[-\w]+)$',
        views.profiling_json, name='profiling_json')
]
