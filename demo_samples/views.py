import json, os, glob, calendar
from datetime import date as dt, datetime as dtime
from datetime import datetime
# from datetime import datetime as dt dtime
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse

from django.db.models import Q
from django import *
#from django.views.generic import TemplateView

from backend.models import Appendix,Facility,MedicalLab
from .models import *
#from .forms import PastRegimensForm,AttachSamplesForm
from django.forms import formset_factory
from django.forms import *
#from .forms import PastRegimensForm
#from .forms import ClinicianForm
#from .forms import EnvelopeForm
from .forms import *
from home import utils
from . import utils as sample_utils
from django.db import connections
from django.db import transaction
from worksheets.models import Worksheet,WorksheetSample
from . import utils as worksheet_utils
# Create your views here.
#from requests.structures import CaseInsensitiveDict
#import requests

ENVS_LIMIT = 1000
SAMPLES_LIMIT = 1000

@permission_required('samples.add_sample', login_url='/login/')
@transaction.atomic
def create(request):
	facilities = Facility.objects.values('id','facility');
	#for fac in facilities:
	#	return HttpResponse(fac['facility'])#YYY

	saved_sample = request.GET.get('saved_sample')
	page_type = request.GET.get('page_type')
	PastRegimensFormSet = modelformset_factory(PastRegimens, PastRegimensForm, extra=5)
	if request.method == 'POST':
		pst = request.POST
		#return HttpResponse(pst)
		pat_id = pst.get('patient_id')
		page_type = pst.get('page_type')
		patient_form = PatientForm(pst)
		phone_form = PatientPhoneForm(pst)
		envelope_form = EnvelopeForm(pst)
		sample_form = SampleForm(pst)
		sample_form.date_received = pst['date_received']
		drug_resistance_form = DrugResistanceRequestForm(pst)
		past_regimens_formset =PastRegimensFormSet(pst)

		valid_patient = patient_form.is_valid()
		valid_phone = phone_form.is_valid()
		valid_envelope = envelope_form.is_valid()
		valid_sample = sample_form.is_valid()
		valid_dr = drug_resistance_form.is_valid()
		valid_past_regimens = past_regimens_formset.is_valid()

		null_dob = pst.get('null_dob')
		null_treatment_initiation_date = pst.get('null_treatment_initiation_date')

		if not pst.get('dob') and not null_dob:
			patient_form.add_error('dob', 'Date is blank')

		if not pst.get('treatment_initiation_date') and not null_treatment_initiation_date:
			patient_form.add_error('treatment_initiation_date', 'Date is blank')

		if not pst.get('date_collected'):
			patient_form.add_error('date_collected', 'Collection date cannotDate is blank')

		loc_exists = sample_utils.locator_id_exists(pst, pst.get('s_id'))

		#if loc_exists:
		#	loc_by = loc_exists.created_by
		#	loc_on = loc_exists.created_at
		#	sample_form.add_error('locator_position', 'Locator ID already created by %s on %s'%(loc_by,loc_on))
		if not sample_utils.initiation_date_valid(pst):
			patient_form.add_error('treatment_initiation_date', 'Initiation date can not be < DoB')
		elif not sample_utils.collection_date_valid(pst):
			sample_form.add_error('date_collected','sample collection date cannot be < DoB')
		elif valid_patient and valid_phone and valid_envelope and valid_sample and valid_dr and valid_past_regimens:
			facility = sample_form.cleaned_data.get('facility')
			art_number = patient_form.cleaned_data.get('art_number')
			#unique_id = "%s-A-%s" %(facility.pk, art_number.replace(' ','').replace('-','').replace('/',''))
			sanitized_art_no = utils.removeSpecialCharactersFromString(request.POST.get('reception_art_number'))
			unique_id = "%s-A-%s" %(facility.pk, sanitized_art_no)
			#if patient exits, load patient object else, create a new patient
			if not pat_id:
				patient = patient_form.save(commit=False)
				patient.unique_id = unique_id
				patient.created_by = request.user
				patient.parent_id = patient.id
				patient.facility_id = facility.id
				patient.treatment_duration = pst.get('treatment_duration')	
				p.sanitized_art_number = sanitized_art_no			
				patient.save()
			else:
				patient = Patient.objects.get(pk=pat_id)

			# patient_form.cleaned_data.update({'created_by': request.user})
			# patient, pat_created = Patient.objects.update_or_create(
			# 			unique_id=unique_id,
			# 			defaults=patient_form.cleaned_data
			# 			)

			

			ph_number = phone_form.cleaned_data.get('phone')
			if ph_number:
				phone, phone_created = PatientPhone.objects.get_or_create(patient=patient,**phone_form.cleaned_data)

			envelope, env_created = Envelope.objects.get_or_create(
						envelope_number=envelope_form.cleaned_data.get('envelope_number'),
						defaults={'sample_type': sample_form.cleaned_data.get('sample_type'),'sample_medical_lab':utils.user_lab(request)}
						)

			sample = Sample.objects.filter(pk=request.POST.get('s_id')).first()
			sample.locator_category = sample_form.cleaned_data.get('locator_category')
			sample.locator_position = sample_form.cleaned_data.get('locator_position')
			sample.form_number = sample_form.cleaned_data.get('form_number')
			sample.facility = sample_form.cleaned_data.get('facility')
			sample.current_regimen = sample_form.cleaned_data.get('current_regimen')
			sample.other_regimen = sample_form.cleaned_data.get('other_regimen')
			sample.pregnant = sample_form.cleaned_data.get('pregnant')
			sample.anc_number = sample_form.cleaned_data.get('anc_number')
			sample.breast_feeding = sample_form.cleaned_data.get('breast_feeding')
			sample.consented_sample_keeping = sample_form.cleaned_data.get('consented_sample_keeping')
			sample.active_tb_status = sample_form.cleaned_data.get('active_tb_status')
			sample.date_collected = sample_form.cleaned_data.get('date_collected')
			sample.treatment_duration = sample_form.cleaned_data.get('treatment_duration')
			sample.current_who_stage = sample_form.cleaned_data.get('current_who_stage')
			sample.sample_type = sample_form.cleaned_data.get('sample_type')
			sample.viral_load_testing = sample_form.cleaned_data.get('viral_load_testing')
			sample.treatment_indication = sample_form.cleaned_data.get('treatment_indication')
			sample.treatment_indication_other = sample_form.cleaned_data.get('treatment_indication_other')
			sample.treatment_line = sample_form.cleaned_data.get('treatment_line')
			sample.failure_reason = sample_form.cleaned_data.get('failure_reason')
			sample.tb_treatment_phase = sample_form.cleaned_data.get('tb_treatment_phase')
			sample.arv_adherence = sample_form.cleaned_data.get('arv_adherence')
			sample.last_test_date = sample_form.cleaned_data.get('last_test_date')
			sample.current_regimen_initiation_date = sample_form.cleaned_data.get('current_regimen_initiation_date')
			sample.last_value = sample_form.cleaned_data.get('last_sample_type')
			sample.last_sample_type = sample_form.cleaned_data.get('locator_category')
			sample.treatment_care_approach = sample_form.cleaned_data.get('treatment_care_approach')
			sample.barcode = sample_form.cleaned_data.get('barcode')
			sample.verified = 1
			sample.patient = patient
			sample.is_data_entered = 1
			sample.patient_unique_id = patient.unique_id
			sample.is_data_entered = 1

			patient.save()
			#sample.vl_sample_id = sample_utils.create_sample_id()
			sample.data_entered_by = request.user
			sample.sample_medical_lab = utils.user_lab(request)
			sample.data_entered_at = datetime.now().date()
			#sample.created_at = datetime.now().date()
			envep_no = request.POST.get('envelope_number')
			env_type = int(envep_no[-4:])
			if (env_type >= 900 and env_type < 1000) or (env_type > 800 and env_type < 900):
				sample.is_study_sample = 1
			else:
				sample.is_study_sample = 0

			sample.save()

			if 'has_dr' in request.POST:
				drug_resistance = drug_resistance_form.save(commit=False)
				drug_resistance.sample = sample
				drug_resistance.save()

				past_regimens = past_regimens_formset.save(commit=False)
				for past_regimen in past_regimens:
					past_regimen.drug_resistance_request = drug_resistance
					past_regimen.save()

			return redirect('/samples/create?saved_sample=%s&page_type=%s' %(sample.pk,page_type))
		else:
			#get back the page date format
			sample_form.add_error('form_number', 'Saving failed')
	else:
		envelope_form = EnvelopeForm(initial={'envelope_number': sample_utils.initial_env_number()})
		
		phone_form = PatientPhoneForm
		patient_form = PatientForm
		d = datetime.now()
		next_barcode = ''
		if saved_sample:
			sample = Sample.objects.filter(pk=saved_sample).first()
			#next_barcode = sample.barcode[:-2]
			next_barcode = sample_utils.get_next_barcode(sample.barcode,sample.sample_type) 
		
		sample_form = SampleForm(initial={'locator_category':'V', 'date_collected': d.strftime("%d/%m/%Y"),'barcode':next_barcode})
		drug_resistance_form = DrugResistanceRequestForm
		past_regimens_formset = PastRegimensFormSet(queryset=PastRegimens.objects.none())
		null_treatment_initiation_date = None
		null_dob = None

	context = {
		'envelope_form': envelope_form,
		'phone_form': phone_form,
		'patient_form': patient_form,
		'sample_form': sample_form,
		'drug_resistance_form': drug_resistance_form,
		'past_regimens_formset': past_regimens_formset,
		'regimens': Appendix.objects.filter(appendix_category=3),
		'null_dob': null_dob,
		'null_treatment_initiation_date':null_treatment_initiation_date,
		'facilities':facilities,
		'page_type':page_type,
	}

	if saved_sample:
		#sample = Sample.objects.filter(pk=saved_sample).first()
		context.update({'sample':sample,'next_sample':1})
	
	if page_type == '2':
		return render(request, 'samples/create2.html', context)
	else:
		
		return render(request, 'samples/create.html', context)


