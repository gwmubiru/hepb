from django.conf.urls import url

from . import views

app_name = 'samples'

urlpatterns  = [
	#url(r'^$', views.index, name='list_samples'),
	url(r'^create/$', views.create, name='create'),
	url(r'^get_facility/(?P<form_number>[\w-]+)/$', views.get_facility, name='get_facility'),
	url(r'^list/$', views.list, name='list'),
	url(r'^list_json$', views.ListJson.as_view(), name='list_json'),
	url(r'^show/(?P<sample_id>[0-9]+)$', views.show, name='show'),
	url(r'^edit/(?P<sample_id>[0-9]+)$', views.edit, name='edit'),
	url(r'^verify_list/$', views.verify_list, name='verify_list'),
	url(r'^verify/(?P<envelope_id>[0-9]+)/$', views.verify, name='verify'),
	url(r'^verify_envelope/(?P<envelope_id>[0-9]+)/$', views.verify_envelope, name='verify_envelope'),
	url(r'^save_verify/$', views.save_verify, name='save_verify'),

	#ex: /polls/5/
    #url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
    #ex: /polls/5/results/
    #url(r'^(?P<pk>[0-9]+)/results/$', views.ResultsView.as_view(), name='results'),
    #ex: /polls/5/vote/
    #url(r'^(?P<question_id>[0-9]+)/vote/$', views.vote, name='vote'),
]