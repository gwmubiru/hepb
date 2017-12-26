from django.contrib import admin

from .models import *

class ReadOnlyAdmin(object):
	"""Disables all editing capabilities."""

	def __init__(self, *args, **kwargs):
		super(ReadOnlyAdmin, self).__init__(*args, **kwargs)
		self.readonly_fields = self.model._meta.get_all_field_names()

	def has_add_permission(self, request):
		return False

	def has_delete_permission(self, request, obj=None):
		return False

	def save_model(self, request, obj, form, change):
		return False


class VLAdmin(object):
	#actions = ('merge',)
	
	def has_delete_permission(self, request, obj=None):
		return False

	# def merge(self, request, queryset):
	# 	main = queryset[0]
	# 	tail = queryset[1:]

	# 	related = main._meta.get_all_related_objects()
	# 	valnames = dict()

	# 	for r in related:
	# 		valnames.update({r.get_accessor_name():r.field.name})

	# 	for t in tail:
	# 		for access_name, field_name in valnames.iteritems():
	# 			update_candidates = getattr(t, access_name).all()
	# 			for candidate in update_candidates:
	# 				setattr(candidate, field_name, main)
	# 				candidate.save()
	# 		t.delete()

	# 	self.message_user(request, "All merged to %s." %main)

class FacilityAdmin(VLAdmin, admin.ModelAdmin):
	list_display = ('facility','district','hub','dhis2_name', 'dhis2_uid',)
	search_fields = ('facility', 'district__district',)

class AppendixCategoryAdmin(VLAdmin, admin.ModelAdmin):
	pass

class AppendixAdmin(VLAdmin, admin.ModelAdmin):
	search_fields = ('appendix',)

class DistrictAdmin(VLAdmin, admin.ModelAdmin):
	search_fields = ('district',)

class HubAdmin(VLAdmin, admin.ModelAdmin):
	search_fields = ('hub',)

class UserProfileAdmin(VLAdmin, admin.ModelAdmin):
	list_display = ('user','phone','medical_lab',)
	search_fields = ('user__username', 'user__email',)

class DeleteLogAdmin(VLAdmin, ReadOnlyAdmin, admin.ModelAdmin):
	fields = ('section', 'ref_number', 'delete_reason', 'deleted_by', 'deleted_at', 'data',)
	list_display = ('section', 'ref_number', 'delete_reason', 'deleted_by', 'deleted_at', )
	search_fields = ('ref_number',)
	show_fields = ('ref_number',)

# Register your models here.
admin.site.register(AppendixCategory, AppendixCategoryAdmin)
admin.site.register(Appendix, AppendixAdmin)
admin.site.register(Region)
admin.site.register(Ip)
admin.site.register(District, DistrictAdmin)
admin.site.register(Hub, HubAdmin)
admin.site.register(HubRider)
admin.site.register(Facility, FacilityAdmin)
admin.site.register(IpFacilitySupport)
admin.site.register(MedicalLab)
admin.site.register(DeleteLog, DeleteLogAdmin)
admin.site.register(UserProfile, UserProfileAdmin)


admin.site.disable_action('delete_selected')
#admin.site.disable_action('delete_link')