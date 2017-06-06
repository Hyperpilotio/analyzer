from django.conf.urls import url
from . import views

urlpatterns = [
	url(r'^show/$', views.show, name='show')
]
