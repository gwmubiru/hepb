from django import forms

from .models import Worksheet
from samples.models import Sample
from home import utils


class WorksheetForm(forms.ModelForm):
	class Meta:
		model = Worksheet
		fields = (
			'worksheet_reference_number',
			'machine_type',
			'sample_type',
			'sample_prep',
			'sample_prep_expiry_date',
			'bulk_lysis_buffer',
			'bulk_lysis_buffer_expiry_date',
			'control',
			'control_expiry_date',
			'calibrator',
			'calibrator_expiry_date',
			'include_calibrators',
			'amplication_kit',
			'amplication_kit_expiry_date',
			'assay_date',
		)

		attrs = {'class':'form-control input-sm w-md', 'required':'true'}
		attrs2 = {'class':'form-control input-sm w-xs', 'required':'true'}
		attrs_date = {'class':'form-control input-sm w-sm date'}

		widgets = {
			'worksheet_reference_number': forms.TextInput(attrs=attrs),
			'machine_type': forms.Select(attrs=attrs2),
			'sample_type': forms.Select(attrs=attrs2),
			'sample_prep': forms.TextInput(attrs=attrs),
			'sample_prep_expiry_date': forms.DateInput(attrs=attrs_date),
			'bulk_lysis_buffer': forms.TextInput(attrs=attrs),
			'bulk_lysis_buffer_expiry_date': forms.DateInput(attrs=attrs_date),
			'control': forms.TextInput(attrs=attrs),
			'control_expiry_date': forms.DateInput(attrs=attrs_date),
			'calibrator': forms.TextInput(attrs=attrs),
			'calibrator_expiry_date': forms.DateInput(attrs=attrs_date),
			'amplication_kit': forms.TextInput(attrs=attrs),
			'amplication_kit_expiry_date': forms.DateInput(attrs=attrs_date),
			'assay_date': forms.DateInput(attrs=attrs_date),
		}

class AttachSamplesForm(forms.ModelForm):
	samples = forms.ModelMultipleChoiceField(
					queryset=Sample.objects.values('id','form_number').filter(
						verified=True, 
						in_worksheet=False).order_by('created_at')[:80],
					widget=forms.CheckboxSelectMultiple())
	class Meta:
		model = Worksheet
		fields = ('samples',)