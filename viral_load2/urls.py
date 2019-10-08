"""viral_load2 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
	https://docs.djangoproject.com/en/dev/topics/http/urls/
Examples:
Function views
	1. Add an import:  from my_app import views
	2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
	1. Add an import:  from other_app.views import Home
	2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
	1. Add an import:  from blog import urls as blog_urls
	2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include,url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from home import views as home_views, session

urlpatterns = [
	url(r'^$', home_views.home, name='home_page'),
	url(r'^login/', home_views.login_page, name='login_page'),
	url(r'^login_attempt/', home_views.login_attempt, name='login_attempt'),
	url(r'^logout/', home_views.logout, name='logout'),
	url(r'^quick_stats/', home_views.quick_stats, name='quick_stats'),
	url(r'^change-password/$', auth_views.password_change, {'post_change_redirect': 'home_page'}, name='password_change'),
	url(r'^admin/', admin.site.urls),
	url(r'^samples/', include('samples.urls')),
	url(r'^worksheets/', include('worksheets.urls')),
	url(r'^results/', include('results.urls')),
	url(r'^api/', include('api.urls')),
]
