from __future__ import unicode_literals

from django.db import models

from django.contrib.auth.models import User

from samples.models import Sample

import backend.models as backend

#'awaiting_results','has_results','passed_lab_qc','passed_data_qc'

# Create your models here.
MACHINE_TYPES = ( ('A', 'Abbott'), ('R', 'Roche CAP/CTM'), ('C', 'Cobas 8800') )
STAGE_CHOICES = ( (1, 'awaiting_results'),(2, 'has_results'), (3, 'passed_lab_qc'), (4, 'passed_data_qc') )

class Worksheet(models.Model):
	
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
	stage = models.PositiveSmallIntegerField(choices=STAGE_CHOICES, default=1)
	worksheet_medical_lab = models.ForeignKey(backend.MedicalLab, related_name='worksheet_medical_lab', default=1)

	class Meta:
		db_table = 'vl_worksheets'


#Attaching samples to work sheet
class WorksheetSample(models.Model):
	worksheet = models.ForeignKey(Worksheet, on_delete=models.CASCADE)
	sample = models.ForeignKey(Sample, on_delete=models.CASCADE)
	stage = models.PositiveSmallIntegerField(choices=STAGE_CHOICES, default=1)
	sample_run = models.PositiveSmallIntegerField(default=1)
	instrument_id = models.CharField(max_length=64, null=True, blank=True)
	rack_id = models.CharField(max_length=64, null=True, blank=True)

	class Meta:
		db_table = 'vl_worksheet_samples'


class WorksheetPrinting(models.Model):
	worksheet = models.OneToOneField(Worksheet, on_delete=models.CASCADE)
	worksheet_printed_by = models.ForeignKey(User, related_name='worksheet_printed_by')
	printed_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_worksheet_printing'