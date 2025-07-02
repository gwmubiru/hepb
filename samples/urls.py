from django.urls import re_path
from django.contrib.auth.decorators import login_required

#from . import views, data_table_views
from . import views, data_table_views
from django.views.decorators.csrf import csrf_exempt

app_name = 'samples'

urlpatterns  = [
	re_path(r'^create/$', login_required(views.create), name='create'),
	re_path(r'^get_rejection_reasons/$', login_required(views.get_rejection_reasons), name='get_rejection_reasons'),
	re_path(r'^receive/$', login_required(views.receive), name='receive'),
	re_path(r'^merge_envelopes/$', login_required(views.merge_envelopes), name='merge_envelopes'),
	re_path(r'^reject_sample/$', login_required(views.reject_sample), name='reject_sample'),
	re_path(r'^receive_batch/$', login_required(views.receive_batch), name='receive_batch'),
	re_path(r'^receive_hie/$', login_required(views.receive_hie), name='receive_hie'),
	re_path(r'^receive_sample_only/$', login_required(views.receive_sample_only), name='receive_sample_only'),
	re_path(r'^create_range/$', login_required(views.create_range), name='create_range'),
	re_path(r'^receive_api/$', csrf_exempt(views.receive_api), name='receive_api'),
	re_path(r'^does_form_number_exist/(?P<form_number>[\w-]+)/$', login_required(views.does_form_number_exist), name='does_form_number_exist'),
	re_path(r'^list/$', login_required(views.list), name='list'),
	re_path(r'^pending_verification_list/$', login_required(views.pending_verification_list), name='pending_verification_list'),
	re_path(r'^update_patient_parent/$', login_required(views.update_patient_parent), name='update_patient_parent'),
	re_path(r'^list_json$', login_required(data_table_views.ListJson.as_view()), name='list_json'),
	re_path(r'^show/(?P<sample_id>[0-9]+)$', login_required(views.show), name='show'),
	re_path(r'^edit/(?P<sample_id>[0-9]+)$', login_required(views.edit), name='edit'),
	re_path(r'^edit_received/(?P<reception_id>[0-9]+)$', login_required(views.edit_received), name='edit_received'),

	re_path(r'^verify_list/$', login_required(views.verify_list), name='verify_list'),
	re_path(r'^receive_package/$', login_required(views.receive_package), name='receive_package'),
	re_path(r'^verify/(?P<sample_id>[0-9]+)/$', login_required(views.verify), name='verify'),
	re_path(r'^remove/(?P<sample_id>[0-9]+)/$', login_required(views.remove), name='remove'),
	re_path(r'^switch_samples/$', login_required(views.switch_samples), name='switch_samples'),
	re_path(r'^detach_sample/$', login_required(views.detach_sample), name='detach_sample'),
	re_path(r'^verify_envelope/(?P<envelope_id>[0-9]+)/$', login_required(views.verify_envelope), name='verify_envelope'),
	re_path(r'^save_verify/$', login_required(views.save_verify), name='save_verify'),
	re_path(r'^verify_list_json$', login_required(data_table_views.VerifyListJson.as_view()), name='verify_list_json'),

	re_path(r'^get_district_hub/(?P<facility_id>[0-9]+)/$', login_required(views.get_district_hub), name='get_district_hub'),
	re_path(r'^patient_history/(?P<facility_id>[0-9]+)/$', login_required(views.pat_hist), name='pat_hist'),
	re_path(r'^release_rejects/$', login_required(views.release_rejects), name='release_rejects'),
	re_path(r'^intervene_list/$', login_required(views.intervene_list), name='intervene_list'),

	re_path(r'^vl_list/$', login_required(data_table_views.vl_list), name="vl_list"),
	re_path(r'^vl_list/data/$', login_required(data_table_views.vl_list_data), name="vl_list_data"),

	re_path(r'^search/$', login_required(views.search), name='search'),

	re_path(r'^envelope_list/$', login_required(views.envelope_list), name="envelope_list"),
	re_path(r'^envelope_list_json/$', login_required(data_table_views.envelope_list_json), name='envelope_list_json'),
	re_path(r'^reverse_approval/(?P<verification_id>[0-9]+)/$', login_required(views.reverse_approval), name="reverse_approval"),
	re_path(r'^download/(?P<path>.*)$',login_required(views.download), name="download"),
	re_path(r'^reports/$',login_required(views.reports), name='reports'),
	re_path(r'^facility_art_numbers/(?P<facility_id>[0-9]+)/$', login_required(views.facility_art_numbers), name='facility_art_numbers'),
	re_path(r'^get_patient/$', login_required(views.get_patient), name='get_patient'),
	re_path(r'^get_barcode_details/$', login_required(views.get_barcode_details), name='get_barcode_details'),
	re_path(r'^get_envelope_details/$', login_required(views.get_envelope_details), name='get_envelope_details'),
	re_path(r'^get_envelope_status_for_lab/$', login_required(views.get_envelope_status_for_lab), name='get_envelope_status_for_lab'),
	re_path(r'^get_tracking_code_details/$', login_required(views.get_tracking_code_details), name='get_tracking_code_details'),
	re_path(r'^fix_verifications/$', login_required(views.fix_verifications), name='fix_verifications'),
	re_path(r'^range_list/$', login_required(views.range_list), name='range_list'),
	re_path(r'^release_sample_only_results/$', login_required(views.release_sample_only_results), name='release_sample_only_results'),
	re_path(r'^range_envelopes/$', login_required(views.range_envelopes), name='range_envelopes'),
	re_path(r'^range_json/$', login_required(views.RangeJson.as_view()), name='range_json'),

]
