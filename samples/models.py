from __future__ import unicode_literals
from decimal import * 
from django.db import models
from django.contrib.auth.models import User
import backend.models as backend

# Create your models here.

#hold records of forms dispatched to facilities
class ClinicalRequestFormsDispatch(models.Model):
	facility = models.ForeignKey(backend.Facility, on_delete=models.CASCADE)
	ref_number =  models.CharField(max_length=64, null=True)
	dispatched_at = models.DateTimeField()
	dispatched_by = models.ForeignKey(User)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_forms_dispatch'
		verbose_name_plural = 'Forms Dispatch'


#hold the form numbers
class ClinicalRequestForm(models.Model):
	form_number = models.CharField(max_length=128, unique=True)
	dispatch = models.ForeignKey(ClinicalRequestFormsDispatch, on_delete=models.CASCADE, null=True)
	received_back = models.BooleanField(default=False)
	
	class Meta:
		db_table = 'vl_forms'
		verbose_name_plural = 'Forms'

class Clinician(models.Model):
	facility = models.ForeignKey(backend.Facility)
	cname = models.CharField(max_length=128)
	cphone = models.CharField(max_length=64, null=True, blank=True)
	class Meta:
		db_table = 'vl_clinicians'
		unique_together = ('facility', 'cname')

class LabTech(models.Model):
	facility = models.ForeignKey(backend.Facility)
	lname = models.CharField(max_length=128)
	lphone = models.CharField(max_length=64, null=True, blank=True)
	class Meta:
		db_table = 'vl_lab_techs'
		unique_together = ('facility', 'lname')	

#hold patient records that later on link to the samples
class Patient(models.Model):
	GENDER_CHOICES = (
		('M', 'Male'),
		('F', 'Female'),
		('X', 'Missing Gender'),
		('L', 'Left Blank')
	)
	unique_id = models.CharField(max_length=128)
	name = models.CharField(max_length=128,null=True, blank=True)
	hep_number = models.CharField(max_length=64, null=True, blank=True)
	other_id = models.CharField(max_length=64, null=True, blank=True)
	gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
	dob = models.DateField(null=True, blank=True)
	created_by = models.ForeignKey(User)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_patients'

class PatientPhone(models.Model):
	patient = models.ForeignKey(Patient)
	phone = models.CharField(max_length=16, null=True, blank=True)

	class Meta:
		db_table = 'vl_patient_phones'


class Envelope(models.Model):
	envelope_number = models.CharField(max_length=10)
	stage = models.PositiveSmallIntegerField(choices=((1,'not_verified'), (2, 'verified'), (3, 'in_worksheet')), default=1)
	sample_type = models.CharField(max_length=1, choices=( ('P', 'Plasma'), ('D', 'DBS') ), default='')
	sample_medical_lab = models.ForeignKey(backend.MedicalLab,related_name='sample_medical_lab', default=1)
	created_at = models.DateTimeField(auto_now_add=True)

	# def __init__(self):
	# 	return self.envelope_number

	class Meta:
		db_table = 'vl_envelopes'

