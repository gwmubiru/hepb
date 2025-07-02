from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

import backend.models as backend

# Create your models here.

#hold records of forms dispatched to facilities
class ClinicalRequestFormsDispatch(models.Model):
	facility = models.ForeignKey(backend.Facility, on_delete=models.CASCADE)
	id = models.AutoField(primary_key=True)
	ref_number =  models.CharField(max_length=64, null=True)
	dispatched_at = models.DateTimeField()
	dispatched_by = models.ForeignKey(User, on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_forms_dispatch'
		verbose_name_plural = 'Forms Dispatch'


#hold the form numbers
class ClinicalRequestForm(models.Model):
	form_number = models.CharField(max_length=128, unique=True)
	id = models.AutoField(primary_key=True)
	dispatch = models.ForeignKey(ClinicalRequestFormsDispatch, on_delete=models.CASCADE, null=True)
	received_back = models.BooleanField(default=False)
	
	class Meta:
		db_table = 'vl_forms'
		verbose_name_plural = 'Forms'

class Clinician(models.Model):
	facility = models.ForeignKey(backend.Facility, on_delete=models.CASCADE)
	id = models.AutoField(primary_key=True)
	cname = models.CharField(max_length=128)
	cphone = models.CharField(max_length=64, null=True, blank=True)
	class Meta:
		db_table = 'vl_clinicians'
		unique_together = ('facility', 'cname')

class LabTech(models.Model):
	facility = models.ForeignKey(backend.Facility, on_delete=models.CASCADE)
	id = models.AutoField(primary_key=True)
	lname = models.CharField(max_length=128)
	lphone = models.CharField(max_length=64, null=True, blank=True)
	class Meta:
		db_table = 'vl_lab_techs'
		unique_together = ('facility', 'lname')	

#holds the facility patients on ART
class FacilityPatient(models.Model):
	GENDER_CHOICES = (
		('M', 'Male'),
		('F', 'Female'),
		('L', 'Left Blank'),
	)
	id = models.AutoField(primary_key=True)
	art_number = models.CharField(max_length=255, null=True, blank=True)	
	unique_id = models.CharField(max_length=255, null=True, blank=True)	
	treatment_initiation_date = models.DateField(null=True, blank=True)
	date_of_birth = models.DateField(null=True, blank=True)
	facility = models.ForeignKey(backend.Facility,null=True, blank=True, on_delete=models.CASCADE)
	gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
	class Meta:
		db_table = 'facility_patients'

#hold patient records that later on link to the samples
class Patient(models.Model):
	GENDER_CHOICES = (
		('M', 'Male'),
		('F', 'Female'),
		('X', 'Missing Gender'),
		('L', 'Left Blank'),
	)
	TX_DURATION_CHOICES = ( (1, '6 months -< 1yr'), (2, '1 -< 2yrs'), (3, '2 -< 5yrs'), (4, '5yrs and above'), (5, 'Left Blank') )
	id = models.AutoField(primary_key=True)
	unique_id = models.CharField(max_length=128, null=True, blank=True)
	art_number = models.CharField(max_length=64, null=True, blank=True)
	sanitized_art_number = models.CharField(max_length=64, null=True, blank=True)
	other_id = models.CharField(max_length=64, null=True, blank=True)
	gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
	dob = models.DateField(null=True, blank=True)
	facility = models.ForeignKey(backend.Facility,null=True, blank=True, on_delete=models.CASCADE)
	facility_patient = models.ForeignKey(FacilityPatient,null=True, blank=True, on_delete=models.CASCADE)
	parent_id = models.PositiveIntegerField(null=True, blank=True)
	treatment_initiation_date = models.DateField(null=True, blank=True)
	current_regimen_initiation_date = models.DateField(null=True, blank=True)
	treatment_duration = models.PositiveSmallIntegerField(choices=TX_DURATION_CHOICES, null=True, blank=True)
	is_verified = models.PositiveSmallIntegerField(default=0)
	is_the_clean_patient = models.PositiveSmallIntegerField(default=0)
	created_by = models.ForeignKey(User, on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_patients'

class PatientPhone(models.Model):
	patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
	id = models.AutoField(primary_key=True)
	phone = models.CharField(max_length=16, null=True, blank=True)

	class Meta:
		db_table = 'vl_patient_phones'


class Envelope(models.Model):
	envelope_number = models.CharField(max_length=10)
	id = models.AutoField(primary_key=True)
	stage = models.PositiveSmallIntegerField(choices=((1,'not_verified'), (2, 'verified'), (3, 'in_worksheet'),(4, 'completed')), default=1)
	sample_type = models.CharField(max_length=1, choices=( ('P', 'Plasma'), ('D', 'DBS') ), default='')
	sample_medical_lab = models.ForeignKey(backend.MedicalLab,related_name='sample_medical_lab', default=1, on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)

	# def __init__(self):
	# 	return self.envelope_number

	class Meta:
		db_table = 'vl_envelopes'

class SampleReception(models.Model):
	SAMPLE_TYPES = ( ('P', 'Plasma'), ('D', 'DBS') )
	id = models.AutoField(primary_key=True)
	barcode = models.TextField(unique=True)
	facility = models.ForeignKey(backend.Facility, on_delete=models.CASCADE)
	art_number = models.CharField(max_length=64, null=True, blank=True)
	date_collected = models.DateField(null=True, blank=True)
	date_received = models.DateField()
	sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES)
	is_data_entered = models.PositiveSmallIntegerField(default=False)
	creator = models.ForeignKey(User, related_name='creator', on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.barcode
	
	class Meta:
		db_table = 'vl_sample_reception'

class TrackingCode(models.Model):
	code = models.TextField(unique=True)
	id = models.AutoField(primary_key=True)
	status = models.PositiveSmallIntegerField(default=False)
	creation_by = models.ForeignKey(User, related_name='creation_by', on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.code
	
	class Meta:
		db_table = 'vl_tracking_codes'

class Sample(models.Model):
	YES_NO_CHOICES = ( ('Y', 'Yes'), ('N', 'No'), ('L', 'Left Blank') )
	id = models.AutoField(primary_key=True)
	CONSENT_CHOICES = ( ('Y', 'Accept'), ('N', 'Decline'), ('L', 'Left Blank') )
	SAMPLE_TYPES = ( ('P', 'Plasma'), ('D', 'DBS') )
	TX_DURATION_CHOICES = ( (1, '6 months -< 1yr'), (2, '1 -< 2yrs'), (3, '2 -< 5yrs'), (4, '5yrs and above'), (5, 'Left Blank') )
	WHO_STAGES = ((1, 'I'), (2, 'II'), (3, 'III'), (4, 'IV'))
	STAGES = ((1, 'Created'), (2, 'Pending_result_auth'), (3, 'panding_result_release'), (4, 'completed'))
	TX_CARE_APPROACHES = ((1, 'FBIM'), (2, 'FBG'), (3, 'FTDR'), (4, 'CDDP'), (5, 'CCLAD'))
	patient = models.ForeignKey(Patient, null=True, blank=True, on_delete=models.CASCADE)
	patient_unique_id = models.CharField(max_length=128)
	reception_art_number = models.CharField(max_length=40,null=True, blank=True)
	locator_category = models.CharField(max_length=1, choices=( ('V', 'V'), ('R', 'R'),('W', 'W') ))
	envelope = models.ForeignKey(Envelope,null=False, blank=False, on_delete=models.CASCADE)
	locator_position = models.CharField(max_length=4)
	vl_sample_id = models.CharField(max_length=128, unique=True, null=True, blank=True)
	form_number = models.CharField(max_length=64, unique=True)
	facility = models.ForeignKey(backend.Facility,null=False, blank=False, on_delete=models.CASCADE)
	facility_patient = models.ForeignKey(FacilityPatient,null=True, blank=True, on_delete=models.CASCADE)
	sample_reception = models.ForeignKey(SampleReception,null=True, blank=True, on_delete=models.CASCADE)
	tracking_code = models.ForeignKey(TrackingCode, on_delete=models.CASCADE)
	current_regimen = models.ForeignKey(backend.Appendix, related_name='current_regimen',null=True, blank=True, on_delete=models.CASCADE)
	other_regimen = models.CharField(max_length=128, null=True, blank=True)
	pregnant = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True, blank=True)
	anc_number = models.CharField(max_length=64, null=True, blank=True) #anc number for pregnant women
	breast_feeding = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True, blank=True)
	consented_sample_keeping = models.CharField(max_length=1, choices=CONSENT_CHOICES, null=True, blank=True)
	active_tb_status = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True, blank=True)
	date_collected = models.DateField(null=True, blank=True)
	date_received = models.DateField()
	treatment_duration = models.PositiveSmallIntegerField(choices=TX_DURATION_CHOICES, null=True, blank=True)
	treatment_initiation_date = models.DateField(null=True, blank=True)
	
	is_study_sample = models.BooleanField(default=False)
	current_who_stage = models.PositiveSmallIntegerField(choices=WHO_STAGES, null=True, blank=True)
	stage = models.PositiveSmallIntegerField(choices=STAGES, null=True, blank=True)
	sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES,null=True, blank=True)
	viral_load_testing = models.ForeignKey(backend.Appendix, related_name='viral_load_testing', on_delete=models.CASCADE)
	treatment_indication = models.ForeignKey(backend.Appendix, related_name='treatment_indication', null=True, blank=True, on_delete=models.CASCADE)
	treatment_indication_other = models.CharField(max_length=64, null=True, blank=True)
	treatment_line = models.ForeignKey(backend.Appendix, related_name='treatment_line',null=True, blank=True, on_delete=models.CASCADE)
	failure_reason = models.ForeignKey(backend.Appendix, related_name='failure_reason', null=True, blank=True, on_delete=models.CASCADE)
	tb_treatment_phase = models.ForeignKey(backend.Appendix, related_name='tb_treatment_phase', null=True, blank=True, on_delete=models.CASCADE)
	arv_adherence = models.ForeignKey(backend.Appendix, related_name='arv_adherence', null=True, blank=True, on_delete=models.CASCADE)
	treatment_care_approach = models.PositiveSmallIntegerField(choices=TX_CARE_APPROACHES, null=True, blank=True)
	is_data_entered = models.PositiveSmallIntegerField(default=False)
	
	last_test_date = models.DateField(null=True, blank=True)
	last_value = models.CharField(max_length=64, null=True, blank=True)
	last_sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES, null=True, blank=True)
	clinician = models.ForeignKey(Clinician, null=True, blank=True, on_delete=models.CASCADE)
	lab_tech = models.ForeignKey(LabTech, null=True, blank=True, on_delete=models.CASCADE)
	
	verified = models.BooleanField(default=True)
	in_worksheet = models.BooleanField(default=False)
	created_by = models.ForeignKey(User, related_name='created_by',null=True, blank=True, on_delete=models.CASCADE)
	updated_by = models.ForeignKey(User, related_name='updated_by', null=True, on_delete=models.CASCADE)
	data_entered_by = models.ForeignKey(User, related_name='data_entered_by', null=True, on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)
	data_entered_at = models.DateTimeField(null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True)
	barcode = models.TextField(null=True, blank=True)
	barcode = models.TextField(null=True, blank=True)
	barcode2 = models.TextField(null=True, blank=True)
	barcode3 = models.TextField(null=True, blank=True)
	barcode4 = models.TextField(null=True, blank=True)
	barcode5 = models.TextField(null=True, blank=True)



	def __str__(self):
		return self.form_number
	
	class Meta:
		db_table = 'vl_samples'
		#unique_together = ('locator_category', 'envelope', 'locator_position')

