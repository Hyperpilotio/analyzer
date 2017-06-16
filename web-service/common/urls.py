from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^echo/$', views.echo, name='echo'),
    url(r'^connectToDB/$', views.connectToDB, name='connectToDB')
]
