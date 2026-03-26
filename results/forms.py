from django import forms

from .models import WorksheetResultsUpload,CobasResultsUpload
from home import utils

class UploadForm(forms.ModelForm):
	
	class Meta:
		model = WorksheetResultsUpload
		fields = ('multiplier', 'results_file',)
		widgets = {
			#'worksheet': forms.HiddenInput(),
			'multiplier': forms.TextInput(attrs=utils.ATTRS2),
			'machine_type': forms.TextInput(attrs=utils.ATTRS2),
			'reference_number': forms.TextInput(attrs=utils.ATTRS2),
			#'results_file': forms.FileInput(attrs={"class": "form-control-file", "multiple":True}),
			'results_file': forms.FileInput(attrs={"class": "form-control-file"}),
			#'files': forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True})),
		}

class CobasUploadForm(forms.ModelForm):
	
	class Meta:
		model = CobasResultsUpload
		fields = ( 'results_file',)
		widgets = {
			'reference_number': forms.TextInput(attrs=utils.ATTRS),
			'results_file': forms.FileInput(attrs={"class": "form-control-file"}),
		}