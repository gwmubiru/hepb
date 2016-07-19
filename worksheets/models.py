from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

import samples.models as samples

# Create your models here.
class Worksheet(models.Model):
	MACHINE_TYPES = ( ('A', 'Abott'), ('R', 'Roche') )
	SAMPLE_TYPES = ( ('P', 'Plasma'), ('D', 'DBS') )
	worksheet_reference_number = models.CharField(max_length=128)
	machine_type = models.CharField(max_length=1, choices=MACHINE_TYPES)
	worksheet_type = models.CharField(max_length=1, choices=SAMPLE_TYPES)
	sample_prep = models.CharField(max_length=64)
	sample_prep_expiry_date = models.DateField()
	bulk_lysis_buffer = models.CharField(max_length=64)
	bulk_lysis_buffer_expiry_date = models.DateField()
	control = models.CharField(max_length=64)
	control_expiry_date = models.DateField()
	calibrator = models.CharField(max_length=64)
	calibrator_expiry_date = models.DateField()
	include_calibrators = models.BooleanField(default=False)
	amplication_kit = models.CharField(max_length=64)
	amplication_kit_expiry_date = models.DateField()
	assay_date = models.DateField()
	generated_by = models.ForeignKey(User, related_name='generated_by')
	worksheet_updated_by = models.ForeignKey(User, related_name='worksheet_updated_by')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_worksheets'


class WorksheetSample(models.Model):
	worksheet = models.ForeignKey(Worksheet)
	sample = models.ForeignKey(samples.Sample)
	attached_by = models.ForeignKey(User, related_name='attached_by')
	created_at = models.DateTimeField(auto_now_add=True)	

	class Meta:
		db_table = 'vl_worksheet_samples'	