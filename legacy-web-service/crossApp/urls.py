from django.conf.urls import url
from . import views

urlpatterns = [
    # predict Cross-App Interference Score matrix of two applications
    url(r'^predict/$', views.predict, name='predict')
]
