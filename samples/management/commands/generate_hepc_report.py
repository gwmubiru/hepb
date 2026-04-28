from django.core.management.base import BaseCommand

from samples.reporting import generate_program_report


class Command(BaseCommand):
	help = "Generate HepC reports into media/hepc_reports"

	def handle(self, *args, **options):
		generate_program_report(2, 'media/hepc_reports')

