from django.conf.urls import url
from prediction import views

urlpatterns = [
    # predict Cross-App Interference Score matrix of two applications
    url(r'^app2app/$', views.app2app, name='app2app')
]
