from django.contrib import admin
from backend.admin import VLAdmin

from .models import *

# Register your models here.
class SampleAdmin(VLAdmin, admin.ModelAdmin):
	list_display = ('form_number',)
	search_fields = ('form_number',)

class EnvelopeAdmin(VLAdmin, admin.ModelAdmin):
	list_display = ('envelope_number','stage',)
	search_fields = ('envelope_number','stage',)

class SampleWithIssueAdmin(VLAdmin, admin.ModelAdmin):
	list_display = ('reception_date', 'sample_type', 'test_type', 'barcode', 'facility_name', 'form_number', 'infant_name', 'retrieval_status', 'retrieval_date')
	search_fields = ('barcode', 'facility_name', 'form_number', 'infant_name', 'art_number', 'pack_number')
	list_filter = ('sample_type', 'test_type', 'retrieval_status')


admin.site.register(Sample,SampleAdmin)
admin.site.register(Envelope,EnvelopeAdmin)
admin.site.register(SampleWithIssue,SampleWithIssueAdmin)
