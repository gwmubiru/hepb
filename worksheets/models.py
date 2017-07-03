from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

from samples.models import Sample

#'awaiting_results','has_results','passed_lab_qc','passed_data_qc'

# Create your models here.
class Worksheet(models.Model):
	MACHINE_TYPES = ( ('A', 'Abbott'), ('R', 'Roche CAP/CTM'), ('C', 'Cobas 8800') )
	STAGE_CHOICES = ( (1, 'awaiting_results'),(2, 'has_results'), (3, 'passed_lab_qc'), (4, 'passed_data_qc') )
	samples = models.ManyToManyField(Sample, through='WorksheetSample')
	worksheet_reference_number = models.CharField(max_length=128)
	machine_type = models.CharField(max_length=1, choices=MACHINE_TYPES)
	sample_type = models.CharField(max_length=1, choices=Sample.SAMPLE_TYPES)
	sample_prep = models.CharField(max_length=64,null=True, blank=True)
	sample_prep_expiry_date = models.DateField(null=True, blank=True)
	bulk_lysis_buffer = models.CharField(max_length=64, null=True, blank=True)
	bulk_lysis_buffer_expiry_date = models.DateField(null=True, blank=True)
	control = models.CharField(max_length=64, null=True, blank=True)
	control_expiry_date = models.DateField(null=True, blank=True)
	calibrator = models.CharField(max_length=64, null=True, blank=True)
	calibrator_expiry_date = models.DateField(null=True, blank=True)
	include_calibrators = models.BooleanField(default=False)
	amplication_kit = models.CharField(max_length=64, null=True, blank=True)
	amplication_kit_expiry_date = models.DateField(null=True, blank=True)
	assay_date = models.DateTimeField()
	generated_by = models.ForeignKey(User, related_name='generated_by')
	worksheet_updated_by = models.ForeignKey(User, related_name='worksheet_updated_by', null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	stage = models.PositiveSmallIntegerField(choices=MACHINE_TYPES, default=1)

	class Meta:
		db_table = 'vl_worksheets'


#Attaching samples to work sheet
class WorksheetSample(models.Model):
	worksheet = models.ForeignKey(Worksheet, on_delete=models.CASCADE)
	sample = models.ForeignKey(Sample, on_delete=models.CASCADE)
	has_result = models.BooleanField(default=False)
	instrument_id = models.CharField(max_length=64, null=True, blank=True)

	class Meta:
		db_table = 'vl_worksheet_samples'	