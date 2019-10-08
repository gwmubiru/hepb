import datetime as dt, calendar, pandas as pd, zipfile, time
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Sample
from dateutil import parser

class Command(BaseCommand):
	help = "Reconcile VL sample IDs to begin from 1 for month"

	def handle(self, *args, **options):
		for n in range(3):
			now = time.localtime()
			period = time.localtime(time.mktime((now.tm_year, now.tm_mon - n, 1, 0, 0, 0, 0, 0, 0)))[:2]
			self.year = period[0]
			self.month = period[1]
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
				data_qc = utils.getattr_ornone(result, 'resultsqc')
				data_qc_at = data_qc.released_at if data_qc else ""

				rdata_qc = utils.getattr_ornone(s, 'rejectedsamplesrelease')
				rdata_qc_at = rdata_qc.released_at if rdata_qc else ""

				dispatch = utils.getattr_ornone(s, 'resultsdispatch')
				dispatched_at = dispatch.dispatch_date if dispatch else ''

				authorised = result.authorised if result else False
				approval = utils.getattr_ornone(s, 'verification')
				accepted = approval.accepted if approval else 'pending'
				if accepted == True:
					status = 'accepted'
				elif accepted == False:
					status = 'rejected'
				else:
					status = ''
				verification_date = approval.created_at if approval else ''
				rejection_reason = utils.getattr_ornone(approval.rejection_reason, 'appendix') if approval else ''


				w_info = self.__get_worksheets_info(s)

				date_tested = self.__local_date(result.test_date) if result else ''
				date_uploaded = self.__local_date(result.result_upload_date) if result else ''

				sample_arr = [
						s.form_number,
						"%s%s/%s"%(s.locator_category, s.envelope.envelope_number, s.locator_position),
						s.facility.facility,
						self.__get_district(s.facility),
						self.__get_hub(s.facility),
						self.__local_date(s.date_collected),
						self.__local_date(s.date_received),
						s.get_sample_type_display(),
						s.patient.name,
						s.patient.hep_number,
						s.patient.other_id,
						s.patient_unique_id,
						s.patient.gender,
						self.__local_date(dob),
						age,
						self.__local_date(s.treatment_initiation_date),
						utils.getattr_ornone(s.current_regimen, 'appendix'),
						utils.getattr_ornone(s.viral_load_testing, 'appendix'),	
						s.pregnant,
						s.breast_feeding,
						self.__local_date(verification_date),
						rejection_reason,

						'Y' if result else 'N',
						'Y' if authorised else 'N',
						result.result_alphanumeric if result else '',
						date_tested,

						self.__local_date(result.authorised_at) if result else '',
						self.__local_date(data_qc_at),
						self.__local_date(rdata_qc_at),
						self.__local_date(dispatched_at),
						self.__local_date(s.created_at),
						w_info.get('ref_numbers'),
						w_info.get('first_added'),
						
						s.facility.dhis2_name,
						s.facility.dhis2_uid,
						date_uploaded if date_uploaded  else date_tested,
						]
				output.append(sample_arr)

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
				'Patient Name',
				'Hep B Number',
				'Other ID',
				'Unique ID',
				'Sex',
				'Date of Birth',
				'Age (years)',
				'Treatment Initiation Date',
				'Current Regimen',
				'Indication for Viral Load Testing',
				'Pregnant',
				'Breast Feeding',
				'Approval Date',
				'Rejection Reason',
				'Tested',
				'Passed Lab QC?',
				'Result',
				'Test Date',
				'Lab QC date',
				'Data QC date',
				'Data QC date for Rejects',
				'Date dispatched',
				'Date Record Captured',
				'Worksheet(s)',
				'Date first added to Worksheet',
				'DHIS2 Facility Name',
				'DHIS2 Facility Code',
				'Date of Results Upload',
				]
	def __get_worksheets_info(self, s):
		worksheets = s.worksheet_set.all()
		ref_numbers = '/'.join([w.worksheet_reference_number for w in worksheets])
		first_added = self.__local_date(worksheets[0].created_at) if len(worksheets) > 0 else ''
		return {'ref_numbers':ref_numbers, 'first_added':first_added}

	def __dr_requested(self, s):
		ret = 'N'
		dr = utils.getattr_ornone(s, 'drugresistancerequest')
		if dr:
			ret = 'Y' if (dr.patient_on_rifampicin or dr.body_weight) else 'N'
		return ret


	def __local_date(self, date_val):
		format = "%d-%b-%Y"
		ret = ''
		try:
			if hasattr(date_val, 'strftime'):
				ret = date_val.strftime(format)
			elif date_val:
				#date_obj = dt.datetime.strptime(date_val,"%Y-%m-%d")
				date_obj = parser.parse(date_val)
				ret = date_obj.strftime(format)
			else:
				ret = ""
		except:
			ret = ''

		return ret