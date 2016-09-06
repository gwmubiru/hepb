import datetime
from django import forms

from backend.models import Appendix, Facility
from .models import *
from home import utils

def appendix_field(category, required=True):
		queryset = Appendix.objects.filter(
						appendix_category_id=category
						)
		attrs = utils.ATTRS if required else utils.ATTRS_OPTIONAL
		widget = forms.Select(attrs=attrs)
		return forms.ModelChoiceField(queryset=queryset, widget=widget, required=required)


class PatientForm(forms.ModelForm):
	class Meta:
		model = Patient

		fields = ('art_number', 'other_id', 'gender', 'dob',)

		widgets = {
			'art_number': forms.TextInput(attrs=utils.ATTRS),
			'other_id': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'gender': forms.Select(attrs=utils.ATTRS2),
			'dob': forms.DateInput(attrs=utils.ATTRS_DATE),
		}

	# unique_id = models.CharField(max_length=128, unique=True)
	# art_number = models.CharField(max_length=64)
	# other_id = models.CharField(max_length=64, null=True)
	# gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
	# dob = models.DateField(null=True)
	# created_by = models.ForeignKey(User)
	# created_at = models.DateTimeField(auto_now_add=True)
	# updated_at = models.DateTimeField(auto_now=True)

class EnvelopeForm(forms.ModelForm):
	class Meta:
		model = Envelope

		fields = ('envelope_number',)

		widgets = {
			'envelope_number': forms.TextInput(
				attrs={'class':'form-control input-sm', 'size': '14', 'required':'true'}
				),
		}

class PatientPhoneForm(forms.ModelForm):
	class Meta:
		model = PatientPhone

		fields = ('phone',)

		widgets = {
			'phone': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
		}
		

