from django.conf.urls import url
from prediction import views

urlpatterns = [
    url(r'^predict/$', views.predict, name='predict')
]
