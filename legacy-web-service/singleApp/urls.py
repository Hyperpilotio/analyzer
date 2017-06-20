from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^calibration/(?P<appId>[-\w]+)$',
        views.calibration, name='calibration'),
    url(r'^profiling/(?P<appId>[-\w]+)$',
        views.profiling, name='profiling')
]
