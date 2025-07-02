import datetime as dt
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Sample
from worksheets.models import Worksheet,WorksheetSample
from results.models import Result,ResultsQC

class Command(BaseCommand):
	help = "insert results manually"


	def handle(self, *args, **options):
		self.__release_results()

	def __release_results(self):
		worksheet_samples = WorksheetSample.objects.raw('select * from vl_worksheet_samples where id in()')
		
		for ws in worksheet_samples:
			restult = Result.objects.filter(sample_id=ws.sample_id).first()
			if restult is None:
				result= Result()
				result.repeat_test = 2
				result.result1 = ws.result_alphanumeric
				result.result_numeric = ws.result_numeric
				result.result_alphanumeric = ws.result_alphanumeric
				result.method = ws.method
				result.test_date = ws.test_date
				result.authorised_at = ws.authorised_at
				result.authorised_by_id = ws.authoriser_id
				result.sample_id = ws.sample_id
				result.test_by_id = ws.tester_id
				result.suppressed = ws.suppressed
				result.authorised = ws.authorised
				result.worksheet_sample_id = ws.id
				result.supression_cut_off_id = ws.supression_cut_off_id
				result.save()

				print(ws.sample_id)

				result_qc = ResultsQC()
				result_qc.released = 1
				result_qc.released_at = '2025-02-22 09:50:29.510871'
				result_qc.qc_date = result.test_date
				result_qc.comments = 'manual'
				result_qc.released_by_id = 6463903
				result_qc.result_id = result.id
				result_qc.save()
				
		print('kiwedde')


