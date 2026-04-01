from datetime import *
from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from backend.models import Appendix, Facility
from .models import *
from home import utils
from home import db_aliases
from . import utils as sample_utils
from django.core.cache import cache


def appendix_field(category, required=True, attrs=False, db_alias='default'):
	cache_key = f"appendix_category_{db_alias}_{category}"
	queryset = cache.get(cache_key)
	if queryset is None:
		queryset = list(Appendix.objects.using(db_alias).filter(appendix_category_id=category))
		cache.set(cache_key, queryset, timeout=3600)  # cache for 1 hour
	if not attrs:
		attrs = utils.ATTRS if required else utils.ATTRS_OPTIONAL
	widget = forms.Select(attrs=attrs)
	return forms.ModelChoiceField(queryset=Appendix.objects.using(db_alias).filter(pk__in=[obj.pk for obj in queryset]),
   
                                widget=widget, required=required)


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

class PatientForm(forms.ModelForm):
	class Meta:
		model = Patient

		fields = ('hep_number', 'other_id', 'gender', 'dob','name','treatment_initiation_date',)

		widgets = {
			'hep_number': forms.TextInput(attrs={'class':'form-control input-sm w-md'}),
			'other_id': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'treatment_initiation_date': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'name': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'gender': forms.Select(attrs=utils.ATTRS2),
			'dob': forms.DateInput(attrs=utils.ATTRS_DATE),
		}

		labels = {
			'hep_number':'Patient Hep No.',
			'other_id':'Other ID(NIN)',
			'name':'Name',
			'treatment_initiation_date':'Treatment initiation  date',
		}

	def clean(self):
		utils.non_future_dates(self, ['dob','treatment_initiation_date'])
		cld = self.cleaned_data
		if cld.get('hep_number') == '' and cld.get('other_id') == '' and cld.get('locator_category') != 'R':
			self.add_error('hep_number', 'Both ART number and Other ID are null, atleast one is required or reject')


class PatientExistenceForm(forms.ModelForm):
	class Meta:
		model = Patient

		fields = ('hep_number',)

		widgets = {
			'hep_number': forms.TextInput(attrs={'class':'form-control input-sm w-md', 'ng-model':'hep_number', 'ng-change':'patHist()'}),
		}

		labels = {
			'hep_number':'Patient Clinic ID/ART #',
		}
	def clean(self):
		cleaned_data = self.cleaned_data
		
class PatientExistsFacilityForm(forms.ModelForm):

	class Meta:
		model = Sample

		fields = (
			'facility',
			)

		widgets = {
			'facility': forms.Select(attrs={'class':'form-control input-sm w-md', 'required':'true', 'ng-model':'facility'}),
			}
	def clean(self):
		cleaned_data = self.cleaned_data

	def __init__(self, *args, **kwargs):
		db_alias = kwargs.pop('db_alias', db_aliases.get_hepb_db_alias())
		super(PatientExistsFacilityForm, self).__init__(*args, **kwargs)
		self.fields['facility'].queryset = Facility.objects.using(db_alias).all()

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
		#if len(env_number) != 9:
			#self.add_error('envelope_number', "Invalid envelope number. Right format is YYMM-XXXX")


