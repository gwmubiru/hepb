from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from backend.models import *
from django.db import IntegrityError


class Command(BaseCommand):
	help = "Transfer facility stuff from old database to the new database"

	# def add_arguments(self, parser):
	# 	pass

	def handle(self, *args, **options):
		self.__save_regions()
		self.__save_ips()
		self.__save_districts()
		self.__save_hubs()		
		self.__save_facilities()

	def __get_regions(self):
		sql = """SELECT * FROM `vl_regions`"""
		cursor = connections['old_db'].cursor()
		cursor.execute(sql)
		self.old_regions = utils.dictfetchall(cursor)

	def __save_regions(self):
		self.__get_regions()
		for old_region in self.old_regions:
			defaults = {'region':old_region.get('region')}
			r, r_created = Region.objects.update_or_create(pk=old_region.get('id'), defaults=defaults)
			print "region saved %s" %r.region

	def __get_ips(self):
		sql = """SELECT * FROM `vl_ips`"""
		cursor = connections['old_db'].cursor()
		cursor.execute(sql)
		self.old_ips = utils.dictfetchall(cursor)

	def __save_ips(self):
		self.__get_ips()
		for old_ip in self.old_ips:
			defaults = {'ip':old_ip.get('ip'), 'full_name':old_ip.get('ip')}
			i, i_created = Ip.objects.update_or_create(pk=old_ip.get('id'), defaults=defaults)
			print "region saved %s" %i.ip

	def __get_districts(self):
		sql = """SELECT * FROM `vl_districts`"""
		cursor = connections['old_db'].cursor()
		cursor.execute(sql)
		self.old_districts = utils.dictfetchall(cursor)

	def __save_districts(self):
		self.__get_districts()
		for old_district in self.old_districts:
			region_id = old_district.get('regionID') if Region.objects.filter(pk=old_district.get('regionID')).exists() else None
			defaults = {
				'region_id': region_id,
				'district': old_district.get('district'),
				'map_code': old_district.get('mapCode'),
				'dhis2_uid': old_district.get('dhis2_uid'),
			}
			d, d_created = District.objects.update_or_create(pk=old_district.get('id'), defaults=defaults)
			print "district saved %s" %d.district


	def __get_hubs(self):
		sql = """SELECT * FROM `vl_hubs`"""
		cursor = connections['old_db'].cursor()
		cursor.execute(sql)
		self.old_hubs = utils.dictfetchall(cursor)

	def __save_hubs(self):
		self.__get_hubs()
		for old_hub in self.old_hubs:
			ip_id = old_hub.get('ipID') if Ip.objects.filter(pk=old_hub.get('ipID')).exists() else None
			defaults = {
				'hub': old_hub.get('hub'),
				'hub_email': old_hub.get('email'),
				'ip_id': ip_id,
			}
			h, h_created = Hub.objects.update_or_create(pk=old_hub.get('id'), defaults=defaults)
			print "hub saved %s" %h.hub
			# except:
			# 	print "hub saving failed %s" %old_hub.get('hub')



	def __get_facilities(self):
		sql = """SELECT * FROM `vl_facilities`"""
		cursor = connections['old_db'].cursor()
		cursor.execute(sql)
		self.old_facilities = utils.dictfetchall(cursor)

	def __save_facilities(self):
		self.__get_facilities()
		for old_facility in self.old_facilities:
			district_id = old_facility.get('districtID') if District.objects.filter(pk=old_facility.get('districtID')).exists() else None
			hub_id = old_facility.get('hubID') if Hub.objects.filter(pk=old_facility.get('hubID')).exists() else None
			defaults = {
				'facility':old_facility.get('facility'),
				'district_id': district_id,
				'hub_id': hub_id,	
				'dhis2_name': old_facility.get('dhis2_name'),
				'dhis2_uid': old_facility.get('dhis2_uid'),
				'facility_contact': old_facility.get('phone'),
				'facility_email': old_facility.get('email'),
				'physical_address': old_facility.get('physicalAddress'),
				'return_address': old_facility.get('returnAddress'),
			}
			f, f_created = Facility.objects.update_or_create(pk=old_facility.get('id'), defaults=defaults)
			print "facility saved %s" %f.facility