class SampleIdentifier(models.Model):
	barcode = models.TextField(unique=True)
	id = models.AutoField(primary_key=True)
	sample = models.ForeignKey(backend.Facility, on_delete=models.CASCADE)
	is_completed = models.PositiveSmallIntegerField(default=False)
	stage = models.PositiveSmallIntegerField(default=False)
	createby = models.ForeignKey(User, related_name='createby', on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)
	result_numeric = models.TextField(null=True, blank=True)
	result_alphanumeric = models.TextField(null=True, blank=True)
	test_date = models.DateTimeField(null=True, blank=True) 
	tested_by = models.ForeignKey(User, related_name='tested_by', null=True, on_delete=models.CASCADE)
	

	def __str__(self):
		return self.barcode
	
	class Meta:
		db_table = 'vl_sample_identifiers'

class DrugResistanceRequest(models.Model):
	sample = models.OneToOneField(Sample, on_delete=models.CASCADE)
	id = models.AutoField(primary_key=True)
	body_weight = models.PositiveSmallIntegerField(null=True, blank=True)
	patient_on_rifampicin = models.CharField(max_length=1, choices=( ('Y', 'Yes'), ('N', 'No'),), null=True, blank=True)

	class Meta:
		db_table = 'vl_drug_resistance_requests'

