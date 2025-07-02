from django.urls import include
from django.contrib.auth.decorators import login_required
from django.urls import re_path
from . import views

app_name = 'api'
urlpatterns  = [
	re_path(r'^results/$', views.results, name='results'),
	re_path(r'^facilities/$', views.facilities, name='facilities'),
	re_path(r'^samples/$', views.samples, name='samples'),
	re_path(r'^update_dispatch_details/$', views.update_dispatch_details, name='update_dispatch_details'),
]
