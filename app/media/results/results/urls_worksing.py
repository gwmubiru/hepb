from django.urls import include,path
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'results'
urlpatterns  = [
	path(r'^upload/$', login_required(views.upload), name='upload'),
	path(r'^release_list/(?P<machine_type>[A|R|C|H])/$', login_required(views.release_list), name='release_list'),
	path(r'^release_results/$', login_required(views.release_results), name='release_results'),
	path(r'^cobas_upload/$', login_required(views.cobas_upload), name='cobas_upload'),
	path(r'^alinity_upload/$', login_required(views.alinity_upload), name='alinity_upload'),
	path(r'^list/$', login_required(views.list), name='list'),
	path(r'^worksheet/(?P<worksheet_id>[0-9]+)/$', login_required(views.worksheet_results), name='worksheet'),
	path(r'^api', login_required(views.api), name='api'),
	path(r'^anomalies/(?P<machine_type>[0-9]+)/$', login_required(views.get_anomalies), name='anomalies'),
	path(r'^intervene_list/$', login_required(views.intervene_list), name='intervene_list'),
	path(r'^dr_results/$', login_required(views.dr_results), name='dr_results'),
	path(r'^reschedule/(?P<result_pk>[0-9]+)/$', login_required(views.reschedule), name='reschedule'),
	path(r'^approve_for_dr/(?P<result_pk>[0-9]+)/$', login_required(views.approve_for_dr), name='approve_for_dr'),
	path(r'^authorize_sample/$', login_required(views.authorize_sample), name='authorize_sample'),
	path(r'^release_sample/$', login_required(views.release_sample), name='release_sample'),
	path(r'^samples_pending_results/$', login_required(views.samples_pending_results), name='samples_pending_results'),
	#url(r'^fix_abbot_uploads/$', login_required(views.fix_abbot_uploads), name='fix_abbot_uploads'),

	#url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
	#url(r'^update_run_with_contamination_info/(?P<res_id>[0-9]+)/$', login_required(views.update_run_with_contamination_info), name='update_run_with_contamination_info'),
]