class PastRegimens(models.Model):
	drug_resistance_request = models.ForeignKey(DrugResistanceRequest, on_delete=models.CASCADE)
	id = models.AutoField(primary_key=True)
	regimen =  models.ForeignKey(backend.Appendix, on_delete=models.CASCADE)
	start_date = models.DateField(null=True, blank=True)
	stop_date = models.DateField(null=True, blank=True)

	class Meta:
		db_table = 'vl_past_regimens'

class DrugResistanceResults(models.Model):
	drug_resistance_request = models.ForeignKey(DrugResistanceRequest, on_delete=models.CASCADE)
	id = models.AutoField(primary_key=True)
	results_file = models.FileField(upload_to='drug_resistance_results')
	upload_date = models.DateTimeField(auto_now_add=True)
	drr_uploaded_by = models.ForeignKey(User, related_name='drr_uploaded_by', on_delete=models.CASCADE)

	class Meta:
		db_table = 'vl_drug_resistance_results'

class Verification(models.Model):
	sample = models.OneToOneField(Sample, on_delete=models.CASCADE)
	id = models.AutoField(primary_key=True)
	accepted = models.BooleanField(default=False)
	rejection_reason = models.ForeignKey(backend.Appendix, null=True, blank=True, on_delete=models.CASCADE)
	comments = models.CharField(max_length=128, null=True, blank=True)
	verified_by = models.ForeignKey(User, related_name='verified_by', on_delete=models.CASCADE)
	pat_edits = models.PositiveSmallIntegerField(default=0)
	sample_edits = models.PositiveSmallIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)


	class Meta:
		db_table = 'vl_verifications'
		
