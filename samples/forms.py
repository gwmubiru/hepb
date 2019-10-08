from datetime import *
from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from backend.models import Appendix, Facility
from .models import *
from home import utils

def appendix_field(category, required=True, attrs=False):
		queryset = Appendix.objects.filter(
						appendix_category_id=category
						)
		if not attrs:
			attrs = utils.ATTRS if required else utils.ATTRS_OPTIONAL
		widget = forms.Select(attrs=attrs)
		return forms.ModelChoiceField(queryset=queryset, widget=widget, required=required)

class ClinicianForm(forms.ModelForm):
	class Meta:
		model = Clinician
		fields = ('cname', 'cphone')
		widgets = {
			'cname':forms.TextInput(attrs={'class':'form-control input-sm w-md',  'autocomplete':'off', 'ng-model':'cname', 'ng-focus':'getClinicians()'}), 
			'cphone': forms.TextInput(attrs={'class':'form-control input-sm w-md', 'ng-model':'cphone'})}
		labels = {'cname': 'Requesting Clinician', 'cphone':'Phone'}

class PreliminaryFindingsForm(forms.ModelForm):
	class Meta:
		model = PreliminaryFindings
		fields = (
			'hbeag_results', 
			'hiv_coinfected',
			'hiv_hcv_coinfected',
			'hiv_hcv_tb_coinfected',
			'hep_other_coinfections',
			'alt_value_1',
			'alt_value_2',
			'alt_value_3',
			'ast_value_1',
			'ast_value_2',
			'ast_value_3',
			'alt_value_normal_range',
			'ast_value_normal_range',
			'platelet_count',
			'platelet_normal_range',
			'fetal_protein_value',
			'fetal_protein_value_normal_range',
			'ast_plt_ratio_greater_than_2',
			'serum_creatinine',
			'serum_creatinine_normal_range',
			'prem_other_findings')
		widgets = {
			'hbeag_results': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'hiv_coinfected':forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'hiv_hcv_coinfected':forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'hiv_hcv_tb_coinfected':forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'hep_other_coinfections':forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'alt_value_1': forms.TextInput(attrs={'class':'form-control input-sm small-input', 'placeholder':'1','size':'5'}),
			'alt_value_2': forms.TextInput(attrs={'class':'form-control input-sm small-input', 'placeholder':'2','size':'5'}),
			'alt_value_3': forms.TextInput(attrs={'class':'form-control input-sm small-input', 'placeholder':'3','size':'5'}),
			'alt_value_normal_range': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Normal Ranges 1U/ML','size':'18'}),
			'platelet_count': forms.TextInput(attrs={'class':'form-control input-sm small-input', 'placeholder':'1','size':'5'}),
			'platelet_normal_range': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Normal Ranges 1U/ML','size':'18'}),
			'ast_value_1': forms.TextInput(attrs={'class':'form-control input-sm small-input', 'placeholder':'1','size':'5'}),
			'ast_value_2': forms.TextInput(attrs={'class':'form-control input-sm small-input', 'placeholder':'2','size':'5'}),
			'ast_value_3': forms.TextInput(attrs={'class':'form-control input-sm small-input', 'placeholder':'3','size':'5'}),
			'ast_value_normal_range': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Normal Ranges 1U/ML','size':'18'}),
			'fetal_protein_value': forms.TextInput(attrs={'class':'form-control', 'size':'5'}),
			'fetal_protein_value_normal_range': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Normal Ranges 1U/ML','size':'18'}),
			'serum_creatinine': forms.TextInput(attrs={'class':'form-control', 'size':'5'}),
			'serum_creatinine_normal_range': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Normal Ranges 1U/ML','size':'18'}),			
			'ast_plt_ratio_greater_than_2':forms.Select(attrs=utils.ATTRS_OPTIONAL),
			'prem_other_findings':forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
		}
		labels = {
			'hbeag_results': 'HBeAg results',
			'hiv_coinfected':'HBV/HIV',
			'hiv_hcv_coinfected':'HBV/HCV',
			'hiv_hcv_tb_coinfected': 'HBV/HIV/TB',
			'hep_other_coinfections': 'Others',
			'prem_other_findings':'Other Findings',
		}
class LabTechForm(forms.ModelForm):
	class Meta:
		model = LabTech
		fields = ('lname', 'lphone')
		widgets = {
			'lname':forms.TextInput(attrs={'class':'form-control input-sm w-md', 'autocomplete':'off', 'ng-model':'lname', 'ng-focus':'getLabTechs()','required':'true'}), 
			'lphone': forms.TextInput(attrs={'class':'form-control input-sm w-md', 'ng-model':'lphone'})}
		labels = {'lname': 'Name of Lab Contact Person', 'lphone':'Phone No.'}

class PatientForm(forms.ModelForm):
	class Meta:
		model = Patient

		fields = ('hep_number', 'other_id', 'gender', 'dob','name',)

		widgets = {
			'hep_number': forms.TextInput(attrs={'class':'form-control input-sm w-md'}),
			'other_id': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'name': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'gender': forms.Select(attrs=utils.ATTRS2),
			'dob': forms.DateInput(attrs=utils.ATTRS_DATE),
		}

		labels = {
			'hep_number':'Patient Hep No.',
			'other_id':'Other ID(NIN)',
			'name':'Name',
		}

	def clean(self):
		utils.non_future_dates(self, ['dob'])
		cld = self.cleaned_data
		if cld.get('hep_number') == '' and cld.get('other_id') == '' and cld.get('locator_category') != 'R':
			self.add_error('hep_number', 'Both ART number and Other ID are null, atleast one is required or reject')


