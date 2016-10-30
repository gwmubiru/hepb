from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'results'
urlpatterns  = [
	url(r'^upload/(?P<worksheet_id>[0-9]+)/$', login_required(views.upload), name='upload'),
	url(r'^list/$', login_required(views.list), name='list'),
	url(r'^worksheet/(?P<worksheet_id>[0-9]+)/$', login_required(views.worksheet_results), name='worksheet'),
	#url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
]