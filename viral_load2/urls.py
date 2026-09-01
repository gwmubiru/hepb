from django.urls import include,re_path
from django.urls import re_path as url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from home import views as home_views, session

urlpatterns = [
	re_path(r'^$', home_views.home, name='home_page'),
	re_path(r'^login/', home_views.login_page, name='login_page'),
	re_path(r'^login_attempt/', home_views.login_attempt, name='login_attempt'),
	re_path(r'^select_program/', home_views.select_program, name='select_program'),
	re_path(r'^set_program/', home_views.set_program, name='set_program'),
	re_path(r'^logout/', home_views.logout, name='logout'),
	re_path(r'^quick_stats/', home_views.quick_stats, name='quick_stats'),
	re_path(r'^data_entry_stats/', home_views.data_entry_stats, name='data_entry_stats'),	
	re_path(r'^sample_approval_stats/', home_views.sample_approval_stats, name='sample_approval_stats'),	
	re_path(r'^password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
	re_path(r'^admin/', admin.site.urls),
	re_path(r'^samples/', include('samples.urls')),
	re_path(r'^worksheets/', include('worksheets.urls')),
	re_path(r'^results/', include('results.urls')),
	re_path(r'^clean_data/', home_views.clean_data, name='clean_data'),
	re_path(r'^facility_data/', home_views.facility_data, name='facility_data'),
	re_path(r'^clean_data_list/', home_views.clean_data_list, name='clean_data_list'),
	re_path(r'^api/', include('api.urls')),
	re_path(r'^oauth/', include('sso.urls')),
]
