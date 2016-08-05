from __future__ import unicode_literals
import datetime

from django.db import models
from django.utils import timezone

# Create your models here.

#Appendix Categories are to help categorize appendices 
class AppendixCategory(models.Model):
	category = models.CharField(max_length=64, unique=True)

	class Meta:
		db_table = 'backend_appendix_categories'
		verbose_name_plural = 'Appendix Categories'

	def __str__(self): #return category as default
		return self.category


#Appendices are to hold basic back end data to be used on forms
class Appendix(models.Model):
	appendix_category = models.ForeignKey(AppendixCategory, on_delete=models.CASCADE)
	code = models.CharField(max_length=32)
	appendix = models.CharField(max_length=64)
	tag = models.CharField(max_length=64, null=True)

	def __str__(self): #return appendix as default
		return self.appendix

	class Meta:
		db_table = 'backend_appendices'
		verbose_name_plural = 'Appendices'


#Hold data about regions
class Region(models.Model):
	region = models.CharField(max_length=32, unique=True)

	def __str__(self): #return region as default
		return self.region

	class Meta:
		db_table = 'backend_regions'


#Hold data about Implementing Partners (ips)
class Ip(models.Model):
	ip = models.CharField(max_length=32, unique=True)
	full_name = models.CharField(max_length=128)
	address = models.CharField(max_length=64)
	ip_email = models.EmailField(max_length=128)
	website = models.URLField(max_length=128)
	focal_person_name = models.CharField(max_length=64)
	focal_person_contact = models.CharField(max_length=64)
	focal_person_email = models.EmailField(max_length=128)
	funding_source = models.CharField(max_length=64)
	active = models.BooleanField(default=True)

	def __str__(self): #return ip as default
		return self.ip

	class Meta:
		db_table = 'backend_ips'


#Hold data about districts
class District(models.Model):
	region = models.ForeignKey(Region, on_delete=models.CASCADE)
	district = models.CharField(max_length=32, unique=True)
	map_code = models.CharField(max_length=64)

	def __str__(self): #return district as default
		return self.district

	class Meta:
		db_table = 'backend_districts'


#Hold data about hubs
class Hub(models.Model):	
	ip = models.ForeignKey(Ip)
	hub = models.CharField(max_length=32, unique=True)
	hub_email = models.EmailField(max_length=128)
	coordinator_name = models.CharField(max_length=64)
	coordinator_contact = models.CharField(max_length=64)
	coordinator_email = models.EmailField(max_length=128)
	active = models.BooleanField(default=True)

	def __str__(self): #return hub as default
		return self.hub

	class Meta:
		db_table = 'backend_hubs'


#Hold data about Hub Riders (border borders) that transport samples/ results between hubs and facilities
class HubRider(models.Model):
	hub = models.ForeignKey(Hub, on_delete=models.CASCADE)
	rider = models.CharField(max_length=64)
	contact = models.CharField(max_length=64)
	address = models.CharField(max_length=128)
	email = models.EmailField(max_length=128)
	number_plate = models.CharField(max_length=8)
	active = models.BooleanField(default=True)

	def __str__(self): #return rider as default
		return self.rider

	class Meta:
		db_table = 'backend_hub_riders'
		verbose_name_plural = 'Hub Riders'		


#Hold data about facilities (hospitals, and lower level health centers including HC IV, HC III and HC II)
class Facility(models.Model):
	district = models.ForeignKey(District, on_delete=models.CASCADE)
	hub = models.ForeignKey(Hub, on_delete=models.CASCADE)
	ips = models.ManyToManyField(Ip, through='IpFacilitySupport')
	facility = models.CharField(max_length=128)
	hub_facility = models.BooleanField(default=False)#this field asks whether the facility is a hub
	facility_contact = models.CharField(max_length=64)
	facility_email = models.EmailField(max_length=128)
	physical_address = models.CharField(max_length=128)
	return_address = models.CharField(max_length=128)
	coordinator_name = models.CharField(max_length=64)
	coordinator_contact = models.CharField(max_length=64)
	coordinator_email = models.EmailField(max_length=128)
	active = models.BooleanField(default=True)

	def __str__(self): #return facility as default
		return self.facility

	class Meta:
		db_table = 'backend_facilities'
		verbose_name_plural = 'Facilities'

		
#Many to Many r/ship between facility and ips
class IpFacilitySupport(models.Model):
	ip = models.ForeignKey(Ip)
	facility = models.ForeignKey(Facility)
	start_date = models.DateField()
	stopped = models.BooleanField(default=False)
	stop_date = models.DateField()

	class Meta:
		db_table = 'backend_ip_facility_support'
		verbose_name_plural = 'IP Facility Support'