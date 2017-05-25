from django.conf.urls import url
from visualization import views

urlpatterns = [
    url(r'^visualize/$', views.visualize, name='visualize')
]
