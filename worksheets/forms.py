from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import Worksheet
from samples.models import Sample
from home import utils


class WorksheetForm(forms.ModelForm):
	class Meta:
		model = Worksheet
		fields = (
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

		widgets = {
			'machine_type': forms.Select(attrs=utils.ATTRS2),
			'sample_type': forms.Select(attrs=utils.ATTRS2),
			'sample_prep': forms.TextInput(attrs=utils.ATTRS),
			'sample_prep_expiry_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'bulk_lysis_buffer': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'bulk_lysis_buffer_expiry_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'control': forms.TextInput(attrs=utils.ATTRS),
			'control_expiry_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'calibrator': forms.TextInput(attrs=utils.ATTRS),
			'calibrator_expiry_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'amplication_kit': forms.TextInput(attrs=utils.ATTRS),
			'amplication_kit_expiry_date': forms.DateInput(attrs=utils.ATTRS_DATE),
		}

		labels = {
			'control': _('Control lot'),
			'calibrator': _('Calibrator lot'),
			'amplication_kit': _('Amplication kit lot'),
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