@permission_required('samples.add_sample', login_url='/login/')

def fix_reception(request):
	bar_par = request.GET.get('barcode_pattern')
	sample_reception_objs = SampleReception.objects.filter(barcode__startswith=bar_par)

	env_no = bar_par[:4]+'-'+bar_par[4:8]
	envelope = Envelope.objects.filter(envelope_number=env_no).first()
	if not envelope:
		envelope  = Envelope(envelope_number = env_no,sample_medical_lab_id =1,stage =1, created_at = datetime.now().date())
	for sample_reception in sample_reception_objs:
		s = Sample.objects.filter(barcode = sample_reception.barcode)
		if not s:
			s = Sample(locator_category = 'v',locator_position=sample_reception.barcode[8:10],
					barcode=sample_reception.barcode,created_by =sample_reception.creator,sample_reception = sample_reception,
					date_received = sample_reception.created_at,form_number=sample_reception.barcode,
					sample_type=sample_reception.sample_type,date_collected=sample_reception.date_collected,envelope = envelope)
			s.save()

			v = Verification.objects.filter(sample=s).first()
			v = v if v else Verification()
			v.pat_edits = 0
			v.sample_edits = 0
			v.sample = s
			accepted = 'v'
			v.accepted = True
			v.rejection_reason_id = None
			v.verified_by = sample_reception.creator
			v.save()
	return HttpResponse('done')

def fix_identifiers(request):
	bar_par = request.GET.get('barcode_pattern')
	samples = Sample.objects.filter(barcode__startswith=bar_par)
	for sample in samples:
		if sample:
			identifier = SampleIdentifier.objects.filter(barcode=sample.barcode).first()
			if identifier:
				identifier.sample_id = sample.id
				identifier.save()
			else:
				return HttpResponse('not yet')

	return HttpResponse('done')

def fix_verifications(request):
	env_no = request.GET.get('env_number')
	envelope = Envelope.objects.filter(envelope_number = env_no)
	samples = Sample.objects.filter(envelope = envelope)
	for sample in samples:
		existing_ver = Verification.objects.filter(sample= sample).first()
		if not existing_ver:
			ver = Verification()
			ver.accepted = 1
			ver.verified_by_id = 1
			ver.pat_edits = 0
			ver.sample_edits =0
			ver.created_at = sample.created_at
			ver.updated_at = sample.created_at
			ver.sample = sample
			ver.save()

			sample.verified = 1
			sample.save()
		else:
			#mark sample verified
			if sample.locator_category == 'V':
				existing_ver.accepted = 1
			else:
				existing_ver.accepted = 0
			existing_ver.save()
			sample.verified = 1
			sample.save()
	return HttpResponse('done')


def receive_api(request):

	return HttpResponse(request.POST.get('facilityid'))
	#geodata = response.json()
	#return HttpResponse(geodata['ip'])
	
