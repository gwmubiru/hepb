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
		parser.add_argument('ops', nargs='+')

	def handle(self, *args, **options):
		self.create_year = options['ops'][0]
		self.create_month = options['ops'][1]
		self.machine_type = options['ops'][2]
		self.single = options['ops'][3]

		if int(self.create_year)==2017 and int(self.create_month)>3:
			print "Enter period before 2017 March"
			return False
		self.old_results = []
		if self.single==1:
			for x in xrange(0,5):
				self.__save_results()
		else:
			for x in xrange(0,3):
				self.__save_results2()

	def __get_roche_results(self):
		sql = """SELECT s.id AS sid, res_r.Result AS result, fctr.factor, res_r.created AS test_date, res_r.createdby As test_by,
						res_o.result AS override_result, res_o.created AS ocreated,
			    	   	prt.created AS date_printed, prt.createdby AS printed_by  
			    FROM vl_samples AS s 
			    INNER JOIN vl_results_roche AS res_r ON s.vlSampleID=res_r.sampleID
			    LEFT JOIN vl_results_multiplicationfactor AS fctr ON res_r.worksheetID=fctr.worksheetID
			    LEFT JOIN vl_results_override AS res_o ON s.vlSampleID=res_o.sampleID
			    LEFT JOIN vl_logs_printedresults AS prt ON s.id=prt.sampleID
			    WHERE YEAR(s.created)=%s AND MONTH(s.created)=%s AND s.migrated = 'YES' AND in_worksheet = 1 AND result_migrated=0
			    AND res_r.single=1
			    GROUP BY s.id LIMIT 20000"""
		cursor = connections['old_db'].cursor()
		cursor.execute(sql, [self.create_year, self.create_month])
		self.old_results = utils.dictfetchall(cursor)

	def __get_abbott_results(self):
		sql = """SELECT s.id AS sid, res_a.result AS result, fctr.factor, res_a.created AS test_date, res_a.createdby As test_by,
						res_o.result AS override_result, res_o.created AS ocreated,
			    	   	prt.created AS date_printed, prt.createdby AS printed_by  
			    FROM vl_samples AS s 
			    INNER JOIN vl_results_abbott AS res_a ON s.vlSampleID=res_a.sampleID
			    LEFT JOIN vl_results_multiplicationfactor AS fctr ON res_a.worksheetID=fctr.worksheetID
			    LEFT JOIN vl_results_override AS res_o ON s.vlSampleID=res_o.sampleID
			    LEFT JOIN vl_logs_printedresults AS prt ON s.id=prt.sampleID
			    WHERE YEAR(s.created)=%s AND MONTH(s.created)=%s AND s.migrated = 'YES' AND in_worksheet = 1 AND result_migrated=0
			    AND res_a.single=1
			    GROUP BY s.id LIMIT 20000"""
		cursor = connections['old_db'].cursor()
		cursor.execute(sql, [self.create_year, self.create_month])
		self.old_results = utils.dictfetchall(cursor)

	def __get_roche_results2(self):

		sql = """SELECT s.id AS sid,
			    	   GROUP_CONCAT(DISTINCT res_r.Result, '||', fctr_r.factor, '||', res_r.created, '||', res_r.createdby SEPARATOR '::') AS concat_result,
			    	   res_o.result AS override_result, res_o.created AS ocreated,
			    	   prt.created AS date_printed, prt.createdby AS printed_by
			    FROM vl_samples AS s
			    INNER JOIN vl_results_roche AS res_r ON s.vlSampleID=res_r.sampleID
			    LEFT JOIN vl_results_override AS res_o ON s.vlSampleID=res_o.sampleID
			    LEFT JOIN vl_logs_printedresults AS prt ON s.id=prt.sampleID
			    LEFT JOIN vl_results_multiplicationfactor AS fctr_r ON res_r.worksheetID=fctr_r.worksheetID
			    WHERE YEAR(s.created)=%s AND MONTH(s.created)=%s AND s.migrated = 'YES' AND in_worksheet = 1 AND result_migrated=0
			    AND res_r.single=0   GROUP BY s.id LIMIT 20000"""

		cursor = connections['old_db'].cursor()
		cursor.execute(sql, [self.create_year, self.create_month])
		self.old_results = utils.dictfetchall(cursor)

	def __get_abbott_results2(self):

		sql = """SELECT s.id AS sid,
			    	   GROUP_CONCAT(DISTINCT res_a.result, '||', fctr_a.factor, '||', res_a.created, '||', res_a.createdby SEPARATOR '::') AS concat_result,
			    	   res_o.result AS override_result, res_o.created AS ocreated,
			    	   prt.created AS date_printed, prt.createdby AS printed_by
			    FROM vl_samples AS s
			    INNER JOIN vl_results_abbott AS res_a ON s.vlSampleID=res_a.sampleID
			    LEFT JOIN vl_results_override AS res_o ON s.vlSampleID=res_o.sampleID
			    LEFT JOIN vl_logs_printedresults AS prt ON s.id=prt.sampleID
			    LEFT JOIN vl_results_multiplicationfactor AS fctr_a ON res_a.worksheetID=fctr_a.worksheetID
			    WHERE YEAR(s.created)=%s AND MONTH(s.created)=%s AND s.migrated = 'YES' AND in_worksheet = 1 AND result_migrated=0
			    AND res_a.single=0 GROUP BY s.id LIMIT 20000"""

		cursor = connections['old_db'].cursor()
		cursor.execute(sql, [self.create_year, self.create_month])
		self.old_results = utils.dictfetchall(cursor)

	def __save_results(self):
		if self.machine_type == 'roche':
			self.__get_roche_results()
		else:
			self.__get_abbott_results()

		for r in self.old_results:
			try:
				self.__save_result(r)
				connections['old_db'].cursor().execute("UPDATE vl_samples SET result_migrated=1 WHERE id=%s"%r.get('sid'))
				print "saved %s" %r.get('sid')
			except:
				print "Failed %s" %r.get('sid')

	def __save_results2(self):
		if self.machine_type == 'roche':
			self.__get_roche_results2()
		else:
			self.__get_abbott_results2()

		#print self.old_results

		for r in self.old_results:
			try:
				concat_result = r.get('concat_result','')
				s_results = concat_result.split('::')
				latest_result_params = s_results[-1]
				latest_result = latest_result_params.split("||")
				r.update({
					'result':latest_result[0], 
					'factor':latest_result[1],
					'test_date':latest_result[2],
					'test_by':latest_result[3],
					})
				self.__save_result(r)
				connections['old_db'].cursor().execute("UPDATE vl_samples SET result_migrated=1 WHERE id=%s"%r.get('sid'))
				print "saved %s" %r.get('sid')
			except:
				print "Failed %s" %r.get('sid')

	def __save_result(self, r):
		res = Result()
		res.sample_id = r.get('sid')
		res.method = "R" if self.machine_type == 'roche' else "A"

		if r.get('override_result'):
			res.result_numeric = 0
			res.result_alphanumeric = 'Failed'
			res.suppressed = 3
		else:
			res_dict = r_utils.get_result2(r.get('result'),int(r.get('factor')),res.method)
			res.result_numeric = res_dict.get('numeric_result',0)
			res.result_alphanumeric = res_dict.get('alphanumeric_result','')
			res.suppressed = res_dict.get('suppressed',3)

		res.result1 = res.result_alphanumeric
		res.test_date = r.get('test_date')
		res.test_by = utils.get_or_create_user(r.get('test_by'))
		res.authorised = True
		res.authorised_by_id = 1
		res.authorised_at = res.test_date
		res.save()

		res_qc = ResultsQC()
		res_qc.result = res
		res_qc.released = True
		res_qc.released_by_id = 1
		res_qc.released_at = res.test_date
		res_qc.save()

		if r.get('date_printed'):
			res_dispatch = ResultsDispatch()
			res_dispatch.sample_id = res.sample_id
			res_dispatch.dispatch_type = 'D'
			res_dispatch.dispatch_date = r.get('date_printed')
			res_dispatch.dispatched_by = utils.get_or_create_user(r.get('printed_by'))
			res_dispatch.save()


	# def __get_results(self):

	# 	sql = """SELECT s.id AS sid,
	# 		    	   GROUP_CONCAT(res_r.Result, '||', fctr_r.factor, '||', res_r.created, '||', res_r.createdby SEPARATOR '::') AS roche_result,
	# 		    	   GROUP_CONCAT(res_a.result, '||', fctr_a.factor, '||', res_a.created, '||', res_a.createdby SEPARATOR '::') AS abbott_result,
	# 		    	   res_o.result AS override_result, res_o.created AS ocreated,
	# 		    	   prt.created AS date_printed, prt.createdby AS printed_by
	# 		    FROM vl_samples AS s
	# 		    LEFT JOIN vl_results_abbott AS res_a ON s.vlSampleID=res_a.sampleID
	# 		    LEFT JOIN vl_results_roche AS res_r ON s.vlSampleID=res_r.sampleID
	# 		    LEFT JOIN vl_results_override AS res_o ON s.vlSampleID=res_o.sampleID
	# 		    LEFT JOIN vl_logs_printedresults AS prt ON s.id=prt.sampleID
	# 		    LEFT JOIN vl_results_multiplicationfactor AS fctr_a ON res_a.worksheetID=fctr_a.worksheetID
	# 		    LEFT JOIN vl_results_multiplicationfactor AS fctr_r ON res_r.worksheetID=fctr_r.worksheetID
	# 		    WHERE YEAR(s.created)=%s AND MONTH(s.created)=%s AND s.migrated = 'YES' AND in_worksheet = 1 AND result_migrated=0
	# 		    GROUP BY s.id LIMIT 20000"""

	# 	cursor = connections['old_db'].cursor()
	# 	cursor.execute(sql, [self.create_year, self.create_month])
	# 	self.old_results = utils.dictfetchall(cursor)

	# def __save_results(self):
	# 	self.__get_results()
	# 	for r in self.old_results:
	# 		try:
	# 			roche_result = r.get('roche_result')
	# 			abbott_result = r.get('abbott_result')
	# 			override_result = r.get('override_result')

	# 			if roche_result or abbott_result or override_result:
	# 				self.__save_result(r)
	# 				connections['old_db'].cursor().execute("UPDATE vl_samples SET result_migrated=1 WHERE id=%s"%r.get('sid'))
	# 				print "saved %s" %r.get('sid')
	# 			else:
	# 				print "pending %s" %r.get('sid')
	# 		except:
	# 			print "Failed %s" %r.get('sid')



	# def __save_result(self, r):
	# 	res = Result()
	# 	res.sample_id = r.get('sid')		

	# 	roche_result = r.get('roche_result')
	# 	abbott_result = r.get('abbott_result')
	# 	override_result = r.get('override_result')
		
	# 	if roche_result:
	# 		roche_results = roche_result.split('::')
	# 		res_log = self.__process_results(roche_results, "R")
	# 		res_str = roche_results[-1]
	# 		res_strs = res_str.split('||')
	# 		res.method = "R"
	# 	elif abbott_result:
	# 		abbott_results = abbott_result.split('::')
	# 		res_log = self.__process_results(abbott_results, "A")
	# 		res_str = abbott_results[-1]
	# 		res_strs = res_str.split('||')
	# 		res.method = "A"
	# 	else:
	# 		res_log = {}
	# 		res_str = None
	# 		res_strs = []
	# 		res.method = ""

		
	# 	if override_result:
	# 		res.result_numeric = 0
	# 		res.result_alphanumeric = 'Failed'
	# 		res.suppressed = 3
	# 	else:
	# 		if res_str:
	# 			res_dict = r_utils.get_result2(res_strs[0], res_strs[1] , res.method)
	# 		else:
	# 			res_dict = {}
	# 		res.result_numeric = res_dict.get('numeric_result',0)
	# 		res.result_alphanumeric = res_dict.get('alphanumeric_result','')
	# 		res.suppressed = res_dict.get('suppressed',3)

	# 	if res_str:
	# 		res.test_date = res_strs[2]
	# 		res.test_by = utils.get_or_create_user(res_strs[3])
	# 		res.authorised = True
	# 		res.authorised_by_id = 1
	# 		res.authorised_at = res.test_date
	# 		res.result1 = res_log.get('result1','')
	# 		res.result2 = res_log.get('result2','')
	# 		res.result3 = res_log.get('result3','')
	# 		res.result4 = res_log.get('result4','')
	# 		res.result5 = res_log.get('result5','')
	# 		res.save()

	# 		res_qc = ResultsQC()
	# 		res_qc.result = res
	# 		res_qc.released = True
	# 		res_qc.released_by_id = 1
	# 		res_qc.released_at = res.test_date
	# 		res_qc.save()
	# 		if r.get('date_printed'):
	# 			res_dispatch = ResultsDispatch()
	# 			res_dispatch.sample_id = res.sample_id
	# 			res_dispatch.dispatch_type = 'D'
	# 			res_dispatch.dispatch_date = r.get('date_printed')
	# 			res_dispatch.dispatched_by = utils.get_or_create_user(r.get('printed_by'))
	# 			res_dispatch.save()
		
	# def __process_results(self, results, machine_type):
	# 	ret={}
	# 	for i, res in enumerate(results, start=1):
	# 		ress = res.split('||')
	# 		res2 = ress[0]
	# 		if machine_type=='A' and res2.find('Copies')==-1 and res2 not in ['Target Not Detected', 'Not detected']:
	# 			res2 = 'Failed'
	# 		ret.update({'result%s'%i:res2})

	# 	return ret

				