class VerificationRejectionReason(models.Model):
	sample = models.ForeignKey(Sample, on_delete=models.CASCADE)
	id = models.AutoField(primary_key=True)
	rejection_reason = models.ForeignKey(backend.Appendix, null=True, on_delete=models.CASCADE)

	class Meta:
		db_table = 'vl_verification_rejection_reasons'

#track sample sample printing and dispatch
class RejectedSamplesRelease(models.Model):
	REJECTS_STATUS = ((1, 'Released'), (0, 'Pending'), (3, 'Retained'))
	id = models.AutoField(primary_key=True)
	sample = models.OneToOneField(Sample, on_delete=models.CASCADE)
	#released = models.BooleanField(default=False)
	released = models.PositiveSmallIntegerField(choices=REJECTS_STATUS, null=True, blank=True)
	reject_released_by = models.ForeignKey(User, related_name='reject_released_by', null=True, on_delete=models.CASCADE)
	released_at = models.DateTimeField(null=True)
	comments = models.TextField(null=True)

	class Meta:
		db_table = 'vl_rejected_samples_release'

class TempUsedBarcode(models.Model):
	form_number = models.CharField(max_length=128)
	id = models.AutoField(primary_key=True)
	barcode = models.CharField(max_length=128)
	class Meta:
		db_table = 'temp_used_barcodes'

class patientTransferHistory(models.Model):
	old_art_number = models.CharField(max_length=64, null=True, blank=True)
	id = models.AutoField(primary_key=True)
	current_art_number = models.CharField(max_length=64, null=True, blank=True)
	patient_id = models.PositiveIntegerField(null=True, blank=True)
	old_facility_id = models.PositiveIntegerField(null=True, blank=True)
	current_facility_id = models.PositiveIntegerField(null=True, blank=True)
	created_at = models.DateTimeField(null=True)
	class Meta:
		db_table = 'patient_transfer_history'