@transaction.atomic
def receive(request):
	
	#facility_patients = FacilityPatient.objects.all()
	#for fp in facility_patients:
	#	unique_id = "%s-A-%s" %(fp.facility_id, utils.removeSpecialCharactersFromString(fp.art_number))
	#	fp.unique_id = unique_id
	#	fp.save()
	
	saved_sample = request.GET.get('saved_sample')
	tr_code_id = request.GET.get('tr_code_id')
	env_id = request.GET.get('env_id')
	current_tr_code = request.GET.get('current_tr_code')

	#request_type = "POST"
	#data = {"email":"email", "name": "name"}
	#api_url = "http://10.200.254.44/api/restrack/update/package/3"
	#response = requests.request(request_type, api_url, data=data)

	if request.method == 'POST':
		pst = request.POST
		accepted = pst.get('locator_category')
		rejection_reason_id = pst.get('rejection_reason_id')
		if(accepted=='R' and not rejection_reason_id):
			return HttpResponse("rejection reason required for rejected samples")

		#return HttpResponse(r)
		#return HttpResponse(request.POST.get('locator_category'))
		sample_reception_form = SampleReceptionForm(pst)
		valid_sample = sample_reception_form.is_valid()
		if valid_sample:
			tr_code_id = request.POST.get('tracking_code_id')
			env_id = request.POST.get('envelope_id')
			if env_id == '' or env_id is None:
				envelope = Envelope.objects.filter(envelope_number=request.POST.get('envelope_number')).first()
				if envelope is None:
					envelope = Envelope()
					envelope.envelope_number=request.POST.get('envelope_number')
					envelope.sample_type=request.POST.get('sample_type')
					envelope.sample_medical_lab=utils.user_lab(request)
					envelope.stage=2
					envelope.save()
				env_id = envelope.id

			if tr_code_id == ''  or (current_tr_code != '' and pst.get('code') != current_tr_code) :
				tr = TrackingCode.objects.filter(code=pst.get('code')).first()
				if tr is None:
					tr = TrackingCode()
					tr.code = pst.get('code')
					tr.creation_by_id = request.user.id
					tr.save()
				tr_code_id = tr.id
			#get the facility_patient
			#save the sample and its first identifier

			sanitized_art_no = utils.removeSpecialCharactersFromString(request.POST.get('reception_art_number'))
			unique_id = "%s-A-%s" %(request.POST.get('facility'), sanitized_art_no)
			#return HttpResponse(unique_id)
			facility_pat = FacilityPatient.objects.filter(unique_id=unique_id).first()
			fac_pat = facility_pat if facility_pat else None
			s = Sample(tracking_code_id = tr_code_id,locator_category = request.POST.get('locator_category'),locator_position=request.POST.get('locator_position'),
				barcode=request.POST.get('barcode'),created_by =request.user,
				date_received = request.POST.get('date_received'),form_number=request.POST.get('barcode'),facility_id = request.POST.get('facility'),
				sample_type=request.POST.get('sample_type'),envelope_id = env_id,reception_art_number=request.POST.get('reception_art_number'),facility_patient = fac_pat)
			s.save()
			
			#save the corresponding verification object
			#v = Verification.objects.filter(sample=s).first()
			v = Verification()
			v.pat_edits = 0
			v.sample_edits = 0
			v.sample = s
			accepted = pst.get('locator_category')
			v.accepted = True if accepted == 'V' else False
			if(accepted=='R'):
				v.rejection_reason_id = pst.get('rejection_reason_id')
				if not v.rejection_reason_id:
					return HttpResponse("rejection reason required for rejected samples")
			else:
				v.rejection_reason_id = None

			v.verified_by = request.user
			v.save()
			#https://reqbin.com/req/python/c-dwjszac0/curl-post-json-example
			#update the sample tracking system
			#url = "https://reqbin.com/echo/post/json"
			#headers = CaseInsensitiveDict()
			#headers["Content-Type"] = "application/json"
			#data = '{"status":"3","barcode":s.barcode,"facilityid":s.facility_id,"user_id":1}'
			#resp = requests.post(url, headers=headers, data=data)

			return redirect('/samples/receive?saved_sample=%s&tr_code_id=%s&env_id=%s&current_tr_code=%s' %(s.pk, tr_code_id,env_id,pst.get('code')))
		else:

			sample_reception_form.add_error('barcode', 'Saving failed')
	else:
		d = datetime.now()
		sample_reception_form = SampleReceptionForm(initial={'locator_category':'V', 'date_received': datetime.now().date()})

	context = {
		'sample_reception_form': sample_reception_form,
		'tr_code_id': tr_code_id,
		'env_id':env_id,
		'current_tr_code':current_tr_code,
		'reception_id':'',
		'locator_category':'',
		'reception_art_number': ''
	}

	if saved_sample:
		sample = Sample.objects.filter(pk=saved_sample).first()
		context.update({'sample':sample,'tr_code_id':tr_code_id,'env_id':env_id,})

	return render(request, 'samples/receive.html', context)

def get_envelope_details(request):
	envelope_number = request.GET.get('envelope_number')
	ret = []
	envelope = Envelope.objects.filter(id__gte=200000,envelope_number=envelope_number).first()
	
	if envelope is None:
		envelope = Envelope()
		envelope.envelope_number=envelope_number
		envelope.sample_type=request.GET.get('sample_type')
		envelope.sample_medical_lab=utils.user_lab(request)
		envelope.stage=2
		envelope.save()
	
	ret = {
		'envelope_id': envelope.id
		}
	return HttpResponse(json.dumps(ret))

def get_tracking_code_details(request):
	code = request.GET.get('code')
	ret = []
	tr = TrackingCode.objects.filter(code=code).first()
	if tr is None:
		tr = TrackingCode()
		tr.code = code
		tr.creation_by_id = request.user.id
		tr.save()
	
	ret = {
		'tracking_code_id': tr.id
		}
	return HttpResponse(json.dumps(ret))

