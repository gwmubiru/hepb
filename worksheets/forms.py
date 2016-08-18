from django import forms
from home import utils

class WorksheetForm(forms.Form):
	MACHINE_TYPES = ( ('A', 'Abbott'), ('R', 'Roche') )
	SAMPLE_TYPES = ( ('P', 'Plasma'), ('D', 'DBS') )
	attrs = {'class':'form-control input-sm w-md', 'required':'true'}
	attrs2 = {'class':'form-control input-sm w-xs', 'required':'true'}
	attrs_date = {'class':'form-control input-sm w-sm date', 'required':'true'}

	worksheet_reference_number = forms.CharField(max_length=128, widget=forms.TextInput(attrs=attrs))
	machine_type = forms.ChoiceField(choices=MACHINE_TYPES, widget=forms.Select(attrs=attrs2))
	sample_type = forms.ChoiceField(choices=SAMPLE_TYPES, widget=forms.Select(attrs=attrs2))
	sample_prep = forms.CharField(max_length=64, widget=forms.TextInput(attrs=attrs))
	sample_prep_expiry_date = forms.DateField(widget=forms.DateInput(attrs=attrs_date))

	bulk_lysis_buffer = forms.CharField(
							max_length=64, 
							required=False,
							widget=forms.TextInput(
								attrs=utils.delete_item(attrs,'required')
								),
							)

	bulk_lysis_buffer_expiry_date = forms.DateField(
										required=False,
										widget=forms.DateInput(
											attrs=utils.delete_item(attrs_date,'required')
											),
										)

	control = forms.CharField(max_length=64, widget=forms.TextInput(attrs=attrs))
	control_expiry_date = forms.DateField(widget=forms.DateInput(attrs=attrs_date))
	calibrator = forms.CharField(max_length=64, widget=forms.TextInput(attrs=attrs))
	calibrator_expiry_date = forms.DateField(widget=forms.DateInput(attrs=attrs_date))
	include_calibrators = forms.BooleanField()
	amplication_kit = forms.CharField(max_length=64, widget=forms.TextInput(attrs=attrs))
	amplication_kit_expiry_date = forms.DateField(widget=forms.DateInput(attrs=attrs_date))
	assay_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs=attrs_date))
	

	# machine_type = forms.CharField(max_length=1, choices=MACHINE_TYPES)
	# sample_type = forms.CharField(max_length=1, choices=SAMPLE_TYPES)
	# sample_prep = forms.CharField(max_length=64)
	# sample_prep_expiry_date = forms.DateField()
	# bulk_lysis_buffer = forms.CharField(max_length=64, null=True)
	# bulk_lysis_buffer_expiry_date = forms.DateField(null=True)
	# control = forms.CharField(max_length=64)
	# control_expiry_date = forms.DateField()
	# calibrator = forms.CharField(max_length=64)
	# calibrator_expiry_date = forms.DateField()
	# include_calibrators = forms.BooleanField(default=False)
	# amplication_kit = forms.CharField(max_length=64)
	# amplication_kit_expiry_date = forms.DateField()
	# assay_date = forms.DateTimeField()
	# generated_by = forms.ForeignKey(User, related_name='generated_by')
	# worksheet_updated_by = forms.ForeignKey(User, related_name='worksheet_updated_by', null=True)
	# created_at = forms.DateTimeField(auto_now_add=True)
	# updated_at = forms.DateTimeField(auto_now=True)
	# results_uploaded = forms.BooleanField(default=False)
	# printed = forms.BooleanField(default=False)
	
