from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Patient, Sample, PatientPhone, Envelope, Verification
from backend.models import Appendix
from results.models import Result, ResultsQC, ResultsDispatch
from results import utils as r_utils
from worksheets.models import Worksheet, WorksheetSample
from django.utils import timezone

class Command(BaseCommand):
	help = "create results manually where stage=5 but result does not exist"

	
	def handle(self, *args, **options):
		cursor = connections['default'].cursor()
		#get generated matched and unmatched records of facility
		results = cursor.execute("select ws.id, ws.sample_id, ws.repeat_test, ws.authorised, ws.suppressed,ws.method,ws.tester_id,ws.result_numeric, ws.result_alphanumeric,ws.test_date,ws.authorised_at,ws.authoriser_id FROM  vl_worksheet_samples ws left join vl_results r  on ws.id = r.worksheet_sample_id where r.id is null and r.worksheet_sample_id is null and ws.stage=5")
		
		for row in cursor.fetchall():
			if row is not None:
				
				result = Result()
				result.worksheet_sample_id = row[0]
				result.sample_id = row[1]
				result.repeat_test = row[2]
				result.authorised = row[3]
				result.suppressed = row[4]
				result.method =  row[5]
				result.test_by_id = row[6]
				result.result_numeric =row[7]
				result.result1 = row[8]
				result.result_alphanumeric = row[8]
				result.test_date = row[9]
				result.authorised_at = row[10]
				result.authorised_by_id = row[11]
				  	
				result.save()
				other_params = {
					'released': True,
					'comments': 'manual',
					'released_by_id': 6463900,
					'released_at': timezone.now(),
				}

				rqc, rqc_created = ResultsQC.objects.update_or_create(result=result, defaults=other_params)
		print('done')

	
	def creeate_results(self):
		cursor = connections['default'].cursor()
		#get generated matched and unmatched records of facility
		results = cursor.execute("select ws.id, ws.sample_id, ws.repeat_test, ws.authorised, ws.suppressed,ws.method,ws.tester_id,ws.result_numeric, ws.result_alphanumeric,ws.test_date,ws.authorised_at,ws.authoriser_id FROM  vl_worksheet_samples ws left join vl_results r  on ws.id = r.worksheet_sample_id where r.id is null and r.worksheet_sample_id is null and ws.stage=5")
		
		for row in cursor.fetchall():
			if row is not None:
				
				result = Result()
				result.worksheet_sample_id = row[0]
				result.sample_id = row[1]
				result.repeat_test = row[2]
				result.authorised = row[3]
				result.suppressed = row[4]
				result.method =  row[5]
				result.test_by_id = row[6]
				result.result_numeric =row[7]
				result.result1 = row[8]
				result.result_alphanumeric = row[8]
				result.test_date = row[9]
				result.authorised_at = row[10]
				result.authorised_by_id = row[11]
				  	
				result.save()
				other_params = {
					'released': True,
					'comments': 'manual',
					'released_by_id': 6463900,
					'released_at': timezone.now(),
				}

				rqc, rqc_created = ResultsQC.objects.update_or_create(result=result, defaults=other_params)
		print('done')
		

	
				