@transaction.atomic
def receive_batch(request):
	saved_sample = request.GET.get('saved_sample')
	tr_code_id = request.GET.get('tr_code_id')
	env_id = request.GET.get('env_id')
	current_tr_code = request.GET.get('current_tr_code')
	if current_tr_code is None:
		current_tr_code = ''
	if request.method == 'POST':
		pst = request.POST
		sample_reception_form = SampleReceptionForm(pst)
		tr_code_id = request.POST.get('tracking_code_id')
		env_id = request.POST.get('envelope_id')
		saved_id = request.POST.get('saved_id')		
		if request.POST.get('facility') is None:
			sample_reception_form.add_error('facility_id','The facility is required')
			ret = {
				'saved_sample': s.id,
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				'err_msg':'Please select the facility'
			}
		
		sanitized_art_no = utils.removeSpecialCharactersFromString(request.POST.get('reception_art_number'))
		unique_id = "%s-A-%s" %(request.POST.get('facility'), sanitized_art_no)
		#return HttpResponse(unique_id)
		facility_pat = FacilityPatient.objects.filter(unique_id=unique_id).first()
		fac_pat = facility_pat if facility_pat else None
		#save the sample and its first identifier
		
		
		if saved_id:
			mg = saved_id
			s = Sample.objects.get(pk=saved_id)
			s.reception_art_number = request.POST.get('reception_art_number')
			s.reception_art_number = request.POST.get('reception_art_number')
			s.facility_patient = fac_pat
			s.save()
		else:
			s = Sample(tracking_code_id = tr_code_id,locator_category = request.POST.get('locator_category'),locator_position=request.POST.get('the_position'),
			barcode=request.POST.get('the_barcode'),created_by =request.user,
			date_received = request.POST.get('date_received'),form_number=request.POST.get('the_barcode'),reception_art_number = request.POST.get('reception_art_number'),facility_id = request.POST.get('facility'),
			sample_type=request.POST.get('sample_type'),envelope_id = env_id,facility_patient = fac_pat)
			s.save()
		
			#save the corresponding verification object
			#v = Verification.objects.filter(sample=s).first()
			v = Verification()
			v.pat_edits = 0
			v.sample_edits = 0
			v.sample = s
			
			v.accepted = True 		
			v.rejection_reason_id = None

			v.verified_by = request.user
			v.save()
		ret = {
				'saved_sample': s.id,
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':s.barcode,
				'err_msg':'',
				'mg': mg
			}

		return HttpResponse(json.dumps(ret))
		#return redirect('/samples/receive_batch?saved_sample=%s&tr_code_id=%s&env_id=%s&current_tr_code=%s' %(s.pk, tr_code_id,env_id,pst.get('code')))
		#else:

			#sample_reception_form.add_error('barcode', 'Saving failed')
	else:
		d = datetime.now()
		sample_reception_form = SampleReceptionForm(initial={'locator_category':'V', 'date_received': datetime.now().date()})

	context = {
		'sample_reception_form': sample_reception_form,
		'tr_code_id': tr_code_id,
		'env_id':env_id,
		'current_tr_code':current_tr_code,
		'reception_id':'',
	}

	if saved_sample:
		sample = Sample.objects.filter(pk=saved_sample).first()
		context.update({'sample':sample,'tr_code_id':tr_code_id,'env_id':env_id,})

	return render(request, 'samples/receive_bactch.html', context)

@permission_required('samples.change_sample', login_url='/login/')
def edit_received(request, reception_id):
	if request.method == 'POST':
		accepted = request.POST.get('locator_category')
		rejection_reason_id = request.POST.get('rejection_reason_id')
		if(accepted=='R' and not rejection_reason_id):
			return HttpResponse("rejection reason required for rejected samples")
		tr = TrackingCode.objects.filter(code= request.POST.get('code')).first()
		if tr is None:
			tr = TrackingCode()
			tr.code = request.POST.get('code')
			tr.creation_by_id = request.user.id
			tr.save()
		sample_reception = Sample.objects.get(pk=reception_id)
		if sample_reception:
			sample_reception.facility_id = request.POST.get('facility')
			sample_reception.date_received = request.POST.get('date_received')
			sample_reception.reception_art_number = request.POST.get('reception_art_number')
			sample_reception.tracking_code_id = tr.id
			sample_reception.save()
			return redirect("/samples/show/%d" %sample_reception.pk)
	else:
		sample_reception = Sample.objects.get(pk=reception_id)
		context = {
			'sample_reception_form':SampleReceptionForm(instance=sample_reception),
			'current_tr_code':sample_reception.tracking_code.code,
			'reception_id':reception_id,
			'locator_category':sample_reception.locator_category,
			'reception_art_number':sample_reception.reception_art_number,
		}
		return render(request, 'samples/receive.html', context)

@permission_required('samples.change_sample', login_url='/login/')
def edit(request, sample_id):
	sample = Sample.objects.get(pk=sample_id)
	patient = sample.patient
	count_dr = 0
	drug_resistance = None
	date_received = sample.date_received
	try:
		drug_resistance = sample.drugresistancerequest
		count_dr = PastRegimens.objects.filter(drug_resistance_request=drug_resistance).count()
	except :
		pass
	
	
	PastRegimensFormSet = modelformset_factory(PastRegimens, form=PastRegimensForm, 
							extra=(5-count_dr))

	if request.method == 'POST':
		pst = request.POST
		intervene = request.POST.get('intervene')
		patient_form = PatientForm(request.POST, instance=patient)
		sample_form = SampleForm(request.POST, instance=sample)
		drug_resistance_form = DrugResistanceRequestForm(request.POST, instance=drug_resistance)
		past_regimens_formset =PastRegimensFormSet(request.POST)

		valid_patient = patient_form.is_valid()
		valid_sample = sample_form.is_valid()
		valid_dr = drug_resistance_form.is_valid()
		valid_past_regimens = past_regimens_formset.is_valid()

		null_dob = pst.get('null_dob')

		if not pst.get('dob') and not null_dob:
			patient_form.add_error('dob', 'Date is blank')

		elif not pst.get('date_collected'):
			sample_form.add_error('date_collected', 'Collection date cannot be blank')
		elif not sample_utils.collection_date_valid(pst):
			sample_form.add_error('date_collected','sample collection date cannot be < DoB')
		elif sample_utils.locator_id_exists(request.POST, sample_id):
			sample_form.add_error('locator_position', 'Duplicate Locator ID')
		elif not sample_utils.initiation_date_valid(request.POST):
			patient_form.add_error('treatment_initiation_date', 'Initiation date can not be < DoB')

		elif valid_patient  and valid_sample and valid_dr and valid_past_regimens:
			
			patient = patient_form.save(commit=False)
			patient.facility_id = request.POST.get('facility')
			patient.save()

			sample = sample_form.save(commit=False)
			sample.updated_by = request.user

			facility = patient.facility			
			
			sample.sample_medical_lab = utils.user_lab(request)
			sample.save()
			
			if 'has_dr' in request.POST:
				drug_resistance = drug_resistance_form.save(commit=False)
				drug_resistance.sample = sample
				drug_resistance.save()

				past_regimens = past_regimens_formset.save(commit=False)
				for past_regimen in past_regimens:
					past_regimen.drug_resistance_request = drug_resistance
					past_regimen.save()

			if intervene=='results':
				sample.result.resultsqc.released = True
				sample.result.resultsqc.save()
				return redirect("/results/intervene_list/")
			elif intervene=='rejects':
				sample.rejectedsamplesrelease.released = True
				sample.rejectedsamplesrelease.save()
				return redirect("/samples/intervene_list/")


			return redirect("/samples/show/%d" %sample.pk)
		else:
			sample_form.add_error('locator_position', 'Updating failed')

	else:
		intervene = request.GET.get('intervene')
		envelope_form = EnvelopeForm(instance=sample.envelope)
		phone_form = PatientPhoneForm()
		patient_form = PatientForm(instance=patient)
		sample_form = SampleForm(instance=sample)
		drug_resistance_form = DrugResistanceRequestForm(instance=drug_resistance)
		past_regimens_formset = PastRegimensFormSet(queryset=PastRegimens.objects.filter(drug_resistance_request=drug_resistance))
		facilities = Facility.objects.values('id','facility')

	context = {
		'sample_id': sample_id,
		#'envelope_form': envelope_form,
		#'phone_form': phone_form,
		'patient_form': patient_form,
		'sample_form': sample_form,
		'vsi': sample.vl_sample_id,
		'drug_resistance_form': drug_resistance_form,
		'past_regimens_formset': past_regimens_formset,
		'facilities': Facility.objects.all(),
		'regimens': Appendix.objects.filter(appendix_category=3),
		'intervene': intervene,
		'date_received': date_received,
		'facilities':Facility.objects.values('id','facility'),
	}
		
	return render(request, 'samples/create.html', context)


