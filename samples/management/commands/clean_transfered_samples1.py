import datetime as dt
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Patient, Sample, PatientPhone, Envelope, Verification
from backend.models import Appendix
from results.models import Result,ResultsQC

class Command(BaseCommand):
	help = "Transfer sample data from old database to the new database"
	choices = {'No':'N', 'Yes':'Y', 'Left Blank':'L'}
	sample_types = {1:'D', 2:'P'}
	genders = {'Female':'F', 'Male':'M', 'Left Blank':'L', 'Missing Gender':'X'}

	def add_arguments(self, parser):
		parser.add_argument('period', nargs='+')

	def handle(self, *args, **options):
		self.create_year = options['period'][0]
		self.creat_month = options['period'][1]
		self.old_samples = []		
		self.appendices = {}
		self.__appendices()
		#print self.appendices
		self.__save_samples()

	def __get_samples(self):

		# sql = """SELECT s.id AS sid, p.id AS pid, p.created AS pcreated, 
		# 		s.created as screated, v.created AS vcreated, v.id AS vid, s.receiptDate
		# 		FROM vl_samples AS s
		# 		LEFT JOIN vl_patients AS p ON s.patientID=p.id
		# 		LEFT JOIN vl_samples_verify AS v ON s.id=v.sampleID
		# 		WHERE YEAR(s.created)=%s AND MONTH(s.created)=%s AND migrated = 'YES' GROUP BY s.id
		# 		"""

		# cursor = connections['old_db'].cursor()
		# cursor.execute(sql, [self.create_year, self.creat_month])

		sql = """SELECT s.id AS sid, p.id AS pid, p.created AS pcreated, 
				s.created as screated, v.created AS vcreated, v.id AS vid, s.receiptDate
				FROM vl_samples AS s
				LEFT JOIN vl_patients AS p ON s.patientID=p.id
				LEFT JOIN vl_samples_verify AS v ON s.id=v.sampleID
				WHERE facilityID =2537 AND migrated = 'YES' GROUP BY s.id
				"""

		cursor = connections['old_db'].cursor()
		cursor.execute(sql)
		self.old_samples = utils.dictfetchall(cursor)

	def __appendices(self):
		res = Appendix.objects.values('id', 'code', 'appendix_category_id')
		ret = {}
		for r in res:
			cat_id = int(r['appendix_category_id'])
			cat_dict = ret.get(cat_id, {})			
			cat_dict[int(r['code'])] = int(r['id'])
			ret[cat_id] = cat_dict

		self.appendices = ret;	

	def __appendix_id(self, val, cat_id):
		cat_dict = self.appendices.get(cat_id, {})
		appendix_id = cat_dict.get(val, None)
		return appendix_id
		

	def __save_samples(self):
		self.__get_samples()
		for r in self.old_samples:
			#print r.get('treatmentStatusID')
			sid = r.get('sid')
			try:
				p = Patient.objects.filter(pk=r.get('pid')).first()
				if p:
					#p.created_at = dt.datetime.strptime(r.get('pcreated'), "%Y-%m-%d %H:%M:%S")
					p.created_at = r.get('pcreated')
					p.save()

				s = Sample.objects.filter(pk=sid).first()
				if s:
					#dt.datetime.strptime("2016-09-09 10:00:01", '%Y-%m-%d %H:%M:%S')
					#s.created_at = dt.datetime.strptime(r.get('screated'), "%Y-%m-%d %H:%M:%S")
					s.created_at = r.get('screated')
					receiptDate= r.get('receiptDate')
					if receiptDate==None:
						s.date_received = s.created_at
					else:
						s.date_received = utils.get_date(r, 'receiptDate')
					s.save()

					v = Verification.objects.filter(sample=s).first()
					if v:
						#v.created_at = dt.datetime.strptime(r.get('vcreated'), "%Y-%m-%d %H:%M:%S")
						v.created_at = r.get('vcreated')
						v.save()

				print "updated %s" %sid
			except :
				print "Failed %s" %sid
