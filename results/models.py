from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

import samples.models as samples
import backend.models as backend
import worksheets.models as worksheets

# Create your models here.

#hold results for each sample
class FinalResult(models.Model):
	RESULT_CHOICES = ( (1, 'Suppressed'),(2, 'Unsuppressed'), (3, 'Failed') )
	sample = models.ForeignKey(samples.Sample)
	valid = models.BooleanField(default=False)
	final_result = models.PositiveSmallIntegerField(choices=RESULT_CHOICES)
	failure_reason = models.ForeignKey(backend.Appendix)
	result_numeric = models.IntegerField()
	result_alphanumeric = models.TextField()
	test_date = models.DateTimeField()
	test_by = models.ForeignKey(User, related_name='test_by')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_final_results'


#handle repeats of samples
class Repeat(models.Model):
	sample = models.ForeignKey(samples.Sample)
	repeat_test = models.BooleanField(default=False)
	result1 = models.TextField()
	result2 = models.TextField()
	result3 = models.TextField()
	result4 = models.TextField()
	result5 = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_sample_repeats'
	

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
	results_file = models.FileField(upload_to='uploads/results/')
	upload_date = models.DateTimeField()
	uploaded_by = models.ForeignKey(User, related_name='uploaded_by')

	class Meta:
		db_table = 'vl_worksheet_results_uploads'


#track worksheets whose results have been printed
class WorksheetResultsPrinting(models.Model):
	worksheet = models.ForeignKey(worksheets.Worksheet)
	print_date = models.DateTimeField()
	printed_by = models.ForeignKey(User, related_name='printed_by')

	class Meta:
		db_table = 'vl_worksheet_results_printing'		