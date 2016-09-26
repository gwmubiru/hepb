from django import forms

from .models import WorksheetResultsUpload
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