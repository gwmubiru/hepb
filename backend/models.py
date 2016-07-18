from __future__ import unicode_literals
import datetime

from django.db import models

# Create your models here.

#Appendix Categories are to help categorize appendices 
class AppendixCategory(models.Model):
	category = models.CharField(max_length=64, unique=true)


#Appendices are to hold basic back end data to be used on forms
class Appendix(models.Model):
	appendix_category = models.ForeignKey(AppendixCategory, on_delete=models.CASCADE)
	code = models.CharField(max_length=32)
	appendix = models.CharField(max_length=64)

	def __str__(self): #return appendix as default
        return self.appendix


#Hold data about regions
class Region(models.Model):
	region = models.CharField(max_length=32, unique=true)

	def __str__(self): #return region as default
        return self.region


#Hold data about Implementing Partners (ips)
class Ip(models.Model):
	ip = models.CharField(max_length=32, unique=true)
	full_name = models.CharField(max_length=128)
	address = models.CharField(max_length=64)
	ip_email = models.EmailField(max_length=128)
	website = models.URLField(max_length=128)
	focal_person_name = models.CharField(max_length=64)
	focal_person_contact = models.CharField(max_length=64)
	focal_person_email = models.EmailField(max_length=128)
	funding_source = models.CharField(max_length=64)
	active = models.BooleanField(default=true)

	def __str__(self): #return ip as default
        return self.ip


#Hold data about districts
class District(models.Model):
	region = models.ForeignKey(Region, on_delete=models.CASCADE)
	district = models.CharField(max_length=32, unique=true)
	map_code = models.CharField(max_length=64)

	def __str__(self): #return district as default
        return self.district


#Hold data about hubs
class Hub(models.Model):	
	ip = models.ForeignKey(Ip, on_delete=models.CASCADE)
	resident_facility = models.ForeignKey(Facility)
	hub = models.CharField(max_length=32, unique=true)
	hub_email = models.EmailField(max_length=128)
	coordinator_name = models.CharField(max_length=64)
	coordinator_contact = models.CharField(max_length=64)
	coordinator_email = models.EmailField(max_length=128)
	active = models.BooleanField(default=true)

	def __str__(self): #return hub as default
        return self.hub


#Hold data about Hub Riders (border borders) that transport samples/ results between hubs and facilities
class HubRider(models.Model):
	hub = models.ForeignKey(Hub, on_delete=models.CASCADE)
	rider = models.CharField(max_length=64)
	contact = models.CharField(max_length=64)
	address = models.CharField(max_length=128)
	email = models.EmailField(max_length=128)
	number_plate = models.CharField(max_length=8)
	active = models.BooleanField(default=true)

	def __str__(self): #return rider as default
        return self.rider


#Hold data about facilities (hospitals, and lower level health centers including HC IV, HC III and HC II)
class Facility(models.Model):
	district = models.ForeignKey(District, on_delete=models.CASCADE)
	hub = models.ForeignKey(Hub, on_delete=models.CASCADE)
	ips = models.ManyToManyField(Ip, through='IpFacilitySupport')
	facility = models.CharField(max_length=128)
	facility_contact = models.CharField(max_length=64)
	facility_email = models.EmailField(max_length=128)
	physical_address = models.CharField(max_length=128)
	return_address = models.CharField(max_length=128)
	coordinator_name = models.CharField(max_length=64)
	coordinator_contact = models.CharField(max_length=64)
	coordinator_email = models.EmailField(max_length=128)
	active = models.BooleanField(default=true)

	def __str__(self): #return facility as default
        return self.facility


#Many to Many r/ship between facility and ips
class IpFacilitySupport(models.Model):
	ip = models.ForeignKey(Ip)
	facility = models.ForeignKey(Ip)
	start_date = models.DateField(default=datetime.date.today())
	stopped = BooleanField(default=false)
	stop_date = models.DateField()