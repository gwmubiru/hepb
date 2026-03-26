from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

import samples.models as samples
import backend.models as backend
import worksheets.models as worksheets

# Create your models here.

#track
class Result(models.Model):
	METHOD_CHOICES = (
						('A', 'Abbott Real time HIV-1 PCR'),
						('R', 'HIV-1 RNA PCR Roche'),
						('C', 'HIV-1 RNA PCR Roche'),
						('H', 'HIV-1 RNA PCR Panther'),
						('N', 'HIV-1 RNA PCR Alinity')
					)
	id = models.AutoField(primary_key=True)
	sample = models.OneToOneField(samples.Sample, on_delete=models.CASCADE)
	repeat_test = models.PositiveSmallIntegerField(default=2,choices=( (1, 'YES'),(2, 'NO'), (3, 'PROPOSED') ))
	result1 = models.TextField()
	result2 = models.TextField()
	result3 = models.TextField()
	result4 = models.TextField()
	result5 = models.TextField()

	suppressed = models.PositiveSmallIntegerField(default=3,choices=( (1, 'YES'),(2, 'NO'), (3, 'UNKNOWN') ))
	has_low_level_viramia = models.PositiveSmallIntegerField(default=3,choices=( (1, 'YES'),(2, 'NO'),(3, 'Failed')))
	result_numeric = models.IntegerField(null=True)
	worksheet_sample = models.OneToOneField(worksheets.WorksheetSample, on_delete=models.CASCADE)
	result_alphanumeric = models.TextField()
	failure_reason = models.TextField(null=True)
	method = models.CharField(max_length=1, null=True, choices=METHOD_CHOICES)
	result_upload_date = models.DateTimeField(null=True)
	test_date = models.DateTimeField(null=True)
	supression_cut_off = models.ForeignKey(backend.Appendix, related_name='supression_cut_off',null=True, blank=True, on_delete=models.CASCADE)
	test_by = models.ForeignKey(User,null=True, related_name='test_by',on_delete=models.CASCADE)

	authorised = models.BooleanField(default=False)
	authorised_by = models.ForeignKey(User, related_name='authorised_by', null=True,on_delete=models.CASCADE)
	authorised_at = models.DateTimeField(null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.sample.form_number

	class Meta:
		db_table = 'vl_results'


#track sample sample printing and dispatch
class ResultsQC(models.Model):
	id = models.AutoField(primary_key=True)
	result = models.OneToOneField(Result, on_delete=models.CASCADE)
	released = models.BooleanField(default=False)
	released_by = models.ForeignKey(User, related_name='released_by', null=True,on_delete=models.CASCADE)
	dr_reviewed_by = models.ForeignKey(User, related_name='dr_reviewed_by', null=True,on_delete=models.CASCADE)
	dr_reviewed_at = models.DateTimeField(null=True)
	released_at = models.DateTimeField(null=True)
	qc_date = models.DateTimeField(null=True)
	is_reviewed_for_dr = models.PositiveSmallIntegerField(default=0,choices=( (1, 'YES'),(0, 'NO')))
	comments = models.TextField(null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_results_qc'

class ResultsDispatch(models.Model):
	id = models.AutoField(primary_key=True)
	sample = models.OneToOneField(samples.Sample, on_delete=models.CASCADE)
	dispatch_type = models.CharField(max_length=1, null=True, choices=( ('P', 'Printed'),('D', 'Downloaded') ))
	dispatch_date = models.DateTimeField(null=True)
	dispatched_by = models.CharField(max_length=128, null=True)
	received_at_facility = models.BooleanField(default=False)
	date_received_at_facility = models.DateField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'vl_results_dispatch'

#track worksheets whose results have been uploaded
class WorksheetResultsUpload(models.Model):
	id = models.AutoField(primary_key=True)
	#worksheet = models.ForeignKey(worksheets.Worksheet)
	machine_type = models.CharField(max_length=3, null=True)
	reference_number = models.CharField(max_length=100, null=True)
	results_file = models.FileField(upload_to='results')
	multiplier = models.IntegerField(default=1)
	upload_date = models.DateTimeField(auto_now_add=True)
	uploaded_by = models.ForeignKey(User, related_name='uploaded_by',on_delete=models.CASCADE)

	def clean(self):
		file_name = self.results_file.name
		if self.machine_type == 'R' and file_name.endswith('.csv') is not True:
			raise ValidationError(_("Expecting a csv file"))
		if self.machine_type == 'A' and file_name.endswith('.txt') is not True:
			raise ValidationError(_("Expecting a txt file"))

	class Meta:
		db_table = 'vl_worksheet_results_uploads'

class CobasResultsUpload(models.Model):
	id = models.AutoField(primary_key=True)
	results_file = models.FileField(upload_to='results')
	multiplier = models.IntegerField(default=1)
	upload_date = models.DateTimeField(auto_now_add=True)
	cobas_uploaded_by = models.ForeignKey(User, related_name='cobas_uploaded_by',on_delete=models.CASCADE)

	def clean(self):
		file_name = self.results_file.name
		if file_name.endswith('.csv') is not True and file_name.endswith('.lis') is not True:
			raise ValidationError(_("Expecting a csv file"))

	class Meta:
		db_table = 'vl_cobas_results_uploads'
