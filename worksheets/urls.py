from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'worksheets'
urlpatterns  = [
	url(r'^create/(?P<machine_type>[A|R|C])$', login_required(views.create), name='create'),
	url(r'^attach_samples/(?P<worksheet_id>[0-9]+)/$', login_required(views.attach_samples), name='attach_samples'),
	url(r'^show/(?P<worksheet_id>[0-9]+)/$', login_required(views.show), name='show'),
	url(r'^edit/(?P<worksheet_id>[0-9]+)/$', login_required(views.edit), name='edit'),
	url(r'^vlprint/(?P<worksheet_id>[0-9]+)/$', login_required(views.vlprint), name='vlprint'),
	url(r'^list/$', login_required(views.list), name='list'),
	url(r'^pdf/(?P<worksheet_id>[0-9]+)/$', login_required(views.generate_pdf), name='pdf'),
	url(r'^list_json/$', login_required(views.ListJson.as_view()), name='list_json'),
	url(r'^authorize_list/(?P<machine_type>[A|R|C])/$', login_required(views.authorize_list), name='authorize_list'),
	url(r'^authorize_results/(?P<worksheet_id>[0-9]+)/$', login_required(views.authorize_results), name='authorize_results'),
	url(r'^pending_samples/$', login_required(views.pending_samples), name='get_pending_samples'),
	url(r'^pending_envelopes/$', login_required(views.pending_envelopes), name='pending_envelopes'),
	url(r'^delete/(?P<pk>[0-9]+)/$', login_required(views.delete), name='delete'),
	url(r'^reg_info/(?P<machine_type>[A|R|C])/$', login_required(views.reg_info), name='reg_info'),
	url(r'^get_instrument_id/$', login_required(views.get_instrument_id), name='get_instrument_id'),
	url(r'^barcodes/(?P<pk>[0-9]+)/$', login_required(views.barcodes), name='barcodes'),
	#url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
]