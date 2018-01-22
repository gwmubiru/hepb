from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Patient, Sample, PatientPhone, Envelope, Verification
from backend.models import Appendix
from results.models import Result, ResultsQC, ResultsDispatch
from results import utils as r_utils
from worksheets.models import Worksheet, WorksheetSample

class Command(BaseCommand):
	help = "Transfer results data from old database to the new database"

	def add_arguments(self, parser):
		parser.add_argument('period', nargs='+')

	def handle(self, *args, **options):
		self.create_year = options['period'][0]
		self.create_month = options['period'][1]
		self.old_results = []
		for x in xrange(0,5):
			self.__save_results()

	def __get_results(self):
		
		sql = """SELECT s.id AS sid, rr.*, fp.*, fp.id AS fpid, rr.created AS auth_at, rr.createdby AS auth_by, w.machineType, w.createdby AS test_by
			    FROM vl_samples AS s
			    LEFT JOIN vl_results_released AS rr ON s.id=rr.sample_id
			    LEFT JOIN vl_facility_printing AS fp ON s.id=fp.sample_id
			    LEFT JOIN vl_samples_worksheetcredentials AS w ON rr.worksheet_id=w.id
			    WHERE YEAR(s.created)=%s AND MONTH(s.created)=%s AND s.migrated = 'YES' AND result_migrated=0
			    GROUP BY s.id LIMIT 20000"""

		cursor = connections['old_db'].cursor()
		cursor.execute(sql, [self.create_year, self.create_month])
		self.old_results = utils.dictfetchall(cursor)

	def __save_results(self):
		self.__get_results()
		for r in self.old_results:
			try:
				self.__save_result(r)
				connections['old_db'].cursor().execute("UPDATE vl_samples SET result_migrated=1 WHERE id=%s"%r.get('sid'))
				print "saved %s" %r.get('sid')
			except:
				print "Failed %s" %r.get('sid')



	def __save_result(self, r):
		rr_result = r.get('result')
		if rr_result:
			res = Result()
			res.sample_id = r.get('sid')
			machineType = r.get('machineType')	
			res.method = 'R' if machineType == 'roche' else 'A'	
			res.result1 = rr_result

			if rr_result == 'Failed':
				res.result_numeric = 0
				res.result_alphanumeric = 'Failed'
				res.suppressed = 3
			elif rr_result == 'Not detected' or rr_result == 'Target Not Detected':
				res.result_numeric = 0
				res.result_alphanumeric = rr_result
				res.suppressed = 1
			elif rr_result.startswith('<') or rr_result.startswith('>'):
				res.result_numeric = r_utils.get_numeric_result(rr_result)
				res.suppressed = 1 if res.result_numeric<1000 else 2
				res.result_alphanumeric = "%s {:,d} Copies / mL".format(res.result_numeric) %rr_result[0]
			else:
				res.result_numeric = r_utils.get_numeric_result(rr_result)
				if res.result_numeric > 10000000:
					res.suppressed = 2
					res.result_alphanumeric = "> 10,000,000 Copies / mL"
				else:
					res.result_alphanumeric = "{:,d} Copies / mL".format(res.result_numeric)
					res.suppressed = 1 if res.result_numeric<1000 else 2

			res.test_date = r.get('test_date')
			res.test_by = utils.get_or_create_user(r.get('test_by'))
			res.authorised = True
			res.authorised_by_id = 1
			res.authorised_at = r.get('auth_at')
			res.save()

			fpid = r.get('fpid')
			if fpid:
				res_qc = ResultsQC()
				res_qc.result = res
				ready = r.get('ready')
				res_qc.comments = r.get('comments')
				res_qc.released = True if ready else False
				res_qc.released_by_id = 1
				res_qc.released_at = r.get('qc_at')
				res_qc.save()

				printed = r.get('printed')
				downloaded = r.get('downloaded')
				if printed == 'YES' or downloaded == 'YES':
					res_dispatch = ResultsDispatch()
					res_dispatch.sample_id = res.sample_id
					res_dispatch.dispatch_type = 'D' if downloaded == 'YES' else 'P'
					res_dispatch.dispatch_date = r.get('printed_at')
					res_dispatch.dispatched_by = r.get('printed_by')
					res_dispatch.save()