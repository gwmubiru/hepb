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


admin.site.register(Sample,SampleAdmin)
admin.site.register(Envelope,EnvelopeAdmin)
