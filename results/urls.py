from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from easy_pdf.views import PDFTemplateView
from .views import HelloPDFView
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
	url(r'^anomalies/(?P<worksheet_id>[0-9]+)/$', login_required(views.get_anomalies), name='anomalies'),
	url(r'^intervene_list/$', login_required(views.intervene_list), name='intervene_list'),
	url(r'^reschedule/(?P<result_pk>[0-9]+)/$', login_required(views.reschedule), name='reschedule'),
	url(r'^authorize_sample/$', login_required(views.authorize_sample), name='authorize_sample'),
	url(r'^release_sample/$', login_required(views.release_sample), name='release_sample'),
	url(r'^print_results/(?P<result_id>[0-9]+)/(?P<worksheet_id>[0-9]+)/$', login_required(views.print_results), name='print_results'),
	#url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
	url(r'^hello.pdf$', HelloPDFView.as_view()),
]