def does_form_number_exist(request, form_number):
	if Sample.objects.filter(form_number = form_number).exists():
		return HttpResponse(form_number)
	else:
		return HttpResponse('')

def get_district_hub(request, facility_id):
	district_hub = sample_utils.get_district_hub_by_facility(facility_id)
	return HttpResponse(district_hub)
def get_patient(request):

	#district_hub = sample_utils.get_district_hub_by_facility(facility_id)
	facility_id = request.GET.get('facility_id')
	art_number = request.GET.get('art_number')

	ret = {}
	#for now turn off this feature
	#return HttpResponse(json.dumps(ret))
	unique_id = "%s-A-%s" %(facility_id, art_number.replace(' ','').replace('-','').replace('/',''))
	patient = Patient.objects.filter( Q(facility_id=facility_id,unique_id=unique_id)).order_by('created_at').last()
	if patient:
		treatment_initiation = ''
		if patient.treatment_initiation_date:
			treatment_initiation = patient.treatment_initiation_date.strftime("%d/%m/%Y").__str__()
		dob = ''
		if patient.dob:
			dob = patient.dob.strftime("%d/%m/%Y").__str__()
		ret = {
			'patient_id':patient.id,
			#'art_number': patient.art_number,
			#.__str__() converts date to string so that serialization might work
			'treatment_initiation_date':treatment_initiation,
			'dob': dob,
			'gender':patient.gender,
			'other_id':patient.other_id,
			}
	return HttpResponse(json.dumps(ret))

def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()

def get_barcode_details(request):
	barcode = request.GET.get('barcode')
	ret = []
	sample = Sample.objects.filter(id__gte=5000000,barcode=barcode).first()
	if sample:
		rec_date = sample.date_received
		ret = {
			'reception_facility': sample.facility_id,
			's_id': sample.id,
			'is_data_entered': sample.is_data_entered,
			'reception_art_number': sample.reception_art_number,
			'date_received': "{}-{}-{}".format(rec_date.year, rec_date.month, rec_date.day)
			}
	
	return HttpResponse(json.dumps(ret))

def show(request, sample_id):
	sample = Sample.objects.get(pk=sample_id)
	patient = sample.patient
	envelope = sample.envelope
	drug_resistance = None
	try:
		drug_resistance = sample.drugresistancerequest
	except :
		pass

	PastRegimensFormSet = modelformset_factory(PastRegimens, form=PastRegimensForm)

	context = {
		'clinician_form': ClinicianForm(instance=sample.clinician),
		'lab_tech_form': LabTechForm(instance=sample.lab_tech),
		'sample_id': sample_id,
		'envelope_form': EnvelopeForm(instance=sample.envelope),
		'phone_form': PatientPhoneForm(),
		'patient_form': PatientForm(instance=patient),
		'sample_form': SampleForm(instance=sample),
		'drug_resistance_form': DrugResistanceRequestForm(instance=drug_resistance),
		'past_regimens_formset': PastRegimensFormSet(queryset=PastRegimens.objects.filter(drug_resistance_request=drug_resistance)),
		'vl_sample_id': sample.vl_sample_id,
	}

	return render(request, 'samples/show.html', context)

def list(request):
	search_val = request.GET.get('search_val')
	is_data_entered = request.GET.get('is_data_entered')

	# if search_val:
	# 	samples = Sample.objects.filter(
	# 				Q(form_number__icontains=search_val)|
	# 				Q(vl_sample_id__icontains=search_val)|
	# 				sample_utils.locator_cond(search_val)
	# 				).order_by('-pk')[:1]
	# 	if samples:
	# 		sample = samples[0]
	# 		return redirect('/samples/show/%d' %sample.pk)

	return render(request, 'samples/list.html', {'global_search':search_val,'is_data_entered':is_data_entered })

def update_patient_parent(request):
	parent_patients = Patient.objects.filter(is_the_clean_patient=1, facility_id=1526)[:100]
	cursor = connections['default'].cursor()
	for parent_patient in parent_patients:

		#assign update each patient with this facility_id and unique_id to all that don't have a parent

		patients_for_parent = Patient.objects.filter(unique_id=parent_patient.unique_id,facility_id=parent_patient.facility_id)
		if patients_for_parent.count > 0:
			for patient in patients_for_parent:
				#patient.parent_id = parent_patient.id
				connections['default'].cursor().execute("UPDATE vl_patients SET parent_id=%s WHERE id=%s",[parent_patient.id,patient.id])
				#patient.save()
	return HttpResponse('done')

