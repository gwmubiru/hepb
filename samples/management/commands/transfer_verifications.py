import datetime as dt
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Patient, Sample, PatientPhone, Envelope, Verification
from backend.models import Appendix
from results.models import Result,ResultsQC

class Command(BaseCommand):
	help = "Transfer unverified samples from old system"
	choices = {'No':'N', 'Yes':'Y', 'Left Blank':'L'}
	sample_types = {1:'D', 2:'P'}
	genders = {'Female':'F', 'Male':'M', 'Left Blank':'L', 'Missing Gender':'X'}

	def add_arguments(self, parser):
		parser.add_argument('period', nargs='+')

	def handle(self, *args, **options):
		self.create_year = options['period'][0]
		self.create_month = options['period'][1]	
		self.appendices = {}
		self.__appendices()
		self.__update_samples()

	def __update_samples(self):
		unverified_samples = Sample.objects.filter(verified=0,created_at__year=int(self.create_year), created_at__month=int(self.create_month))
		for sample in unverified_samples:
			sql = """SELECT v.*, s.id AS sid,s.created as screated, v.created AS vcreated, v.id AS vid, v.createdby AS verified_by,in_worksheet
				FROM vl_samples AS s
				LEFT JOIN vl_patients AS p ON s.patientID=p.id
				LEFT JOIN vl_samples_verify AS v ON s.id=v.sampleID
				WHERE s.id=%s  GROUP BY s.id
				"""
			cursor = connections['old_db'].cursor()
			cursor.execute(sql,[sample.pk])
			old_samples = utils.dictfetchall(cursor)


			# try:
			if len(old_samples)>0:
				old_sample = old_samples[0]
				vid = old_sample.get('vid')
				if (vid!=None):
					sample.verified = True
					sample.save()
					self.__save_verification(old_sample)
					print "Updated %s as %s" %(sample.pk,  old_sample.get('vcreated'))
			# except:
			# 	print "Failed %s" %sample.pk

	def __save_verification(self, r):
		outcome = r.get('outcome')
		in_worksheet = r.get('in_worksheet',0)
		user = utils.get_or_create_user(r.get('verified_by'))

		v = Verification()
		v.sample_id = int(r.get('sid'))
		v.comments = r.get('comments')
		v.accepted = True if(outcome=='Accepted' or in_worksheet==1) else False
		v.created_at = r.get('vcreated')
		v.rejection_reason_id = self.__appendix_id(r.get('outcomeReasonsID', 0), 4)
		v.verified_by_id = user.id
		v.save()
		v.created_at = r.get('vcreated')
		v.save()


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