class EnvelopeForm(forms.ModelForm):
	class Meta:
		model = Envelope

		fields = ('envelope_number',)

		widgets = {
			'envelope_number': forms.TextInput(
				attrs={'class':'form-control input-sm', 'size': '14', 'required':'true'}
				),
		}

	def clean(self):
		cleaned_data = self.cleaned_data
		env_number = self.cleaned_data.get('envelope_number')
		if len(env_number) != 9:
			self.add_error('envelope_number', "Invalid envelope number. Right format is YYMM-XXXX")

class PatientPhoneForm(forms.ModelForm):
	class Meta:
		model = PatientPhone

		fields = ('phone',)

		widgets = {
			'phone': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
		}
		

class SampleForm(forms.ModelForm):

	#facility = Facility.objects.values('id', 'facility').filter(active=True)	
	current_regimen = appendix_field(3, False)
	treatment_indication = appendix_field(6, False)
	failure_reason = appendix_field(2, False)
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
			'other_regimen',
			'pregnant',
			'anc_number',
			'breast_feeding',
			'active_tb_status',
			'date_collected',
			'date_received',
			'treatment_duration',
			'treatment_initiation_date',
			'current_who_stage',
			'sample_type',
			'treatment_indication',
			'treatment_indication_other',
			'failure_reason',
			'tb_treatment_phase',
			'arv_adherence',			
			'last_test_date',
			'last_value',
			'last_sample_type',
			'treatment_care_approach',
			'is_patient_on_treatment',
			'current_drug_name',
			'reason_for_vl',
			'is_study_sample',
			)

		widgets = {
			'locator_category': forms.Select(attrs=utils.ATTRS2),
			'locator_position': forms.TextInput(
				attrs={'class':'form-control input-sm', 'size': '4', 'required':'true'}
				),
			'form_number': forms.TextInput(attrs=utils.ATTRS),
			'facility': forms.Select(attrs={'class':'form-control input-sm w-md', 'required':'true', 'ng-model':'facility'}),
			'pregnant': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'anc_number': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'breast_feeding': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'active_tb_status': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'date_collected': forms.DateInput(attrs=utils.ATTRS_DATE),
			'date_received': forms.DateInput(attrs=utils.ATTRS_DATE),
			'treatment_duration': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'treatment_initiation_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'current_who_stage':forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'sample_type': forms.Select(attrs=utils.ATTRS2),
			'treatment_indication_other': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'treatment_care_approach':forms.Select(attrs=utils.ATTRS2_OPTIONAL),		
			'last_test_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'last_value': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'last_sample_type': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'other_regimen':forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'is_patient_on_treatment':forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'current_drug_name': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'current_regimen':forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'reason_for_vl':forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			}

		labels = {
			'current_who_stage':'Current WHO Stage',
			'treatment_duration':'How long has the patient been on tx',
			'treatment_indication': "Indication for Treament initiation",
			'last_test_date': "Last VL Date",
			'last_value': "Value of Last Test",
			'last_sample_type': "Sample Type of Last Test",
			'treatment_care_approach':'Treament care approach(DSDM)',
			'is_patient_on_treatment':'Is Patient on Hep B Treament?',
			'current_drug_name': 'If Yes, Drug Name',
			'reason_for_vl':'Reason for VL',
			}

	def clean(self):
		cleaned_data = self.cleaned_data

		date_today = date.today()
		locator_category = cleaned_data.get('locator_category')
		date_collected = cleaned_data.get('date_collected')
		date_received = cleaned_data.get('date_received')
		locator_position = cleaned_data.get('locator_position')
		sample_type = cleaned_data.get('sample_type')

		if sample_type=='D' and len(locator_position)!=2:
			self.add_error('locator_position', 'Length of 2 for sample position expected for DBS')
		elif sample_type=='P' and len(locator_position)!=3:
			self.add_error('locator_position', 'Length of 3 for sample position expected for Plasma')


		pk = self.instance.pk

		utils.non_future_dates(self, ['date_collected',  'treatment_initiation_date', 'last_test_date'])


		# if (date_today - date_collected).days >=30 and locator_category!='R' and not pk:
		# 	self.add_error('date_collected', "date collected >= 30 days, please reject")

		form_fltr = Q(form_number=cleaned_data.get('form_number'))
		if pk:
			form_fltr = ~Q(pk=pk) & form_fltr

		if Sample.objects.filter(form_fltr).exists():
			self.add_error('form_number', "Form number exists")


class DrugResistanceRequestForm(forms.ModelForm):
	
	class Meta:
		model = DrugResistanceRequest
		fields = ('body_weight','patient_on_rifampicin',)
		widgets = {
		'body_weight': forms.TextInput(attrs=utils.ATTRS_OPTIONAL), 
		'patient_on_rifampicin': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
		}

class PastRegimensForm(forms.ModelForm):
	regimen = appendix_field(3, False, utils.ATTRS2_OPTIONAL)
	
	class Meta:
		model = PastRegimens
		fields = ('regimen','start_date','stop_date',)
		widgets = {
			'start_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			'stop_date': forms.DateInput(attrs=utils.ATTRS_DATE),
			}
		