import datetime as dt, calendar, pandas as pd, zipfile, time
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Sample, Patient
from worksheets.models import Worksheet,WorksheetSample
from dateutil import parser
import logging

class Command(BaseCommand):
	help = "Reconcile VL sample IDs to begin from 1 for month"
	l = logging.getLogger('django.db.backends')
	l.setLevel(logging.DEBUG)
	l.addHandler(logging.StreamHandler())
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
		patients = Patient.objects.all()
		for p in patients:
			sanitized_art_no = utils.removeSpecialCharactersFromString(p.art_number)
			p.sanitized_art_number = sanitized_art_no
			p.save()


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
				'Barcode',
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
				'Test Date',
				'Lab QC date',
				'Data QC date',
				'Data QC date for Rejects',
				'Date downloaded',
				'Date Record Captured',
				'Worksheet(s)',
				'Date first added to Worksheet',
				'HIV DR Requested?',
				'DHIS2 Facility Name',
				'DHIS2 Facility Code',
				'Date of Results Upload',
				'WHO Status',
				'Specimen Storage Broad Consent',
				]
	def __get_worksheets_info(self, s):
		worksheets = s.worksheet_set.all()
		ref_numbers = '/'.join([w.worksheet_reference_number for w in worksheets])
		first_added = self.__local_date(worksheets[0].created_at) if len(worksheets) > 0 else ''
		return {'ref_numbers':ref_numbers, 'first_added':first_added}

	def __get_worksheet_barcode(self, s):
		#worksheet_sample = WorksheetSample.objects.get(sample_id=3870075)
		ws = WorksheetSample.objects.filter(sample=s).first()
		if ws:
			return ws.instrument_id
		else:
			return ''

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
