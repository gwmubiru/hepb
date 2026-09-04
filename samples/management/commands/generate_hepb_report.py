from django.core.management.base import BaseCommand

from samples.reporting import generate_program_report


class Command(BaseCommand):
	help = "Generate HepB reports into media/hepb_reports"

	def handle(self, *args, **options):
		generate_program_report(1, 'media/hepb_reports')

