from django.contrib import admin

from .models import *

# Register your models here.
admin.site.register(AppendixCategory)
admin.site.register(Appendix)
admin.site.register(Region)
admin.site.register(Ip)
admin.site.register(District)
admin.site.register(Hub)
admin.site.register(HubRider)
admin.site.register(Facility)