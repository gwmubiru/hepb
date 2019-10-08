from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views, data_table_views

app_name = 'samples'

urlpatterns  = [
	#url(r'^$', views.index, name='list_samples'),
	url(r'^create/$', login_required(views.create), name='create'),
	url(r'^get_facility/(?P<form_number>[\w-]+)/$', login_required(views.get_facility), name='get_facility'),
	url(r'^list/$', login_required(views.list), name='list'),
	url(r'^list_json$', login_required(data_table_views.ListJson.as_view()), name='list_json'),
	url(r'^show/(?P<sample_id>[0-9]+)$', login_required(views.show), name='show'),
	url(r'^edit/(?P<sample_id>[0-9]+)$', login_required(views.edit), name='edit'),
	url(r'^verify_list/$', login_required(views.verify_list), name='verify_list'),
	url(r'^verify/(?P<sample_id>[0-9]+)/$', login_required(views.verify), name='verify'),
	url(r'^verify_envelope/(?P<envelope_id>[0-9]+)/$', login_required(views.verify_envelope), name='verify_envelope'),
	url(r'^save_verify/$', login_required(views.save_verify), name='save_verify'),
	url(r'^verify_list_json$', login_required(data_table_views.VerifyListJson.as_view()), name='verify_list_json'),
	url(r'^get_district_hub/(?P<facility_id>[0-9]+)/$', login_required(views.get_district_hub), name='get_district_hub'),
	url(r'^patient_history/(?P<facility_id>[0-9]+)/$', login_required(views.pat_hist), name='pat_hist'),
	url(r'^clinicians/(?P<facility_id>[0-9]+)/$', login_required(views.clinicians), name='clinicians'),
	url(r'^lab_techs/(?P<facility_id>[0-9]+)/$', login_required(views.lab_techs), name='lab_techs'),
	url(r'^release_rejects/$', login_required(views.release_rejects), name='release_rejects'),
	url(r'^released_rejects/$', login_required(views.released_rejects), name='released_rejects'),
	url(r'^intervene_list/$', login_required(views.intervene_list), name='intervene_list'),

	url(r'^vl_list/$', login_required(data_table_views.vl_list), name="vl_list"),
	url(r'^vl_list/data/$', login_required(data_table_views.vl_list_data), name="vl_list_data"),

	url(r'^search/$', login_required(views.search), name='search'),

	url(r'^envelope_list/$', login_required(views.envelope_list), name="envelope_list"),
	url(r'^envelope_list_json/$', login_required(data_table_views.envelope_list_json), name='envelope_list_json'),
	url(r'^generate_forms/$', login_required(views.generate_forms), name="generate_forms"),
	url(r'^forms/$', login_required(views.forms), name="forms"),
	url(r'^edit_dispatch/(?P<dispatch_id>[0-9]+)/$', login_required(views.edit_dispatch), name="edit_dispatch"),
	url(r'^reverse_approval/(?P<verification_id>[0-9]+)/$', login_required(views.reverse_approval), name="reverse_approval"),
	url(r'^download/(?P<path>.*)$',login_required(views.download), name="download"),
	url(r'^reports/$',login_required(views.reports), name="reports"),
	url(r'^print_rejects/(?P<sample_id>[0-9]+)/$', login_required(views.print_rejects), name='print_rejects'),
]