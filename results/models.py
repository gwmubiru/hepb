from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

import samples.models as samples
import backend.models as backend
import worksheets.models as worksheets

# Create your models here.

#hold results for each sample
class FinalResult(models.Model):
	RESULT_CHOICES = ( (1, 'Suppressed'),(2, 'Unsuppressed'), (3, 'Failed') )
	METHOD_CHOICES = ( ('A', 'Abbott Real time HIV-1 PCR'), ('R', 'HIV-1 RNA PCR Roche'))
	sample = models.OneToOneField(samples.Sample, on_delete=models.CASCADE)
	valid = models.BooleanField(default=False)
	final_result = models.PositiveSmallIntegerField(choices=RESULT_CHOICES)
	result_numeric = models.IntegerField()
	result_alphanumeric = models.TextField()
	method = models.CharField(max_length=1, null=True, choices=METHOD_CHOICES)
	test_date = models.DateTimeField()
	test_by = models.ForeignKey(User, related_name='test_by')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_final_results'


#track 
class SampleResults(models.Model):
	sample = models.OneToOneField(samples.Sample, on_delete=models.CASCADE)
	repeat_test = models.BooleanField(default=False)
	result1 = models.TextField()
	result2 = models.TextField()
	result3 = models.TextField()
	result4 = models.TextField()
	result5 = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_sample_results'
	

#track sample sample printing and dispatch
class SamplePrintingDispatching(object):
	sample = models.ForeignKey(samples.Sample)
	print_date = models.DateTimeField()
	sample_printed_by = models.ForeignKey(User, related_name='sample_printed_by')
	dispatched = models.BooleanField(default=False)
	dispatch_date = models.DateTimeField()
	sample_dispatched_by = models.ForeignKey(User, related_name='sample_dispatched_by')


#track worksheets whose results have been uploaded
class WorksheetResultsUpload(models.Model):
	worksheet = models.ForeignKey(worksheets.Worksheet)
	results_file = models.FileField(upload_to='results')
	multiplier = models.IntegerField(default=1)
	upload_date = models.DateTimeField(auto_now_add=True)
	uploaded_by = models.ForeignKey(User, related_name='uploaded_by')

	class Meta:
		db_table = 'vl_worksheet_results_uploads'


#track worksheets whose results have been printed
class WorksheetResultsPrinting(models.Model):
	worksheet = models.ForeignKey(worksheets.Worksheet)
	print_date = models.DateTimeField()
	printed_by = models.ForeignKey(User, related_name='printed_by')

	def clean(self):
		file_name = self.results_file.name		
		if self.worksheet == 'R' and file_name.endswith('.csv') is not True:
			raise ValidationError(_("Expecting a csv file"))
		if self.worksheet == 'A' and file_name.endswith('.txt') is not True:
			raise ValidationError(_("Expecting a txt file"))

	class Meta:
		db_table = 'vl_worksheet_results_printing'		