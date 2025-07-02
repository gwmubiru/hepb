from django.urls import re_path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'worksheets'
urlpatterns  = [
	
	re_path(r'^create/(?P<sample_type>[P|D])$', login_required(views.create), name='create'),
	re_path(r'^update/(?P<sample_type>[P|D])$', login_required(views.update), name='update'),
	re_path(r'^update_status/(?P<worksheet_id>[0-9]+)/$', login_required(views.update_status), name='update_status'),
	re_path(r'^attach_samples/(?P<stage>[0-9]+)/(?P<sample_type>[P|D])/$', login_required(views.attach_samples), name='attach_samples'),
	re_path(r'^show/(?P<worksheet_id>[0-9]+)/$', login_required(views.show), name='show'),
	re_path(r'^edit/(?P<worksheet_id>[0-9]+)/$', login_required(views.edit), name='edit'),
	re_path(r'^vlprint/(?P<worksheet_id>[0-9]+)/$', login_required(views.vlprint), name='vlprint'),
	re_path(r'^list_page/$', login_required(views.list_page), name='list_page'),
	re_path(r'^pdf/(?P<worksheet_id>[0-9]+)/$', login_required(views.generate_pdf), name='pdf'),
	re_path(r'^list_json/$', login_required(views.ListJson.as_view()), name='list_json'),
	re_path(r'^authorize_list/(?P<machine_type>[A|R|C|H])/$', login_required(views.authorize_list), name='authorize_list'),
	re_path(r'^authorize_results/$', login_required(views.authorize_results), name='authorize_results'),
	re_path(r'^authorize_runs/$', login_required(views.authorize_runs), name='authorize_runs'),
	re_path(r'^pending_samples/$', login_required(views.pending_samples), name='get_pending_samples'),
	re_path(r'^pending_envelopes/$', login_required(views.pending_envelopes), name='pending_envelopes'),
	re_path(r'^delete/(?P<pk>[0-9]+)/$', login_required(views.delete), name='delete'),
	re_path(r'^reg_info/(?P<machine_type>[A|R|C|H])/$', login_required(views.reg_info), name='reg_info'),
	re_path(r'^get_instrument_id/$', login_required(views.get_instrument_id), name='get_instrument_id'),
	re_path(r'^attach_results/$', login_required(views.attach_results), name='attach_results'),
	re_path(r'^choose_machine_type/$', login_required(views.choose_machine_type), name='choose_machine_type'),	
	re_path(r'^manage_repeats/$', login_required(views.manage_repeats), name='manage_repeats'),
	re_path(r'^manage_plasma_repeats/$', login_required(views.manage_plasma_repeats), name='manage_plasma_repeats'),
	re_path(r'^dilute_sample/$', login_required(views.dilute_sample), name='dilute_sample'),
	re_path(r'^does_worksheet_sample_number_exist/(?P<ws>[\w-]+)/$', login_required(views.does_worksheet_sample_number_exist), name='does_worksheet_sample_number_exist'),
	re_path(r'^lab_samples/$', login_required(views.lab_samples), name='lab_samples'),
	re_path(r'^lab_samples_json/$', login_required(views.LabSamplesJson.as_view()), name='lab_samples_json'),
	re_path(r'^get_pending_samples/$', login_required(views.get_pending_samples), name='get_pending_samples'),
	re_path(r'^lab_env_list/$', login_required(views.lab_env_list), name='lab_env_list'),
	re_path(r'^lab_env_list_json/$', login_required(views.lab_env_list_json), name='lab_env_list_json'),
	re_path(r'^create_worksheet_list_json/$', login_required(views.create_worksheet_list_json), name='create_worksheet_list_json'),
	
]