class SampleForm(forms.ModelForm):

	#facility = Facility.objects.values('id', 'facility').filter(active=True)	
	current_regimen = appendix_field(3)
	treatment_indication = appendix_field(6, False)
	failure_reason = appendix_field(2, False)
	tb_treatment_phase = appendix_field(5, False)
	arv_adherence = appendix_field(1, False)
	id = forms.IntegerField(required=False, widget=forms.TextInput({'class': 'hidden'})) 

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
			'consented_sample_keeping',
			'active_tb_status',
			'date_collected',
			'date_received',
			'treatment_duration',
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
			'barcode',
			'id'
			)

		widgets = {
			'locator_category': forms.Select(attrs=utils.ATTRS2),
			'locator_position': forms.TextInput(
				attrs={'class':'form-control input-sm hidden', 'size': '4', 'required':'true'}
				),
			'barcode': forms.TextInput(attrs=utils.ATTRS),
			'form_number': forms.TextInput(attrs=utils.ATTRS),
			'form_number': forms.TextInput(attrs=utils.ATTRS),
			'facility': forms.Select(attrs={'class':'form-control input-sm w-md', 'required':'true', 'ng-model':'facility','ng-change':'patHist()'}),
			'validation_facility': forms.Select(attrs={'class':'form-control input-sm w-md', 'required':'true', 'ng-model':'facility'}),
			'pregnant': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'treatment_duration': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'anc_number': forms.TextInput(attrs=utils.ATTRS_OPTIONAL),
			'breast_feeding': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'consented_sample_keeping': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'active_tb_status': forms.Select(attrs=utils.ATTRS2_OPTIONAL),
			'date_collected': forms.DateInput(attrs=utils.ATTRS_DATE),
			'date_received': forms.DateInput(attrs=utils.ATTRS_DATE),
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
			'consented_sample_keeping':'Specimen Storage Broad Consent',
			'last_value': "Value of Last Test",
			'last_sample_type': "Sample Type of Last Test",
			'is_patient_on_treatment':'Is Patient on Hep B Treament?',
			'current_drug_name': 'If Yes, Drug Name',
			'reason_for_vl':'Reason for VL',
			}

	def __init__(self, *args, **kwargs):
		db_alias = kwargs.pop('db_alias', db_aliases.get_hepb_db_alias())
		super(SampleForm, self).__init__(*args, **kwargs)
		self.fields['facility'].queryset = Facility.objects.using(db_alias).all()
		self.fields['current_regimen'].queryset = Appendix.objects.using(db_alias).filter(appendix_category_id=3)
		self.fields['treatment_indication'].queryset = Appendix.objects.using(db_alias).filter(appendix_category_id=6)
		self.fields['failure_reason'].queryset = Appendix.objects.using(db_alias).filter(appendix_category_id=2)
		self.fields['tb_treatment_phase'].queryset = Appendix.objects.using(db_alias).filter(appendix_category_id=5)
		self.fields['arv_adherence'].queryset = Appendix.objects.using(db_alias).filter(appendix_category_id=1)

	def clean(self):
		cleaned_data = self.cleaned_data

		date_today = date.today()
		locator_category = cleaned_data.get('locator_category')
		date_collected = cleaned_data.get('date_collected')
		date_received = cleaned_data.get('date_received')
		dob = cleaned_data.get('dob')
		locator_position = cleaned_data.get('locator_position')
		sample_type = cleaned_data.get('sample_type')
		consented_sample_keeping = cleaned_data.get('consented_sample_keeping')

		pk = self.instance.pk

		utils.non_future_dates(self, ['date_collected', 'last_test_date','date_received','dob'])
		if not date_collected:
			self.add_error('date_collected', 'Collection date cannot be blank')

		if utils.compare_dates(first_date=date_collected, second_date=date_received, operator='gt'):
			self.add_error('date_collected', "date collected can not be > date received")
			
		if utils.compare_dates(first_date=dob, second_date=date_collected, operator='gt'):
			self.add_error('bob', "date of birth can not be > date of collection")

		if utils.compare_dates(first_date=dob, second_date=date_collected, operator='gt'):
			self.add_error('bob', "date of birth can not be > date of collection")

		if (date_today - date_collected).days >=120 and locator_category!='R' and not pk:
			self.add_error('date_collected', "date collected >= 120 days, please reject")
		if consented_sample_keeping =='' or consented_sample_keeping is None:
			self.add_error('consented_sample_keeping', 'Select an option for patient consent')
		form_fltr = Q(form_number=cleaned_data.get('form_number')) & Q(facility = cleaned_data.get('facility'))
		if pk:
			form_fltr = ~Q(pk=pk) & form_fltr

		if Sample.objects.filter(form_fltr).exists():
			self.add_error('form_number', "Form number exists")

class SampleReceptionForm(forms.ModelForm):
	class Meta:
		model = Sample

		fields = (
			'facility',
			'date_collected',
			'date_received',
			'sample_type',
			'barcode',
			'facility_reference'
			)

		widgets = {
			'barcode': forms.TextInput(attrs={'class':'form-control input-sm special_width','required':'required',}),
			'facility': forms.Select(attrs={'class':'form-control input-sm special_width',}),
			'date_collected': forms.DateInput(attrs={'class': 'form-control input-sm w-xs date_d'}),
			'date_received': forms.DateInput(attrs=utils.ATTRS_DATE),
			'sample_type': forms.Select(attrs=utils.ATTRS3),
			'locator_category': forms.Select(attrs=utils.ATTRS3),
			}

		labels = {
			'facility':'Facility',
			'date_collected': 'Date Collected',
			'date_received': "Reception Date",
			'hep_number': 'Art Number',
			'barcode':'Locator ID',
			}

	def __init__(self, *args, **kwargs):
		db_alias = kwargs.pop('db_alias', db_aliases.get_hepb_db_alias())
		super(SampleReceptionForm, self).__init__(*args, **kwargs)
		self.fields['facility'].queryset = Facility.objects.using(db_alias).all()

	def clean(self):
		cleaned_data = self.cleaned_data
		#self.cleaned_data['date_collected'] = sample_utils.get_mysql_from_uk_date(cleaned_data.get('date_collected'))
		date_today = date.today()
		date_collected = cleaned_data.get('date_collected')
		sample_type = cleaned_data.get('sample_type')
		barcode = cleaned_data.get('barcode')

		pk = self.instance.pk

		utils.non_future_dates(self, ['date_collected'])
		if not date_collected:
			self.add_error('date_collected', 'Date collected is required')
		form_fltr = Q(barcode=cleaned_data.get('barcode'))
		if pk:
			form_fltr = ~Q(pk=pk) & form_fltr

		if SampleReception.objects.filter(form_fltr).exists():
			self.add_error('barcode', "Locator ID already received")

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

	def __init__(self, *args, **kwargs):
		db_alias = kwargs.pop('db_alias', db_aliases.get_hepb_db_alias())
		super(PastRegimensForm, self).__init__(*args, **kwargs)
		self.fields['regimen'].queryset = Appendix.objects.using(db_alias).filter(appendix_category_id=3)
