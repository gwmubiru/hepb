from django.contrib import admin

from .models import *

class FacilityAdmin(admin.ModelAdmin):
	list_display = ('facility','district','hub','dhis2_name', 'dhis2_uid',)
	search_fields = ('facility', 'district__district',)

class AppendixAdmin(admin.ModelAdmin):
	search_fields = ('appendix',)

class DistrictAdmin(admin.ModelAdmin):
	search_fields = ('district',)

class HubAdmin(admin.ModelAdmin):
	search_fields = ('hub',)

class UserProfileAdmin(admin.ModelAdmin):
	list_display = ('user','phone','medical_lab',)
	search_fields = ('user__username', 'user__email',)
# Register your models here.
admin.site.register(AppendixCategory)
admin.site.register(Appendix, AppendixAdmin)
admin.site.register(Region)
admin.site.register(Ip)
admin.site.register(District, DistrictAdmin)
admin.site.register(Hub, HubAdmin)
admin.site.register(HubRider)
admin.site.register(Facility, FacilityAdmin)
admin.site.register(IpFacilitySupport)
admin.site.register(MedicalLab)
admin.site.register(UserProfile, UserProfileAdmin)