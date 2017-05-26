from django.conf.urls import url
from prediction import views

urlpatterns = [
    url(r'^testid2feature/$', views.testid2feature, name='testid2feature')
]
