from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'results'
urlpatterns  = [
	url(r'^upload/(?P<worksheet_id>[0-9]+)/$', login_required(views.upload), name='upload'),
	url(r'^release_list/(?P<machine_type>[A|R|C])/$', login_required(views.release_list), name='release_list'),
	url(r'^release_results/(?P<worksheet_id>[0-9]+)/$', login_required(views.release_results), name='release_results'),
	url(r'^cobas_upload/$', login_required(views.cobas_upload), name='cobas_upload'),
	url(r'^list/$', login_required(views.list), name='list'),
	url(r'^worksheet/(?P<worksheet_id>[0-9]+)/$', login_required(views.worksheet_results), name='worksheet'),
	url(r'^api', login_required(views.api), name='api'),
	url(r'^anomalies/(?P<worksheet_id>[0-9]+)/$', login_required(views.get_anomalies), name='anomalies')
	#url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
]