from django import forms

from .models import WorksheetResultsUpload,CobasResultsUpload
from home import utils

class UploadForm(forms.ModelForm):
	
	class Meta:
		model = WorksheetResultsUpload
		fields = ('worksheet', 'multiplier', 'results_file',)
		widgets = {
			'worksheet': forms.HiddenInput(),
			'multiplier': forms.TextInput(attrs=utils.ATTRS2),
			'results_file': forms.FileInput(attrs={"class": "form-control-file"}),
		}

class CobasUploadForm(forms.ModelForm):
	
	class Meta:
		model = CobasResultsUpload
		fields = ('reference_number', 'multiplier', 'results_file',)
		widgets = {
			'reference_number': forms.TextInput(attrs=utils.ATTRS),
			'multiplier': forms.TextInput(attrs=utils.ATTRS2),
			'results_file': forms.FileInput(attrs={"class": "form-control-file"}),
		}