def pending_verification_list(request):
	search_val = request.GET.get('search_val')
	if request.method == 'POST':
		patient_id = request.POST.get('patient_id')
		p_type = request.POST.get('type')
		patient = Patient.objects.get(pk=patient_id)
		if patient:
			if(p_type == 'new'):
				patient.is_verified = 1
				patient.parent_id = patient_id
				#add other conditions here
				patient.save()
				return HttpResponse(1)
			else:
				#get the patient for consideration
				art_number = request.POST.get('art_number')
				facility_id = request.POST.get('facility_id')
				unique_id = "%s-A-%s" %(facility_id, art_number.replace(' ','').replace('-','').replace('/',''))
				merge_old_patient = Patient.objects.filter(unique_id=unique_id,facility_id=facility_id).first()

				if merge_old_patient:
					#if transfered, create the historical record
					if p_type == 'transfer':
						patient_transfer_history = patientTransferHistory()
						patient_transfer_history.old_art_number = merge_old_patient.art_number
						patient_transfer_history.current_art_number = patient.art_number
						patient_transfer_history.old_facility_id  = merge_old_patient.facility_id
						patient_transfer_history.current_facility_id = patient.facility_id
						patient_transfer_history.created_at = dtime.now()
						patient_transfer_history.save()
						#assign the old patient the new art number
						merge_old_patient.art_number = patient.art_number
						merge_old_patient.save()


					#assign the sample to the right patient_id
					sample = Sample.objects.get(patient_id=patient.id)
					sample.patient_id = merge_old_patient.id
					sample.patient_id = merge_old_patient.id
					sample.facility_id = merge_old_patient.facility_id
					sample.save()

					patient.parent_id = merge_old_patient.id
					patient.is_verified = 2
					patient.save()
					return HttpResponse('done')
						#set the patient to be this merge_patient

	patients = Patient.objects.filter(is_verified=0)[:500]
	facilities = Facility.objects.values('id', 'facility').order_by('facility')
	facility_dropdown = utils.select( "facility_id",
									  {'k_col':'id', 'v_col':'facility', 'items':facilities })
	return render(request, 'samples/pending_verification_list.html', {'global_search':search_val,'patients':patients,'facilities':facilities})

def appendix_select(name="", cat_id=0, clss='form-control input-xs w-md'):
	apendices = Appendix.objects.values('id','appendix')
	more = {'class': clss}
	return utils.select(name,{'k_col':'id', 'v_col':'appendix', 'items':apendices.filter(appendix_category_id=cat_id)},"",more)

@permission_required('samples.add_verification', login_url='/login/')
def verify(request, sample_id):
	facilities = Facility.objects.values('id', 'facility').order_by('facility')
	sample = Sample.objects.get(pk=sample_id)
	context = {
		'sample_id':sample_id,
		'envelope_id': sample.envelope.pk,
		"rejection_reasons": RejectionReasons(sample.sample_type).rejection_reasons,
		"facilities": Facility.objects.all(),
		# "facility_dropdown": utils.select( "facility_id",
		# 								  {'k_col':'id', 'v_col':'facility', 'items':facilities },
		# 								  "",
		# 								  {'ng-model': 'v.facility_id'}),
	}
	return render(request, 'samples/verify.html', context)

@permission_required('samples.add_verification', login_url='/login/')
def get_rejection_reasons(request):
	ret = RejectionReasons(request.GET.get('sample_type')).rejection_reasons
	return HttpResponse(json.dumps(ret))

@permission_required('samples.add_verification', login_url='/login/')
def save_verify(request):
	r = request.POST
	bcode = r.get('barcode')
	if not bcode == "":
		if len(r.get('barcode')) > 14:
			return HttpResponse('the the barcode length should not be more than 14 characters long')
		used_barcode = TempUsedBarcode.objects.filter(barcode=r.get('barcode')).first()
		if used_barcode:
			return HttpResponse('Barcode assigned to '+used_barcode.form_number)
	pat_edits = int(r.get('pat_edits'))
	sample_edits = int(r.get('sample_edits'))
	if(pat_edits>0):
		p = Patient.objects.get(pk=r.get('patient_id'))
		p.art_number = r.get('art_number', '')
		p.other_id = r.get('other_id', '')
		p.dob = utils.get_date(r, 'dob')
		p.gender = r.get('gender', '')
		p.save()

	s = Sample.objects.get(pk=r.get('sample_id'))
	if sample_edits>0:

		facility_id = r.get('facility_id')
		if facility_id:
			s.facility_id = facility_id
		s.form_number = r.get('form_number')
		s.date_collected = utils.get_date(r, 'date_collected')
		s.treatment_initiation_date = utils.get_date(r, 'treatment_initiation_date')
		s.locator_category = r.get('locator_category', '')
		s.locator_position = r.get('locator_position', '')
		tx = r.get('treatment_duration')
		s.treatment_duration = tx if tx else None

	s.verified = 1
	s.barcode = r.get('barcode')
	s.save()

	if s.in_worksheet:
		return HttpResponse("sample in worksheet already")

	v = Verification.objects.filter(sample=s).first()
	v = v if v else Verification()
	v.pat_edits = pat_edits
	v.sample_edits = sample_edits
	v.sample = s
	accepted = int(r.get('accepted',0))
	v.accepted = True if accepted == 1 else False
	if(v.accepted==False):
		v.rejection_reason_id = r.get('rejection_reason_id')
		if not v.rejection_reason_id:
			return HttpResponse("rejection reason required for rejected samples")
	else:
		v.rejection_reason_id = None

	v.verified_by = request.user
	v.save()
	#mark barcode used
	if not bcode == "":
		used_barcode = TempUsedBarcode()
		used_barcode.barcode = r.get('barcode')
		used_barcode.form_number = s.form_number
		used_barcode.save()

	if(not Sample.objects.filter(envelope=s.envelope, verified=False).count()):
		envelope = Envelope.objects.get(pk=s.envelope.pk)
		envelope.stage = 2
		envelope.save()

	return HttpResponse("saved")


@permission_required('samples.add_verification', login_url='/login/')
def verify_list(request):
	search_val = request.GET.get('search_val')
	verified = request.GET.get('verified')
	context = {
		'verified':verified,
		'global_search':search_val,
	}
	if(verified=='0'):
		context.update({
			'pending': Sample.objects.filter(created_at__gte=date(settings.LIST_CUT_OFF_YEAR, settings.LIST_CUT_OFF_MONTH,settings.LIST_CUT_OFF_DATE),verified=False,envelope__sample_medical_lab=request.user.userprofile.medical_lab_id).count(),
			'pending_dbs': Sample.objects.filter(created_at__gte=date(settings.LIST_CUT_OFF_YEAR, settings.LIST_CUT_OFF_MONTH,settings.LIST_CUT_OFF_DATE),verified=False, sample_type='D',envelope__sample_medical_lab=request.user.userprofile.medical_lab_id).count(),
			'pending_plasma': Sample.objects.filter(created_at__gte=date(settings.LIST_CUT_OFF_YEAR, settings.LIST_CUT_OFF_MONTH,settings.LIST_CUT_OFF_DATE),verified=False, sample_type='P',envelope__sample_medical_lab=request.user.userprofile.medical_lab_id).count(),
			})
	else:
		context.update({
			'completed': Sample.objects.filter(verified=True,envelope__sample_medical_lab=request.user.userprofile.medical_lab_id).count(),
			'completed_dbs': Sample.objects.filter(verified=True, sample_type='D',envelope__sample_medical_lab=request.user.userprofile.medical_lab_id).count(),
			'completed_plasma': Sample.objects.filter(verified=True, sample_type='P',envelope__sample_medical_lab=request.user.userprofile.medical_lab_id).count(),
			})
	# if search_val:
	# 	envelopes = Envelope.objects.filter(envelope_number__contains=search_val).order_by('-pk')[:1]
	# 	if envelopes:
	# 		envelope = envelopes[0]
	# 		return redirect('/samples/verify/%d' %envelope.pk)

	return render(request, "samples/verify_list.html", context)
