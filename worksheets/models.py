from __future__ import unicode_literals

from django.db import models

from django.contrib.auth.models import User

from samples.models import Sample,SampleIdentifier,Envelope

import backend.models as backend


MACHINE_TYPES = (('A', 'Abbott'), ('R', 'Roche CAP/CTM'), ('C', 'Cobas 8800'), ('H', 'Hologic'),('A', 'Alinity'),('S', 'Cobas 6800'))
STAGE_CHOICES = ((11, 'awaiting_elution'),(12, 'awaiting_loading'),(1, 'awaiting_results'),(2, 'has_results'), (3, 'passed_lab_qc'), (4, 'passed_data_qc'),(5, 'completed'),(6, 'recalled'),(7, 'rejected'),(8, 'ignored'))
RUN_STAGES = ((1, 'awaiting_authorization'),(2, 'Authorization_complete'), (3, 'Release_complete'))

class Worksheet(models.Model):
	
	samples = models.ManyToManyField(Sample, through='WorksheetSample')
	id = models.AutoField(primary_key=True)
	worksheet_reference_number = models.CharField(max_length=128,null=True, blank=True)
	machine_type = models.CharField(max_length=1, choices=MACHINE_TYPES)
	sample_type = models.CharField(max_length=1, choices=Sample.SAMPLE_TYPES)
	sample_prep = models.CharField(max_length=64,null=True, blank=True)
	sample_prep_expiry_date = models.DateField(null=True, blank=True)
	eluted_pippeted_at = models.CharField(max_length=64, null=True, blank=True)
	loaded_at = models.CharField(max_length=64, null=True, blank=True)
	bulk_lysis_buffer = models.CharField(max_length=64, null=True, blank=True)
	bulk_lysis_buffer_expiry_date = models.DateField(null=True, blank=True)
	control = models.CharField(max_length=64, null=True, blank=True)
	control_expiry_date = models.DateField(null=True, blank=True)
	calibrator = models.CharField(max_length=64, null=True, blank=True)
	calibrator_expiry_date = models.DateField(null=True, blank=True)
	include_calibrators = models.BooleanField(default=False)
	amplication_kit = models.CharField(max_length=64, null=True, blank=True)
	starting_locator_id = models.CharField(max_length=64, null=True, blank=True)
	ending_locator_id = models.CharField(max_length=64, null=True, blank=True)
	amplication_kit_expiry_date = models.DateField(null=True, blank=True)
	assay_date = models.DateTimeField()
	eluted_by = models.ForeignKey(User, related_name='eluted_by',on_delete=models.CASCADE)
	loaded_by = models.ForeignKey(User, related_name='loaded_by',on_delete=models.CASCADE)
	is_repeat = models.PositiveSmallIntegerField(default=0)	
	generated_by = models.ForeignKey(User, related_name='generated_by',on_delete=models.CASCADE)
	worksheet_updated_by = models.ForeignKey(User, related_name='worksheet_updated_by', null=True,on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	stage = models.PositiveSmallIntegerField(choices=STAGE_CHOICES, default=12)
	worksheet_medical_lab = models.ForeignKey(backend.MedicalLab, related_name='worksheet_medical_lab', default=1,on_delete=models.CASCADE)

	class Meta:
		db_table = 'vl_worksheets'

class ResultRun(models.Model):
	id = models.AutoField(primary_key=True)
	reference_number = models.CharField(max_length=128, null=True)
	file_name = models.FileField(upload_to='results')
	disc_file_name = models.CharField(max_length=100, null=True)
	samples_with_more_than_thou_copies = models.IntegerField(default=0)
	has_squential_samples_with_more_than_thou_copies = models.PositiveSmallIntegerField(default=0)
	upload_date = models.DateTimeField(auto_now_add=True)
	stage = models.PositiveSmallIntegerField(choices=RUN_STAGES, default=1)
	run_uploaded_by = models.ForeignKey(User, related_name='run_uploaded_by',on_delete=models.CASCADE)
	low_positive_ctrl = models.CharField(max_length=100, null=True)
	high_positive_ctrl = models.CharField(max_length=100, null=True)	
	negative_ctrl = models.CharField(max_length=100, null=True)
	serial_number = models.CharField(max_length=100, null=True)
	reagent_lot = models.CharField(max_length=100, null=True)
	reagent_expiry_date = models.DateField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		db_table = 'vl_result_runs'	

#Attaching samples to work sheet
class ResultRunDetail(models.Model):
	id = models.AutoField(primary_key=True)
	the_result_run = models.ForeignKey(ResultRun, related_name='the_run', on_delete=models.CASCADE,null=True, blank=True)
	result_run_position = models.PositiveSmallIntegerField(null=True, blank=True)
	status = models.PositiveSmallIntegerField(choices=STAGE_CHOICES, default=1)	
	suppressed = models.PositiveSmallIntegerField(default=0)
	testing_by = models.ForeignKey(User, related_name='testing_by', null=True,on_delete=models.CASCADE)
	result_alphanumeric = models.TextField()
	instrument_id = models.CharField(max_length=64)
	result_numeric = models.IntegerField(null=True, blank=True)
	test_date = models.DateTimeField(null=True, blank=True) 
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_result_run_details'

#Attaching samples to work sheet
class WorksheetSample(models.Model):
	worksheet = models.ForeignKey(Worksheet, on_delete=models.CASCADE,null=True, blank=True)
	id = models.AutoField(primary_key=True)
	sample = models.ForeignKey(Sample, on_delete=models.CASCADE,null=True, blank=True)
	sample_identifier = models.ForeignKey(SampleIdentifier,related_name='sample_identifier', on_delete=models.CASCADE,null=True, blank=True)
	result_run_detail = models.OneToOneField(ResultRunDetail,related_name='result_run_detail', on_delete=models.CASCADE)
	result_run_position = models.PositiveSmallIntegerField(null=True, blank=True)
	stage = models.PositiveSmallIntegerField(choices=STAGE_CHOICES, default=1)
	is_diluted = models.PositiveSmallIntegerField(choices=STAGE_CHOICES, default=0)
	repeat_test = models.PositiveSmallIntegerField(null=True)
	sample_run = models.PositiveSmallIntegerField(default=1)	
	suppressed = models.PositiveSmallIntegerField(default=0)
	has_low_level_viramia = models.PositiveSmallIntegerField(null=True,choices=( (1, 'YES'),(2, 'NO'),(3, 'Failed')))
	tester = models.ForeignKey(User, related_name='tester', null=True,on_delete=models.CASCADE)
	result_alphanumeric = models.TextField()
	failure_reason = models.TextField(null=True)
	method = models.CharField(max_length=1, null=True,blank=True)
	instrument_id = models.CharField(max_length=64)
	other_instrument_id = models.CharField(max_length=64)
	rack_id = models.CharField(max_length=64, null=True, blank=True)
	result_numeric = models.IntegerField(null=True, blank=True)
	test_date = models.DateTimeField(null=True, blank=True) 
	authorised = models.BooleanField(default=False)
	authoriser = models.ForeignKey(User, related_name='authoriser', null=True,on_delete=models.CASCADE)
	authorised_at = models.DateTimeField(null=True)
	supression_cut_off_id = models.PositiveIntegerField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	def has_sample(self):
		hasattr(self, 'sample') and self.sample is not None

	class Meta:
		db_table = 'vl_worksheet_samples'

class WorksheetEnvelope(models.Model):
	id = models.AutoField(primary_key=True)
	worksheet = models.ForeignKey(Worksheet, on_delete=models.CASCADE,null=True, blank=True)
	envelope = models.ForeignKey(Envelope, on_delete=models.CASCADE,null=True, blank=True)
	the_creator = models.ForeignKey(User, related_name='the_creator',on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	class Meta:
		db_table = 'vl_worksheet_envelopes'
		unique_together = ('worksheet', 'envelope',)


class WorksheetPrinting(models.Model):
	worksheet = models.OneToOneField(Worksheet, on_delete=models.CASCADE)
	id = models.AutoField(primary_key=True)
	worksheet_printed_by = models.ForeignKey(User, related_name='worksheet_printed_by',on_delete=models.CASCADE)
	printed_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_worksheet_printing'