class SampleForm(forms.ModelForm):

	#facility = Facility.objects.values('id', 'facility').filter(active=True)	
	current_regimen = appendix_field(3)
	treatment_indication = appendix_field(6, False)
	treatment_line = appendix_field(7) 
	failure_reason = appendix_field(2, False)
	viral_load_testing = appendix_field(8)
	tb_treatment_phase = appendix_field(5, False)
	arv_adherence = appendix_field(1, False)

	class Meta:
		model = Sample

		fields = (
			'locator_category',
			'locator_position',
			'form_number',
			'facility',
			'current_regimen',
			'pregnant',
			'anc_number',
			'breast_feeding',
			'active_tb_status',
			'date_collected',
			'date_received',
			'treatment_inlast_sixmonths',
			'treatment_initiation_date',
			'sample_type',
			'viral_load_testing',
			'treatment_indication',
			'treatment_indication_other',
			'treatment_line',
			'failure_reason',
			'tb_treatment_phase',
			'arv_adherence',
			'routine_monitoring',
			'routine_monitoring_last_test_date',
			'routine_monitoring_last_value',
			'routine_monitoring_last_sample_type',
			'repeat_testing',
			'repeat_testing_last_test_date',
			'repeat_testing_last_value',
			'repeat_testing_last_sample_type',
			'suspected_treatment_failure',
			'suspected_treatment_failure_last_test_date',
			'suspected_treatment_failure_last_value',
			'suspected_treatment_failure_last_sample_type',
			)

		widgets = {
			'locator_category': forms.Select(attrs=utils.ATTRS2),
			'locator_position': forms.TextInput(
				attrs={'class':'form-control input-sm', 'size': '4', 'required':'true'}
				),
			'form_number': forms.TextInput(attrs=utils.ATTRS),
			'facility': forms.Select(attrs=utils.ATTRS),
			'pregnant': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'anc_number': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'breast_feeding': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'active_tb_status': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'date_collected': forms.DateInput(attrs=utils.ATTRS_DATE),
			'date_received': forms.DateInput(attrs=utils.ATTRS_DATE),
			'treatment_inlast_sixmonths': forms.Select(attrs=utils.ATTRS2),
			'treatment_initiation_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'sample_type': forms.Select(attrs=utils.ATTRS2),
			'treatment_indication_other': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			
			'routine_monitoring_last_test_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'routine_monitoring_last_value': forms.TextInput(attrs=utils.ATTRS2_OPTIONAL),
			'routine_monitoring_last_sample_type': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			
			'repeat_testing_last_test_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'repeat_testing_last_value': forms.TextInput(attrs=utils.ATTRS2_OPTIONAL),
			'repeat_testing_last_sample_type':forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			
			'suspected_treatment_failure_last_test_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'suspected_treatment_failure_last_value': forms.TextInput(attrs=utils.ATTRS2_OPTIONAL),
			'suspected_treatment_failure_last_sample_type': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			}

		VL_DATE = "Last VL Date"
		VL_VALUE = "Value"
		VL_SAMPLETYPE = "Sample Type"

		labels = {
			'routine_monitoring_last_test_date': VL_DATE,
			'routine_monitoring_last_value': VL_VALUE,
			'routine_monitoring_last_sample_type': VL_SAMPLETYPE,
			'repeat_testing_last_test_date': VL_DATE,
			'repeat_testing_last_value': VL_VALUE,
			'repeat_testing_last_sample_type': VL_SAMPLETYPE,
			'suspected_treatment_failure_last_test_date': VL_DATE,
			'suspected_treatment_failure_last_value': VL_VALUE,
			'suspected_treatment_failure_last_sample_type': VL_SAMPLETYPE,
			}
		

	# patient = models.ForeignKey(Patient)
	# patient_unique_id = models.CharField(max_length=128)
	# locator_category = models.CharField(max_length=1, choices=( ('V', 'V'), ('R', 'R') ))
	# envelope = models.ForeignKey(Envelope)
	# locator_position = models.CharField(max_length=3)
	# vl_sample_id = models.CharField(max_length=128)
	# form_number = models.CharField(max_length=64)
	# facility = models.ForeignKey(backend.Facility)
	# current_regimen = models.ForeignKey(backend.Appendix, related_name='current_regimen')
	# pregnant = models.CharField(max_length=1, choices=YES_NO_CHOICES)
	# anc_number = models.CharField(max_length=64, null=True) #anc number for pregnant women
	# breast_feeding = models.CharField(max_length=1, choices=YES_NO_CHOICES)
	# active_tb_status = models.CharField(max_length=1, choices=YES_NO_CHOICES, null=True)
	# date_collected = models.DateField(null=True) #Date on which the sample was collected from the patient
	# date_received = models.DateField() #Date received at CPHL
	# treatment_inlast_sixmonths = models.CharField(max_length=1, choices=YES_NO_CHOICES)
	# treatment_initiation_date = models.DateField(null=True)
	# sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES)
	# viral_load_testing = models.ForeignKey(backend.Appendix, related_name='viral_load_testing')
	# treatment_indication = models.ForeignKey(backend.Appendix, related_name='treatment_indication', null=True)
	# treatment_indication_other = models.CharField(max_length=64, null=True)
	# treatment_line = models.ForeignKey(backend.Appendix, related_name='treatment_line')
	# failure_reason = models.ForeignKey(backend.Appendix, related_name='failure_reason', null=True)
	# tb_treatment_phase = models.ForeignKey(backend.Appendix, related_name='tb_treatment_phase', null=True)
	# arv_adherence = models.ForeignKey(backend.Appendix, related_name='arv_adherence', null=True)
	# routine_monitoring = models.BooleanField(default=False)
	# routine_monitoring_last_test_date = models.DateField(null=True)
	# routine_monitoring_last_value = models.CharField(max_length=64, null=True)
	# routine_monitoring_last_sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES, null=True)
	# repeat_testing = models.BooleanField(default=False)
	# repeat_testing_last_test_date = models.DateField(null=True)
	# repeat_testing_last_value = models.CharField(max_length=64, null=True)
	# repeat_testing_last_sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES, null=True)
	
	# suspected_treatment_failure = models.BooleanField(default=False)
	# suspected_treatment_failure_last_test_date = models.DateField(null=True)
	# suspected_treatment_failure_last_value = models.CharField(max_length=64, null=True)
	# suspected_treatment_failure_last_sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES, null=True)
	
	# verified = models.BooleanField(default=False)
	# in_worksheet = models.BooleanField(default=False)
	# printed = models.BooleanField(default=False)
	# dispatched = models.BooleanField(default=False)
	# created_by = models.ForeignKey(User, related_name='created_by')
	# updated_by = models.ForeignKey(User, related_name='updated_by', null=True)
	# created_at = models.DateTimeField(auto_now_add=True)
	# updated_at = models.DateTimeField(auto_now=True)
	
	
		