class PreliminaryFindings(models.Model):
	YES_NO_CHOICES = ( ('Y', 'Yes'), ('N', 'No'), ('L', 'Left Blank') )
	POSITIVE_NEGATIVE = ( (1, 'Positive'), (2, 'Negative') )
	WHETHER_COINFECTED_HIV = ((1,'HBV/HIV'))
	patient = models.ForeignKey(Patient)
	hbeag_results = models.PositiveSmallIntegerField(choices=POSITIVE_NEGATIVE, null=True, blank=True)
	hiv_coinfected = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True, blank=True)
	hiv_hcv_coinfected = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True, blank=True)
	hiv_hcv_tb_coinfected = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True, blank=True)
	hep_other_coinfections = models.CharField(max_length=128,null=True, blank=True)
	alt_value_1 = models.DecimalField(max_digits=5, decimal_places = 2, null=True, blank=True)
	alt_value_2 = models.DecimalField(max_digits=5, decimal_places = 2, null=True, blank=True)
	alt_value_3 = models.DecimalField(max_digits=5, decimal_places = 2, null=True, blank=True)
	ast_value_1 = models.DecimalField(max_digits=5, decimal_places = 2, null=True, blank=True)
	ast_value_2 = models.DecimalField(max_digits=5, decimal_places = 2, null=True, blank=True)
	ast_value_3 = models.DecimalField(max_digits=5, decimal_places = 2, null=True, blank=True)
	alt_value_normal_range = models.CharField(max_length=128,null=True, blank=True)
	platelet_count = models.DecimalField(max_digits=5, decimal_places = 2, null=True, blank=True)
	platelet_normal_range = models.CharField(max_length=128,null=True, blank=True)
	ast_value_normal_range = models.CharField(max_length=128,null=True, blank=True)
	fetal_protein_value = models.DecimalField(max_digits=5, decimal_places = 2, null=True, blank=True)
	fetal_protein_value_normal_range = models.CharField(max_length=128,null=True, blank=True)
	prem_other_findings= models.CharField(max_length=128,null=True, blank=True)
	ast_plt_ratio_greater_than_2 = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True, blank=True)
	serum_creatinine = models.DecimalField(max_digits=5, decimal_places = 2, null=True, blank=True)
	serum_creatinine_normal_range = models.CharField(max_length=128,null=True, blank=True)

	class Meta:
		db_table = 'vl_patient_preliminary_findings'

class PatientTreatmentIndication(models.Model):
	patient = models.ForeignKey(Patient)
	treatment_indication = models.ForeignKey(backend.Appendix, related_name='treatment_indication', null=True, blank=True)

	class Meta:
		db_table = 'vl_patient_treatment_indication'

class Sample(models.Model):
	YES_NO_CHOICES = ( ('Y', 'Yes'), ('N', 'No'), ('L', 'Left Blank') )
	SAMPLE_TYPES = ( ('P', 'Plasma'), ('D', 'DBS') )
	DRUG_NAMES = ( (1, 'Tenofovir'), (2, 'Entecavir') )
	TX_DURATION_CHOICES = ( (1, '6 months -< 1yr'), (2, '1 -< 2yrs'), (3, '2 -< 5yrs'), (4, '5yrs and above'), (5, 'Left Blank') )
	WHO_STAGES = ((1, 'I'), (2, 'II'), (3, 'III'), (4, 'IV'))
	TX_CARE_APPROACHES = ((1, 'FBIM'), (2, 'FBG'), (3, 'FTDR'), (4, 'CDDP'), (5, 'CCLAD'))
	INDICATION_FOR_VL = ( (1, 'Routing Monitoring'), (2, 'Treatment Initiation') )
	patient = models.ForeignKey(Patient)
	patient_unique_id = models.CharField(max_length=128)
	locator_category = models.CharField(max_length=1, choices=( ('V', 'V'), ('R', 'R') ))
	envelope = models.ForeignKey(Envelope)
	locator_position = models.CharField(max_length=4)
	vl_sample_id = models.CharField(max_length=128, unique=True, null=True, blank=True)
	form_number = models.CharField(max_length=64, unique=True)
	facility = models.ForeignKey(backend.Facility)
	current_regimen = models.ForeignKey(backend.Appendix, related_name='current_regimen', null=True, blank=True)
	other_regimen = models.CharField(max_length=128, null=True, blank=True)
	anc_number = models.CharField(max_length=64, null=True, blank=True) #anc number for pregnant women	
	active_tb_status = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True, blank=True)
	treatment_duration = models.PositiveSmallIntegerField(choices=TX_DURATION_CHOICES, null=True, blank=True)	
	is_study_sample = models.BooleanField(default=False)
	current_who_stage = models.PositiveSmallIntegerField(choices=WHO_STAGES, null=True, blank=True)
	viral_load_testing = models.ForeignKey(backend.Appendix, related_name='viral_load_testing',null=True, blank=True)
	treatment_indication_other = models.CharField(max_length=64, null=True, blank=True)
	treatment_line = models.ForeignKey(backend.Appendix, related_name='treatment_line',null=True, blank=True)
	failure_reason = models.ForeignKey(backend.Appendix, related_name='failure_reason', null=True, blank=True)
	tb_treatment_phase = models.ForeignKey(backend.Appendix, related_name='tb_treatment_phase', null=True, blank=True)
	arv_adherence = models.ForeignKey(backend.Appendix, related_name='arv_adherence', null=True, blank=True)
	treatment_care_approach = models.PositiveSmallIntegerField(choices=TX_CARE_APPROACHES, null=True, blank=True)
	lab_tech = models.ForeignKey(LabTech, null=True, blank=True)
	
	verified = models.BooleanField(default=False)
	in_worksheet = models.BooleanField(default=False)
	created_by = models.ForeignKey(User, related_name='created_by')
	updated_by = models.ForeignKey(User, related_name='updated_by', null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	clinician_request_date = models.DateField(null=True)
	is_patient_on_treatment = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True, blank=True)
	treatment_initiation_date = models.DateField(null=True, blank=True)
	current_drug_name = models.PositiveSmallIntegerField(choices=DRUG_NAMES, null=True, blank=True)
	pregnant = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True, blank=True)
	breast_feeding = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True, blank=True)
	reason_for_vl = models.PositiveSmallIntegerField(choices=INDICATION_FOR_VL, null=True, blank=True)
	last_test_date = models.DateField(null=True, blank=True)
	last_value = models.CharField(max_length=64, null=True, blank=True)
	last_sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES, null=True, blank=True)
	clinician = models.ForeignKey(Clinician, null=True, blank=True)
	date_collected = models.DateField(null=True, blank=True)
	date_received = models.DateField()
	sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES)
	def __str__(self):
		return self.form_number
	
	class Meta:
		db_table = 'vl_samples'
		unique_together = ('locator_category', 'envelope', 'locator_position')

