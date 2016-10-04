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
			'last_test_date',
			'last_value',
			'last_sample_type',
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
			
			'last_test_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'last_value': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'last_sample_type': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			}

		VL_DATE = "Last VL Date"
		VL_VALUE = "Value"
		VL_SAMPLETYPE = "Sample Type"

		labels = {
			'last_test_date': "Last VL Date",
			'last_value': "Value",
			'last_sample_type': "Sample Type",
			}