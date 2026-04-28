from django.core.management.base import BaseCommand

from samples.reporting import generate_vl_report


class Command(BaseCommand):
	help = "Generate VL reports into media/vl_reports"

	def handle(self, *args, **options):
		generate_vl_report('media/vl_reports')

