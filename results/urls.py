from django.urls import re_path
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'results'
urlpatterns  = [
	re_path(r'^upload/$', login_required(views.upload), name='upload'),
	re_path(r'^release_list/(?P<machine_type>[A|R|C|H])/$', login_required(views.release_list), name='release_list'),
	re_path(r'^release_results/$', login_required(views.release_results), name='release_results'),
	re_path(r'^cobas_upload/$', login_required(views.cobas_upload), name='cobas_upload'),
	re_path(r'^alinity_upload/$', login_required(views.alinity_upload), name='alinity_upload'),
	re_path(r'^override_results/$', login_required(views.override_results), name='override_results'),
	re_path(r'^list/$', login_required(views.list), name='list'),
	re_path(r'^worksheet/(?P<worksheet_id>[0-9]+)/$', login_required(views.worksheet_results), name='worksheet'),
	re_path(r'^api', login_required(views.api), name='api'),
	re_path(r'^anomalies/(?P<machine_type>[0-9]+)/$', login_required(views.get_anomalies), name='anomalies'),
	re_path(r'^intervene_list/$', login_required(views.intervene_list), name='intervene_list'),
	re_path(r'^dr_results/$', login_required(views.dr_results), name='dr_results'),
	re_path(r'^force_create_result/$', login_required(views.force_create_result), name='force_create_result'),
	re_path(r'^reschedule/(?P<result_pk>[0-9]+)/$', login_required(views.reschedule), name='reschedule'),
	re_path(r'^approve_for_dr/(?P<result_pk>[0-9]+)/$', login_required(views.approve_for_dr), name='approve_for_dr'),
	re_path(r'^authorize_sample/$', login_required(views.authorize_sample), name='authorize_sample'),
	re_path(r'^trouble_shoot_results/$', login_required(views.trouble_shoot_results), name='trouble_shoot_results'),
	re_path(r'^release_sample/$', login_required(views.release_sample), name='release_sample'),
	re_path(r'^samples_pending_results/$', login_required(views.samples_pending_results), name='samples_pending_results'),
	re_path(r'^list/$', login_required(views.list), name='list'),
	re_path(r'^list_json/$', login_required(views.ListJson.as_view()), name='list_json'),
]