@permission_required('samples.add_verification', login_url='/login/')
def verify_envelope(request, envelope_id):
	samples = Sample.objects.filter(envelope_id=envelope_id).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"}).order_by('lposition_int')

	ret=[]
	for s in samples:
		facility = s.facility if hasattr(s, 'facility') else ''
		hub = facility.hub if hasattr(facility, 'hub') else ''
		hub_name = hub.hub if hasattr(hub, 'hub') else ''
		district = facility.district if hasattr(facility, 'district') else ''
		district_name = district.district if hasattr(district, 'district') else ''
		ret.append({
				'patient_id': s.patient.id,
				'sample_id': s.id,
				'accepted': "%s"%int(s.verification.accepted) if hasattr(s, 'verification') else '',
				'vl_sample_id': s.vl_sample_id,
				'locator_category': s.locator_category,
				'locator_position': s.locator_position,
				'envelope_number': s.envelope.envelope_number,
				'loc':"%s%s/%s"  %(s.locator_category, s.envelope.envelope_number, s.locator_position),
				'form_number': s.form_number,
				'sample_type':s.sample_type,
				'facility_id': str(s.facility_id),
				'facility_name': facility.facility if hasattr(facility, 'facility') else '',
				'district': district_name,
				'hub': hub_name,
				'date_collected': utils.local_date(s.date_collected),
				'art_number': s.patient.art_number,
				'other_id': s.patient.other_id,
				'gender': s.patient.gender,
				'barcode': s.barcode,
				'dob': utils.local_date(s.patient.dob),
				'treatment_initiation_date': utils.local_date(s.treatment_initiation_date),
				'treatment_duration':"%s"%(s.treatment_duration) if s.treatment_duration else "",
				'sample_creator': s.created_by.username,
				'created_at': utils.local_date(s.created_at),
			})
	return HttpResponse(json.dumps(ret))



def appendices_json(cat_id):
	appendices = Appendix.objects.values('id', 'appendix').filter(appendix_category_id=cat_id)
	ret={}
	for a in appendices:
		ret[a['id']] = a['appendix']
	return json.dumps(ret)

def pat_hist(request, facility_id):
	ret = []
	#ret = [{'art_number':art_number, 'test_date':'2017-01-01', 'result':'TND'}, {'art_number':art_number, 'test_date':'2017-04-01', 'result':'TND'}]
	art_number = request.GET.get('art_number')
	if art_number == '':
		return HttpResponse(json.dumps(ret))
	unique_id = "%s-A-%s" %(facility_id, art_number.replace(' ','').replace('-','').replace('/',''))
	samples = Sample.objects.filter( Q(patient__unique_id=unique_id)|Q(facility_id=facility_id,patient__art_number=art_number)).order_by('-date_collected')[:3]

	for s in samples:
		ret.append({
				'form_number': s.form_number,
				'date_collected': utils.local_date(s.date_collected),
				'art_number': s.patient.art_number,
				'other_id': s.patient.other_id,
				'gender': s.patient.gender,
				'dob': utils.local_date(s.patient.dob),
				'result':"%s"%s.result.result_alphanumeric if hasattr(s, 'result') else '',
				'test_date':utils.local_date(s.result.test_date) if hasattr(s, 'result') else '',
			})

	return HttpResponse(json.dumps(ret))

def clinicians(request, facility_id):
	clinicians = Clinician.objects.filter(facility=facility_id).order_by('-pk')
	ret = []
	for c in clinicians:
		ret.append({'name':c.cname, 'phone':c.cphone})

	return HttpResponse(json.dumps(ret))

def lab_techs(request, facility_id):
	lab_techs = LabTech.objects.filter(facility=facility_id).order_by('-pk')
	ret = []
	for l in lab_techs:
		ret.append({'name':l.lname, 'phone':l.lphone})

	return HttpResponse(json.dumps(ret))

def release_rejects(request):
	if request.method == 'POST':
		sample = Sample.objects.get(pk=request.POST.get('sample_pk'))
		choice = request.POST.get('choice')
		released = 1 if choice == 'release' else 3

		comments = request.POST.get('comments')

		other_params = {
			'released': released,
			'comments': request.POST.get('comments'),
			'reject_released_by': request.user,
			'released_at': datetime.now().date(),
		}
		rsr, rsr_created = RejectedSamplesRelease.objects.update_or_create(sample=sample, defaults=other_params)
		return HttpResponse("saved")
	else:
		date_rejected_fro = request.GET.get('date_rejected_fro',dt.today().strftime("%Y-%m-1"))
		date_rejected_to = request.GET.get('date_rejected_to',dt.today().strftime("%Y-%m-%d"))

		released = request.GET.get('released', '0')
		if released == '3':
			rlsd = 3
		else:
			rlsd = True if released=='1' else None

		rejects = Verification.objects.filter(accepted=False, sample__rejectedsamplesrelease__released=rlsd,  sample__date_received__gte=date_rejected_fro, sample__date_received__lte=date_rejected_to)
		context = {	'rejects':rejects,
					'date_rejected_fro':date_rejected_fro,
					'date_rejected_to':date_rejected_to,
					'released':released,}

		#return HttpResponse(context['reject_released_by'])
		return render(request, "samples/release_rejects.html", context)

@permission_required('results.add_result', login_url='/login/')
def received(request):
	samples = Sample.objects.filter(created_at__gte=date(settings.LIST_CUT_OFF_YEAR, settings.LIST_CUT_OFF_MONTH,settings.LIST_CUT_OFF_DATE),is_data_entered=0).order_by('-created_at')[:1000]
	context = {'samples': samples}
	return render(request, 'samples/received_samples.html', context)


def intervene_list(request):
	intervene_rejects = RejectedSamplesRelease.objects.filter(released=False,sample__envelope__sample_medical_lab=utils.user_lab(request))[:500]
	return render(request, 'samples/intervene_list.html', {'intervene_rejects':intervene_rejects})

