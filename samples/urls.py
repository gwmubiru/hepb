from django.conf.urls import url

from . import views

app_name = 'samples'

urlpatterns  = [
	#url(r'^$', views.index, name='list_samples'),
	url(r'^create/$', views.create, name='create'),
	url(r'^save/$', views.save, name='save'),
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