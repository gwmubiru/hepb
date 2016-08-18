from django.conf.urls import url

from . import views

app_name = 'worksheets'
urlpatterns  = [
	url(r'^create/$', views.create, name='create'),
	url(r'^attach_samples/(?P<worksheet_id>[0-9]+)/$', views.attach_samples, name='attach_samples'),
	url(r'^list/$', views.list, name='list'),
]