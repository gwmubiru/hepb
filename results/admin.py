from django.contrib import admin
from backend.admin import VLAdmin

from .models import *

# Register your models here.
class ResultAdmin(VLAdmin, admin.ModelAdmin):
	list_display = ('sample',)
	search_fields = ('sample__form_number',)

class ResultQCAdmin(VLAdmin, admin.ModelAdmin):
	list_display = ('result',)
	search_fields = ('result__sample__form_number',)

admin.site.register(Result, ResultAdmin)
admin.site.register(ResultsQC,ResultQCAdmin)
