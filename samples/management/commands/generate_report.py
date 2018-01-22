import datetime as dt, calendar, pandas as pd, zipfile
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Sample

class Command(BaseCommand):
	help = "Reconcile VL sample IDs to begin from 1 for month"

	def add_arguments(self, parser):
		parser.add_argument('period', nargs='+')

	def handle(self, *args, **options):
		self.year = int(options['period'][0])
		self.month = int(options['period'][1])
		self.__generate_report()

	# FormNumber,LocationID,SampleID,Facility,
	# District,Hub,IP,DateofCollection,
	# SampleType,PatientART,PatientOtherID,Gender,
	# Age,PhoneNumber,HasPatientBeenontreatment,DateofTreatmentInitiation,
	# CurrentRegimen,OtherRegimen,IndicationforTreatmentInitiation,WhichTreatmentLineisPatienton,ReasonforFailure,
	# IsPatientPregnant,ANCNumber,IsPatientBreastfeeding,PatienthasActiveTB,
	# IfYesaretheyon,ARVAdherence,RoutineMonitoring,LastViralLoadDate1,
	# LastViralLoadValue1,SampleType1,RepeatViralLoadTest,LastViralLoadDate2,
	# LastViralLoadValue2,SampleType2,SuspectedTreatmentFailure,LastViralLoadDate3,
	# LastViralLoadValue3,SampleType3,Tested,LastWorksheet,
	# MachineType,VLResult,DateTimeApproved,DateTimeRejected,
	# RejectionReason,DateTimeAddedtoWorksheet,DateTimeLatestResultsUploaded,DateTimeResultsPrinted,
	# DateReceivedatCPHL,DateTimeFirstPrinted,DateTimeSamplewasCaptured



	def __generate_report(self):
		num_days = calendar.monthrange(self.year, self.month)[1]
		file_name = "%s%s.csv"%(self.year,format(self.month,'02'))
		file_path = "media/reports/%s"%file_name
		df = pd.DataFrame([], columns=self.__get_headers())
		df.to_csv(file_path, index=False, header=self.__get_headers(), mode='w')
		for day in range(1, num_days+1):
			date = dt.date(self.year, self.month, day)
			samples = Sample.objects.filter(created_at__date=date)

			output = []
			for s in samples:
				then_date = s.date_collected if s.date_collected else s.date_received
				dob = s.patient.dob
				age = then_date.year-dob.year if then_date and dob else ""
					
				result = utils.getattr_ornone(s, 'result')
				authorised = result.authorised if result else False
				approval = utils.getattr_ornone(s, 'verification')
				accepted = approval.accepted if approval else 'pending'
				if accepted == True:
					status = 'accepted'
				elif accepted == False:
					status = 'rejeced'
				else:
					status = ''
				verification_date = approval.created_at if approval else ''
				rejection_reason = utils.getattr_ornone(approval.rejection_reason, 'appendix') if approval else ''

				output.append([
						s.form_number,
						"%s%s/%s"%(s.locator_category, s.envelope.envelope_number, s.locator_position),
						s.facility.facility,
						self.__get_district(s.facility),
						self.__get_hub(s.facility),
						s.date_collected,
						s.date_received,
						s.get_sample_type_display(),
						s.patient.art_number,
						s.patient.other_id,
						s.patient_unique_id,
						s.patient.gender,
						dob,
						age,
						s.treatment_initiation_date,
						s.get_treatment_duration_display(),
						utils.getattr_ornone(s.current_regimen, 'appendix'),
						s.other_regimen,
						utils.getattr_ornone(s.viral_load_testing, 'appendix'),
						utils.getattr_ornone(s.treatment_line, 'appendix'),
						utils.getattr_ornone(s.failure_reason, 'appendix'),
						s.pregnant,
						s.anc_number,
						s.breast_feeding,
						s.active_tb_status,
						utils.getattr_ornone(s.tb_treatment_phase, 'appendix'),
						utils.getattr_ornone(s.arv_adherence, 'appendix'),
						status,
						verification_date,
						rejection_reason,
						'Y' if result else 'N',
						'Y' if authorised else 'N',
						result.result_alphanumeric if result else '',
						result.get_suppressed_display() if result else '',
						result.test_date if result else ''
						])

			df = pd.DataFrame(output)			
			df.to_csv(file_path, index=False, header=False, mode='a', encoding='utf-8')
			print "generated for %s"%date

		zf = zipfile.ZipFile('%s.zip'%file_path, mode='w', compression=zipfile.ZIP_DEFLATED)
		try:
			zf.write(file_path, arcname=file_name)
		finally:
			zf.close()

	def __get_hub(self, facility):		
		if hasattr(facility, 'hub'):
			return utils.getattr_ornone(facility.hub, 'hub')
		else:
			return ""

	def __get_district(self, facility):		
		if hasattr(facility, 'district'):
			return utils.getattr_ornone(facility.district, 'district')
		else:
			return ""


	def __get_headers(self):
		return [
				'Form Number',
				'Location ID',
				'Facility',
				'District',
				'Hub',
				'Date collected',
				'Date Received',
				'Sampe Type',
				'Art Number',
				'Other ID',
				'Unique ID',
				'Sex',
				'Date of Birth',
				'Age (years)',
				'Treatment Initiation Date',
				'Duration on Treatment',
				'Current Regimen',
				'Other Regimen',
				'Treatment Line',
				'Indication for Viral Load Testing',
				'Failure Reason',
				'Pregnant',
				'ANC Number',
				'Breast Feeding',
				'Active TB Status',
				'TB Treatment Phase',
				'ARV Adherence',
				'Status',
				'Approval Date',
				'Rejection Reason',
				'Tested',
				'Passed Lab QC?',
				'Result',
				'Suppressed',
				'Test Date'
				]