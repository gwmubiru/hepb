from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'api'
urlpatterns  = [
	url(r'^results/$', views.results, name='results'),
	url(r'^facilities/$', views.facilities, name='facilities'),
	url(r'^samples/$', views.samples, name='samples'),
]