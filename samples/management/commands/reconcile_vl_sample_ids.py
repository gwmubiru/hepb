import datetime as dt
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Sample

class Command(BaseCommand):
	help = "Reconcile VL sample IDs to begin from 1 for month"

	def add_arguments(self, parser):
		parser.add_argument('period', nargs='+')

	def handle(self, *args, **options):
		self.create_year = options['period'][0]
		self.creat_month = options['period'][1]
		self.__save_samples()

	def __save_samples(self):
		samples = Sample.objects.filter(created_at__year=2017, created_at__month=12)
		smpl_id = 1
		for s in samples:
			s.vl_sample_id = "%s/%s%s" %(str(smpl_id).zfill(6), utils.year('yy'), utils.month('mm'))
			s.save()
			smpl_id += 1
			print "updated %s"%s.pk


