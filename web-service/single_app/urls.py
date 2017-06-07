from django.conf.urls import url
from . import views

urlpatterns = [
	url(r'^show/(?P<app_name>[-\w]+)/$', views.show, name='show')
]
