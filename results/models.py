from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

import samples.models as samples
import backend.models as backend
import worksheets.models as worksheets

# Create your models here.

#track 
class Result(models.Model):
	RESULT_CHOICES = ( (1, 'Suppressed'),(2, 'Unsuppressed'), (3, 'Failed') )
	METHOD_CHOICES = ( ('A', 'Abbott Real time HIV-1 PCR'), ('R', 'HIV-1 RNA PCR Roche'), ('C', 'HIV-1 RNA PCR Roche'))
	sample = models.OneToOneField(samples.Sample, on_delete=models.CASCADE)
	repeat_test = models.BooleanField(default=False)
	result1 = models.TextField()
	result2 = models.TextField()
	result3 = models.TextField()
	result4 = models.TextField()
	result5 = models.TextField()

	final_result = models.PositiveSmallIntegerField(choices=RESULT_CHOICES)
	result_numeric = models.IntegerField()
	result_alphanumeric = models.TextField()
	method = models.CharField(max_length=1, null=True, choices=METHOD_CHOICES)
	test_date = models.DateTimeField()
	test_by = models.ForeignKey(User, related_name='test_by')

	authorised_by = models.ForeignKey(User, related_name='authorised_by', null=True)
	authorised_at = models.DateTimeField(null=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_results'
	

#track sample sample printing and dispatch
class ResultsPrinting(models.Model):
	result = models.ForeignKey(Result, on_delete=models.CASCADE)
	released = models.BooleanField(default=False)
	released_by = models.ForeignKey(User, related_name='released_by', null=True)
	released_at = models.DateTimeField(null=True)
	comments = models.TextField(null=True)

	printed = models.BooleanField(default=False)
	downloaded = models.BooleanField(default=False)
	print_date = models.DateTimeField(null=True)
	printed_by = models.CharField(max_length=128, null=True)

	class Meta:
		db_table = 'vl_results_printing'


#track worksheets whose results have been uploaded
class WorksheetResultsUpload(models.Model):
	worksheet = models.ForeignKey(worksheets.Worksheet)
	results_file = models.FileField(upload_to='results')
	multiplier = models.IntegerField(default=1)
	upload_date = models.DateTimeField(auto_now_add=True)
	uploaded_by = models.ForeignKey(User, related_name='uploaded_by')

	def clean(self):
		file_name = self.results_file.name		
		if self.worksheet == 'R' and file_name.endswith('.csv') is not True:
			raise ValidationError(_("Expecting a csv file"))
		if self.worksheet == 'A' and file_name.endswith('.txt') is not True:
			raise ValidationError(_("Expecting a txt file"))

	class Meta:
		db_table = 'vl_worksheet_results_uploads'	

class CobasResultsUpload(models.Model):
	reference_number = models.CharField(max_length=128, null=True)
	results_file = models.FileField(upload_to='results')
	multiplier = models.IntegerField(default=1)
	upload_date = models.DateTimeField(auto_now_add=True)
	cobas_uploaded_by = models.ForeignKey(User, related_name='cobas_uploaded_by')

	def clean(self):
		file_name = self.results_file.name		
		if file_name.endswith('.csv') is not True:
			raise ValidationError(_("Expecting a csv file"))

	class Meta:
		db_table = 'vl_cobas_results_uploads'	