from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'samples'

urlpatterns  = [
	#url(r'^$', views.index, name='list_samples'),
	url(r'^create/$', login_required(views.create), name='create'),
	url(r'^get_facility/(?P<form_number>[\w-]+)/$', login_required(views.get_facility), name='get_facility'),
	url(r'^list/$', login_required(views.list), name='list'),
	url(r'^list_json$', login_required(views.ListJson.as_view()), name='list_json'),
	url(r'^show/(?P<sample_id>[0-9]+)$', login_required(views.show), name='show'),
	url(r'^edit/(?P<sample_id>[0-9]+)$', login_required(views.edit), name='edit'),
	url(r'^verify_list/$', login_required(views.verify_list), name='verify_list'),
	url(r'^verify/(?P<envelope_id>[0-9]+)/$', login_required(views.verify), name='verify'),
	url(r'^verify_envelope/(?P<envelope_id>[0-9]+)/$', login_required(views.verify_envelope), name='verify_envelope'),
	url(r'^save_verify/$', login_required(views.save_verify), name='save_verify'),
	url(r'^verify_list_json$', login_required(views.VerifyListJson.as_view()), name='verify_list_json'),
	url(r'^get_district_hub/(?P<facility_id>[0-9]+)/$', login_required(views.get_district_hub), name='get_district_hub')
]