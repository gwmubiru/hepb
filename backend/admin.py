from django.contrib import admin
from django.core.serializers import serialize

from .models import *
from samples.models import Sample, LabTech, Clinician, ClinicalRequestFormsDispatch


class ReadOnlyAdmin(object):
	"""Disables all editing capabilities."""

	def __init__(self, *args, **kwargs):
		super(ReadOnlyAdmin, self).__init__(*args, **kwargs)
		#self.readonly_fields = self.model._meta.get_all_field_names()
		self.readonly_fields = map(lambda f: f.attname, self.model._meta.get_fields())

	def has_add_permission(self, request):
		return False

	def has_delete_permission(self, request, obj=None):
		return False

	def save_model(self, request, obj, form, change):
		return False


class VLAdmin(object):
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
	actions = ('merge',)
	list_display = ('facility','district','hub','dhis2_name', 'dhis2_uid',)
	search_fields = ('facility', 'district__district',)

	def merge(self, request, queryset):
		facility0 = queryset[0]
		facility1 = queryset[1]

		samples = Sample.objects.filter(facility=facility1)
		for sample in samples:
			sample.facility = facility0
			sample.save()

		facility_ips = IpFacilitySupport.objects.filter(facility=facility1)
		for facility_ip in facility_ips:
			facility_ip.facility = facility0
			facility_ip.save()

		dispatched_forms = ClinicalRequestFormsDispatch.objects.filter(facility=facility1)
		for dispatched_form in dispatched_forms:
			dispatched_form.facility = facility0
			dispatched_form.save()

		lab_techs = LabTech.objects.filter(facility=facility1)
		for lab_tech in lab_techs:
			lab_tech.lname = self.new_lname(facility0, "%s."%lab_tech.lname)  
			lab_tech.facility = facility0
			lab_tech.save()

		clinicians = Clinician.objects.filter(facility=facility1)
		for clinician in clinicians:
			clinician.cname = self.new_cname(facility0,"%s."%clinician.cname)
			clinician.facility = facility0
			clinician.save()

		facility_stats = FacilityStats.objects.filter(facility=facility1)
		facility_stats.delete()
		
		delete_log = DeleteLog()
		delete_log.ref_number = facility1.pk
		delete_log.section = "facilities"
		delete_log.delete_reason = " %s (%s) merged to %s (%s)"%(facility1.pk, facility1.facility, facility0.pk, facility0.facility)
		delete_log.data = "%s"%serialize('json', [facility1]) 
		delete_log.deleted_by = request.user
		delete_log.save()	

		facility1.delete()

		self.message_user(request, "All merged to %s." %facility0)

	def new_cname(self, facility, cname):
		while(True):
			exists = Clinician.objects.filter(facility=facility, cname=cname).exists()
			if exists:
				cname = "%s "%cname
			else:
				return cname

	def new_lname(self, facility, lname):
		while(True):
			exists = LabTech.objects.filter(facility=facility, lname=lname).exists()
			if exists:
				lname = "%s "%lname
			else:
				return lname


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