class DrugResistanceRequest(models.Model):
	sample = models.OneToOneField(Sample, on_delete=models.CASCADE)
	body_weight = models.PositiveSmallIntegerField(null=True, blank=True)
	patient_on_rifampicin = models.CharField(max_length=1, choices=( ('Y', 'Yes'), ('N', 'No'),), null=True, blank=True)

	class Meta:
		db_table = 'vl_drug_resistance_requests'

class PastRegimens(models.Model):
	drug_resistance_request = models.ForeignKey(DrugResistanceRequest, on_delete=models.CASCADE)
	regimen =  models.ForeignKey(backend.Appendix)
	start_date = models.DateField(null=True, blank=True)
	stop_date = models.DateField(null=True, blank=True)

	class Meta:
		db_table = 'vl_past_regimens'

class DrugResistanceResults(models.Model):
	drug_resistance_request = models.ForeignKey(DrugResistanceRequest, on_delete=models.CASCADE)
	results_file = models.FileField(upload_to='drug_resistance_results')
	upload_date = models.DateTimeField(auto_now_add=True)
	drr_uploaded_by = models.ForeignKey(User, related_name='drr_uploaded_by')

	class Meta:
		db_table = 'vl_drug_resistance_results'

class Verification(models.Model):
	sample = models.OneToOneField(Sample, on_delete=models.CASCADE)
	accepted = models.BooleanField(default=False)
	rejection_reason = models.ForeignKey(backend.Appendix, null=True, blank=True)
	comments = models.CharField(max_length=128, null=True, blank=True)
	verified_by = models.ForeignKey(User, related_name='verified_by')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_verifications'
		
class VerificationRejectionReason(models.Model):
	sample = models.ForeignKey(Sample)
	rejection_reason = models.ForeignKey(backend.Appendix, null=True)

	class Meta:
		db_table = 'vl_verification_rejection_reasons'

#track sample sample printing and dispatch
class RejectedSamplesRelease(models.Model):
	sample = models.OneToOneField(Sample, on_delete=models.CASCADE)
	released = models.BooleanField(default=False)
	reject_released_by = models.ForeignKey(User, related_name='reject_released_by', null=True)
	released_at = models.DateTimeField(null=True)
	comments = models.TextField(null=True)

	class Meta:
		db_table = 'vl_rejected_samples_release'