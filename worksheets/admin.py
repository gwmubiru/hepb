from django.contrib import admin
from backend.admin import VLAdmin

from .models import *

# Register your models here.
class WorksheetAdmin(VLAdmin, admin.ModelAdmin):
	list_display = ('worksheet_reference_number',)
	search_fields = ('worksheet_reference_number',)


admin.site.register(Worksheet, WorksheetAdmin)