def search(request):
	cond = Q()
	search = request.GET.get('search_val')
	approvals = request.GET.get('approvals')
	search_env = request.GET.get('search_env')
	if search:
		search = search.strip()
		if search_env:
			env = Envelope.objects.filter(sample_utils.env_cond(search)).first()
			search = search.replace("-","")
			samples = Sample.objects.filter(envelope=env).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"})[:300]
		else:
			if search.isdigit() or search[:-1].isdigit():
				#fn_cond = Q(form_number=search)
				#samples = Sample.objects.filter(fn_cond)
				#return HttpResponse(samples)
				samples = Sample.objects.filter(form_number=search)
				#return HttpResponse(samples)
			else:
				fn_cond = Q(form_number__icontains=search)
				loc_cond = sample_utils.locator_cond(search)
				cond = fn_cond | loc_cond if loc_cond else fn_cond
				samples = Sample.objects.filter(cond).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"})[:300]
	else:
		samples = None
	return render(request, 'samples/search.html', {'samples':samples, 'approvals':approvals})

def envelope_list(request):
	return render(request, 'samples/envelope_list.html')

def generate_forms(request):
	if request.method == 'POST':
		pst = request.POST
		dispatch = ClinicalRequestFormsDispatch()
		dispatch.ref_number = sample_utils.generate_ref_number()
		dispatch.dispatched_at = pst.get('dispatched_at')
		dispatch.dispatched_by = request.user
		dispatch.facility_id = pst.get('facility_id')
		dispatch.save()

		start = int(pst.get('start'))
		length = int(pst.get('length'))
		for form_number in xrange(start, start+length):
			request_form = ClinicalRequestForm()
			request_form.form_number = form_number
			request_form.dispatch = dispatch
			request_form.save()

		return redirect("/samples/forms/?ref_number=%s"%dispatch.ref_number)
	else:
		facilities = Facility.objects.all()
		facility_select = utils.select2("facility_id", {'k_col':'id', 'v_col':'facility', 'items':facilities.values() }, "", {'id':'id_facility'})
		return render(request, "samples/generate_forms.html", {'facility_select':facility_select})

def forms(request):
	search = request.GET.get('search_val') or request.GET.get('ref_number')
	forms = None
	if search:
		forms = ClinicalRequestForm.objects.filter(Q(dispatch__ref_number=search)|Q(form_number=search))

	return render(request, "samples/forms.html", {'forms':forms})

def edit_dispatch(request, dispatch_id):
	dispatch = ClinicalRequestFormsDispatch.objects.get(pk=dispatch_id)
	if  request.method == 'POST':
		pst = request.POST
		dispatch.facility_id = pst.get('facility_id')
		dispatch.save()
		return redirect("/samples/forms/?ref_number=%s"%dispatch.ref_number)
	else:
		forms = dispatch.clinicalrequestform_set.all().order_by('form_number')
		facilities = Facility.objects.all()
		facility_select = utils.select2("facility_id", {'k_col':'id', 'v_col':'facility', 'items':facilities.values() }, "", {'id':'id_facility'})

		context = {
			'first':forms.first().form_number,
			'last':forms.last().form_number,
			'dispatch':dispatch,
			'facility_select':facility_select,
		}
		return render(request, "samples/edit_dispatch.html", context)

def facility_art_numbers(request, facility_id):
	facility_samples = Sample.objects.filter(facility=facility_id).order_by('-pk')
	ret = []
	for s in facility_samples:
		if s.patient.art_number not in ret:
			ret.append(s.patient.art_number)
	return HttpResponse(json.dumps(ret))
	#return HttpResponse(ret)
def reverse_approval(request, verification_id):
	#/samples/search/?search_val=1602-1267&approvals=1&env_complete=1
	verification = Verification.objects.filter(pk=verification_id).first()
	sample = verification.sample
	ra = "Reverse approval failed"
	if sample.in_worksheet:
		ra = "Reverse approval not possible because the sample is already in a worksheet"
	else:
		if verification:
			sample.verified = False
			sample.save()
			verification.delete()
			ra = "Reverse approval successful"

	return redirect("/samples/search/?search_val=%s&approvals=1&reverse_approval=%s"%(request.GET.get("search_val"), ra))

@permission_required('samples.view_reports', login_url='/login/')
def download(request, path):
	#folder = "reports/drug_resistance" if request.GET.get('dr') else "reports"
	if request.GET.get('dr'):
		folder = "reports/drug_resistance"
	elif request.GET.get('detectables'):
		folder = "reports/detectables"
	elif request.GET.get('cohort'):
		folder = settings.MEDIA_ROOT
	else:
		folder = "reports"

	file_path = os.path.join(settings.MEDIA_ROOT, "%s/%s"%(folder,path))
	if os.path.exists(file_path):
		with open(file_path, 'rb') as fh:
			response = HttpResponse(fh.read(), content_type="application//x-zip-compressed")
			response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
			return response
	else:
		return HttpResponse("report missing")

@permission_required('samples.view_reports', login_url='/login/')
def reports(request):
	#reports = os.listdir("media/reports/")
	if request.GET.get('dr'):
		path = os.path.join(settings.MEDIA_ROOT, "reports/drug_resistance/")
	elif request.GET.get('detectables'):
		path = os.path.join(settings.MEDIA_ROOT, "reports/detectables/")
	else:
		path = os.path.join(settings.MEDIA_ROOT, "reports/")

	reports = []
	for r in glob.glob("%s*.zip"%path):
		stats = os.stat(r)
		last_modified = datetime.fromtimestamp(stats.st_mtime)
		size = round(stats.st_size/1000000.0,1)
		report = os.path.basename(r)
		period = "%s, %s" %(calendar.month_abbr[int(report[4:6])], report[0:4])
		reports.append({'report':report, 'period':period, 'last_modified':last_modified, 'size':size})
	return render(request,'samples/reports.html', {'reports': reports})

class RejectionReasons(Appendix):
	"""docstring for RejectionReason"""
	data_quality = {}
	sample_quality = {}
	eligibility = {}
	rejection_reasons = {}

	def __init__(self, sample_type):
		for r in Appendix.objects.filter(appendix_category=4, tag__startswith=sample_type):
			if 'data_quality' in r.tag:
				self.data_quality.update({r.pk:r.appendix})
			elif 'sample_quality' in r.tag:
				self.sample_quality.update({r.pk:r.appendix})
			elif 'eligibility' in r.tag:
				self.eligibility.update({r.pk:r.appendix})

		self.rejection_reasons = json.dumps({
			'data_quality':self.data_quality,
			'sample_quality':self.sample_quality,
			'eligibility':self.eligibility})
