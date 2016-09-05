from django.conf.urls import url

from . import views

app_name = 'worksheets'
urlpatterns  = [
	url(r'^create/$', views.create, name='create'),
	url(r'^attach_samples/(?P<worksheet_id>[0-9]+)/$', views.attach_samples, name='attach_samples'),
	url(r'^show/(?P<worksheet_id>[0-9]+)/$', views.show, name='show'),
	url(r'^vlprint/(?P<worksheet_id>[0-9]+)/$', views.vlprint, name='vlprint'),
	url(r'^list/$', views.list, name='list'),
	url(r'^pdf/(?P<worksheet_id>[0-9]+)/$', views.generate_pdf, name='pdf'),
	#url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
]