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
		self.create_month = options['period'][1]
		self.old_samples = []		
		self.appendices = {}
		self.__appendices()
		#print self.appendices
		for x in xrange(0,3):
			self.__save_samples()

	def __get_samples(self):

		sql = """SELECT s.*, s.id AS sid, p.*, p.id AS pid, s.createdby AS screatedby,s.created as screated,
				v.*, v.createdby AS verified_by, v.created AS vcreated, v.id AS vid
				FROM vl_samples AS s
				LEFT JOIN vl_patients AS p ON s.patientID=p.id
				LEFT JOIN vl_samples_verify AS v ON s.id=v.sampleID
				WHERE YEAR(s.created)=%s AND MONTH(s.created)=%s AND migrated = 'NO' GROUP BY s.id LIMIT 40000
				"""

		cursor = connections['old_db'].cursor()
		cursor.execute(sql, [self.create_year, self.create_month])
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
			user = utils.get_or_create_user(r.get('screatedby'))
			sid = r.get('sid')
			try:
				p, pat_created = Patient.objects.get_or_create(
					id=r.get('pid'),
					defaults={'unique_id':r.get('uniqueID'),
							  'art_number':r.get('artNumber'),
							  'other_id':r.get('otherID', ''),
							  'gender':self.genders.get(r.get('gender'), None),
							  'dob':utils.get_date(r, 'dateOfBirth'),
							  'created_by_id': user.id},
					)

				enve,env_created = Envelope.objects.get_or_create(envelope_number=r.get('lrEnvelopeNumber'))

				self.__save_sample(r, enve.id, user.id)

				vid = r.get('vid')
				if (vid!=None):
					self.__save_verification(r)
					
				connections['old_db'].cursor().execute("UPDATE vl_samples SET migrated='YES' WHERE id=%s"%sid)
				print "saved %s" %sid
			except :
				print "Failed %s" %sid



	def __save_sample(self, r, env_id, user_id):
		dup_form = r.get('dup_form_number')
		dup_lr = r.get('dup_locator_id')
		s = Sample()
		s.pk = int(r.get('sid'))
		s.patient_id = int(r.get('patientID'))
		s.patient_unique_id = r.get('patientUniqueID')
		s.locator_category = r.get('lrCategory', '')
		s.envelope_id = env_id
		lrN = r.get('lrNumericID', '')
		if dup_lr==1:
			lrN = "%s*"%lrN

		s.locator_position = lrN
		s.vl_sample_id = r.get('vlSampleID')
		form_number = r.get('formNumber', '')
		if dup_form == 1:
			form_number = "%s*"%form_number
		s.form_number = form_number
		s.facility_id = int(r.get('facilityID', 0))
		s.current_regimen_id = self.__appendix_id(r.get('currentRegimenID', 0), 3) 
		s.pregnant = self.choices.get(r.get('pregnant', ''), '')
		s.anc_number = r.get('pregnantANCNumber', '')
		s.breast_feeding = self.choices.get(r.get('breastfeeding', ''), '')
		s.active_tb_status = self.choices.get(r.get('activeTBStatus', ''), '')
		s.date_collected = utils.get_date(r, 'collectionDate')

		receiptDate= r.get('receiptDate')
		if receiptDate==None:
			s.date_received = s.date_collected
		else:
			s.date_received = utils.get_date(r, 'receiptDate')
		
		s.treatment_inlast_sixmonths = self.choices.get(r.get('treatmentLast6Months', ''), '')
		s.treatment_initiation_date = utils.get_date(r, 'treatmentInitiationDate')
		s.sample_type = self.sample_types.get(r.get('sampleTypeID', ''), '')
		s.viral_load_testing_id = self.__appendix_id(r.get('viralLoadTestingID', 0), 8)
		s.treatment_indication_id = self.__appendix_id(r.get('treatmentInitiationID', 0), 6)
		s.treatment_indication_other = r.get('treatmentInitiationOther', '')
		s.treatment_line_id = self.__appendix_id(r.get('treatmentStatusID', 0), 7)
		s.failure_reason_id = self.__appendix_id(r.get('reasonForFailureID', 0), 2)
		s.tb_treatment_phase_id = self.__appendix_id(r.get('tbTreatmentPhaseID', 0), 5)
		s.arv_adherence_id = self.__appendix_id(r.get('arvAdherenceID', 0), 1)
		s.in_worksheet = r.get('in_worksheet',0)

		vid = r.get('vid')
		if (vid!=None):
			s.verified = True

		
		#routine_monitoring = r.get('vlTestingRoutineMonitoring', 0)
		rm_test_date = utils.get_date(r, 'routineMonitoringLastVLDate')
		rm_value = r.get('routineMonitoringValue', '')
		rm_sample_type = self.sample_types.get(r.get('routineMonitoringSampleTypeID', 0), None)
		#repeat_testing = r.get('vlTestingRepeatTesting', 0)
		rt_test_date = utils.get_date(r, 'repeatVLTestLastVLDate')
		rt_value = r.get('repeatVLTestValue', '')
		rt_sample_type = self.sample_types.get(r.get('repeatVLTestSampleTypeID', 0), None)
		#suspected_treatment_failure = r.get('vlTestingSuspectedTreatmentFailure', 0)
		stf_test_date = utils.get_date(r, 'suspectedTreatmentFailureLastVLDate')
		stf_value = r.get('suspectedTreatmentFailureValue', '')
		stf_sample_type = self.sample_types.get(r.get('suspectedTreatmentFailureSampleTypeID', 0), None)

		s.last_test_date = rm_test_date or rt_test_date or stf_test_date
		s.last_value = rm_value or rt_value or stf_value
		s.last_sample_type = rm_sample_type or rt_sample_type or stf_sample_type
		s.created_at = utils.get_date(r, 'screated')

		s.created_by_id = user_id
		s.save()


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
