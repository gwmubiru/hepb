from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Patient, Sample, PatientPhone, Envelope
from backend.models import Appendix


class Command(BaseCommand):
	help = "Transfer sample data from old database to the new database"
	choices = {'No':'N', 'Yes':'Y', 'Left Blank':'L',}
	sample_types = {1:'D', 2:'P'}
	genders = {'Female':'F', 'Male':'M', 'L':'Left Blank', 'X':'Missing Gender'}

	def add_arguments(self, parser):
		parser.add_argument('period', nargs='+')

	def handle(self, *args, **options):
		self.create_year = options['period'][0]
		self.create_month = options['period'][1]
		self.old_samples = []		
		self.__get_samples()

		self.appendices = {}
		self.__appendices()
		#print self.appendices
		self.__save_samples()

	def __get_samples(self):		

		sql = """SELECT s.*, s.id AS sid, p.*, p.id AS pid 
				FROM vl_samples AS s
				LEFT JOIN vl_patients AS p ON s.patientID=p.id
				WHERE YEAR(s.created)=%s AND MONTH(s.created)=%s"""

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
		for r in self.old_samples:
			#print r.get('treatmentStatusID')
			p, pat_created = Patient.objects.get_or_create(
				id=r.get('pid'),
				unique_id=r.get('uniqueID', ''),
				art_number=r.get('artNumber', ''),
				other_id=r.get('otherID', ''),
				gender=self.genders.get(r.get('gender', ''), None),
				dob=utils.get_date(r, 'dateOfBirth'),
				defaults={'created_by_id':1},
				)

			enve,env_created = Envelope.objects.get_or_create(envelope_number=r.get('lrEnvelopeNumber'))

			s = Sample()
			s.id = int(r.get('id'))
			s.patient_id = int(r.get('patientID'))
			s.patient_unique_id = r.get('patientUniqueID')
			s.locator_category = r.get('lrCategory', '')
			s.envelope_id = enve.id
			s.locator_position = int(r.get('lrNumericID', ''))
			s.vl_sample_id = r.get('vlSampleID')
			s.form_number = r.get('formNumber', '')
			s.facility_id = int(r.get('facilityID', 0))
			s.current_regimen_id = self.__appendix_id(r.get('currentRegimenID', 0), 3) 
			s.pregnant = self.choices.get(r.get('pregnant', ''), '')
			s.anc_number = r.get('pregnantANCNumber', '')
			s.breast_feeding = self.choices.get(r.get('breastfeeding', ''), '')
			s.active_tb_status = self.choices.get(r.get('activeTBStatus', ''), '')
			s.date_collected = utils.get_date(r, 'collectionDate')
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


			s.routine_monitoring = r.get('vlTestingRoutineMonitoring', 0)
			s.routine_monitoring_last_test_date = utils.get_date(r, 'routineMonitoringLastVLDate')
			s.routine_monitoring_last_value = r.get('routineMonitoringValue', '')
			s.routine_monitoring_last_sample_type = self.sample_types.get(r.get('routineMonitoringSampleTypeID', 0), None)

			s.repeat_testing = r.get('vlTestingRepeatTesting', 0)
			s.repeat_testing_last_test_date = utils.get_date(r, 'repeatVLTestLastVLDate')
			s.repeat_testing_last_value = r.get('repeatVLTestValue', '')
			s.repeat_testing_last_sample_type = self.sample_types.get(r.get('repeatVLTestSampleTypeID', 0), None)

			s.suspected_treatment_failure = r.get('vlTestingSuspectedTreatmentFailure', 0)
			s.suspected_treatment_failure_last_test_date = utils.get_date(r, 'suspectedTreatmentFailureLastVLDate')
			s.suspected_treatment_failure_last_value = r.get('suspectedTreatmentFailureValue', '')
			s.suspected_treatment_failure_last_sample_type = self.sample_types.get(r.get('suspectedTreatmentFailureSampleTypeID', 0), None)

			s.created_by_id = 1

			s.save()

			print "saved %d" %s.id