from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

import backend.models as backend

# Create your models here.

#hold records of forms dispatched to facilities
class ClinicalRequestFormsDispatch(models.Model):
	facility = models.ForeignKey(backend.Facility, on_delete=models.CASCADE)
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
	dispatch = models.ForeignKey(ClinicalRequestFormsDispatch, on_delete=models.CASCADE)

	def __init__(self):
		return self.form_number

	class Meta:
		db_table = 'vl_forms'
		verbose_name_plural = 'Forms'


#hold patient records that later on link to the samples
class Patient(models.Model):
	GENDER_CHOICES = (
		('M', 'Male'),
		('F', 'Female'),
		('X', 'Missing Gender'),
	)
	unique_id = models.CharField(max_length=128, unique=True)
	art_number = models.CharField(max_length=64)
	other_id = models.CharField(max_length=64)
	gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
	dob = models.DateField()
	created_by = models.ForeignKey(User)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_patients'

class PatientPhone(models.Model):
	patient = models.ForeignKey(Patient)
	phone = models.CharField(max_length=16)
		

class Sample(models.Model):
	YES_NO_CHOICES = ( ('Y', 'Yes'), ('N', 'No') )
	SAMPLE_TYPES = ( ('P', 'Plasma'), ('D', 'DBS') )
	patient = models.ForeignKey(Patient)
	patient_unique_id = models.CharField(max_length=128)
	locator_category = models.CharField(max_length=1, choices=( ('V', 'V'), ('R', 'R') ))
	locator_envelope = models.CharField(max_length=10)
	locator_position = models.CharField(max_length=3)
	vl_sample_id = models.CharField(max_length=128)
	form_number = models.CharField(max_length=64)
	facility = models.ForeignKey(backend.Facility)
	current_regimen = models.ForeignKey(backend.Appendix, related_name='current_regimen')
	pregnant = models.CharField(max_length=1, choices=YES_NO_CHOICES)
	anc_number = models.CharField(max_length=64) #anc number for pregnant women
	breast_feeding = models.CharField(max_length=1, choices=YES_NO_CHOICES)
	active_tb_status = models.CharField(max_length=1, choices=YES_NO_CHOICES)
	date_collected = models.DateField() #Date on which the sample was collected from the patient
	date_received = models.DateField #Date received at CPHL
	treatment_inlast_sixmonths = models.CharField(max_length=1, choices=YES_NO_CHOICES)
	treatment_initiation_date = models.DateField()
	sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES)
	viral_load_testing = models.ForeignKey(backend.Appendix, related_name='viral_load_testing')
	treatment_indication = models.ForeignKey(backend.Appendix, related_name='treatment_indication')
	treatment_indication_other = models.CharField(max_length=64)
	treatment_line = models.ForeignKey(backend.Appendix, related_name='treatment_line')
	failure_reason = models.ForeignKey(backend.Appendix, related_name='failure_reason')
	tb_treatment_phase = models.ForeignKey(backend.Appendix, related_name='tb_treatment_phase')
	arv_adherence = models.ForeignKey(backend.Appendix, related_name='arv_adherence')
	routine_monitoring = models.BooleanField(default=False)
	routine_monitoring_last_test_date = models.DateField(default=False)
	routine_monitoring_last_value = models.CharField(max_length=64)
	routine_monitoring_last_sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES)
	repeat_testing = models.BooleanField(default=False)
	repeat_testing_last_test_date = models.DateField(default=False)
	repeat_testing_last_value = models.CharField(max_length=64)
	repeat_testing_last_sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES)
	suspected_treatment_failure = models.BooleanField(default=False)
	suspected_treatment_failure_last_test_date = models.DateField(default=False)
	suspected_treatment_failure_last_value = models.CharField(max_length=64)
	suspected_treatment_failure_last_sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES)
	verified = models.BooleanField(default=False)
	created_by = models.ForeignKey(User, related_name='created_by')
	updated_by = models.ForeignKey(User, related_name='updated_by')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_samples'


class Verification(models.Model):
	sample = models.ForeignKey(Sample)
	accepted = models.BooleanField(default=False)
	rejection_reason = models.ForeignKey(backend.Appendix)
	comments = models.CharField(max_length=128)
	verified_by = models.ForeignKey(User, related_name='verified_by')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_verifications'
		
class VerificationRejectionReason(models.Model):
	sample = models.ForeignKey(Sample)
	rejection_reason = models.ForeignKey(backend.Appendix)

	class Meta:
		db_table = 'vl_verification_rejection_reasons'