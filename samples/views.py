import json, os, glob, calendar
import csv, pandas, io, json
from datetime import *
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.http import JsonResponse
from django.db.models import Q
from django import *

from backend.models import Appendix,Facility,MedicalLab
from .models import *
from django.forms import formset_factory
from django.forms import *
from .forms import *
from home import utils
from home import programs
from home import db_aliases
from . import utils as sample_utils
from django.db import connections
from django.db import transaction
from worksheets.models import Worksheet,WorksheetSample
from results.models import Result,ResultsQC
from . import utils as worksheet_utils
import requests
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .services import SampleService
from vl import services as vl_services

ENVS_LIMIT = 1000
SAMPLES_LIMIT = 1000


def update_envelope_program_code(envelope_id, program_code):
	if envelope_id and program_code:
		Envelope.objects.filter(pk=envelope_id).update(program_code=program_code)


def posted_date(post_data, field_name):
	return utils.get_date(post_data, field_name)


def _posted_sample_type(request):
	sample_type = request.POST.get('sample_type')
	if sample_type in (None, '', 'None'):
		return None
	return sample_type


def _set_missing_sample_type(sample, request):
	if sample.sample_type not in (None, ''):
		return
	sample_type = _posted_sample_type(request)
	if sample_type:
		sample.sample_type = sample_type


def _set_sample_type_from_request_or_envelope(sample, request, envelope_id=None):
	_set_missing_sample_type(sample, request)
	if sample.sample_type not in (None, ''):
		return
	resolved_envelope_id = envelope_id or sample.envelope_id
	if not resolved_envelope_id:
		return
	envelope = sample.envelope if sample.envelope_id == resolved_envelope_id and getattr(sample, 'envelope', None) else None
	if envelope is None:
		envelope = Envelope.objects.filter(pk=resolved_envelope_id).only('sample_type').first()
	if envelope and envelope.sample_type:
		sample.sample_type = envelope.sample_type


def get_session_program_code(request):
	code = programs.get_active_program_code(request)
	return int(code) if code else None


def get_dropdown_db_alias(request):
	return db_aliases.get_program_db_alias(programs.get_active_program_code(request))


def get_facilities_qs(request):
	return Facility.objects.using(get_dropdown_db_alias(request)).values('id', 'facility')


def get_regimens_qs(request):
	return Appendix.objects.using(get_dropdown_db_alias(request)).filter(appendix_category=3)


def bind_past_regimens_formset(formset, db_alias):
	for form in formset.forms:
		if 'regimen' in form.fields:
			form.fields['regimen'].queryset = Appendix.objects.using(db_alias).filter(appendix_category_id=3)
	return formset


def get_program_label(program_code):
	theme = programs.PROGRAM_THEMES.get(str(program_code or ''), {})
	return theme.get('label', 'Unknown program')


def get_program_mismatch_message(request, actual_program_code, item_label='sample'):
	active_program_code = get_session_program_code(request)
	if not active_program_code or not actual_program_code:
		return ''
	if int(active_program_code) == int(actual_program_code):
		return ''
	return 'This %s belongs to %s, but your active program is %s. Switch program to continue.' % (
		item_label,
		get_program_label(actual_program_code),
		get_program_label(active_program_code),
	)


def get_sample_program_code(sample):
	if sample and getattr(sample, 'program_code', None):
		return int(sample.program_code)
	if sample and sample.envelope_id and sample.envelope and sample.envelope.program_code:
		return int(sample.envelope.program_code)
	return None


def lock_envelope_to_session_program(request, envelope_id):
	active_program_code = get_session_program_code(request)
	if not envelope_id or not active_program_code:
		return ''
	envelope = Envelope.objects.filter(pk=envelope_id).first()
	if envelope is None:
		return ''
	if envelope.program_code:
		return get_program_mismatch_message(request, envelope.program_code, 'envelope')
	update_envelope_program_code(envelope_id, active_program_code)
	return ''

@permission_required('samples.add_sample', login_url='/login/')
@transaction.atomic
def create(request):
	facilities = get_facilities_qs(request)
	saved_sample = request.GET.get('saved_sample')
	page_type = request.GET.get('page_type')
	PastRegimensFormSet = modelformset_factory(PastRegimens, PastRegimensForm, extra=5)
	treatment_indication_options = utils.TREATMENT_INFO_OPTIONS
	treatment_indication_selected_options = ''
	selected_treatment_ids = ''
	
	if request.method == 'POST':
		return handle_post_request(request, facilities, PastRegimensFormSet,treatment_indication_options,treatment_indication_selected_options,selected_treatment_ids)
	else:
		return handle_get_request(request, facilities, saved_sample, page_type, PastRegimensFormSet,treatment_indication_options,treatment_indication_selected_options,selected_treatment_ids)

def handle_post_request(request, facilities, PastRegimensFormSet,treatment_indication_options,treatment_indication_selected_options,selected_treatment_ids):
    pst = request.POST.copy()
    db_alias = get_dropdown_db_alias(request)
    patient_form = PatientForm(pst)
    envelope_form = EnvelopeForm(pst)
    preliminary_findings_form = PreliminaryFindingsForm(pst)
    sample_id = pst.get('id')
    sample_instance = None
    page_type = pst.get('page_type')
    if sample_id:
    	sample_instance = Sample.objects.filter(pk=sample_id).first()
    	sample_form = SampleForm(pst, instance=sample_instance, db_alias=db_alias)
    else:
    	sample_form = SampleForm(pst, db_alias=db_alias)
    drug_resistance_form = DrugResistanceRequestForm(pst)
    past_regimens_formset = bind_past_regimens_formset(PastRegimensFormSet(pst), db_alias)
   
    if SampleService.validate_forms(patient_form, preliminary_findings_form,envelope_form, sample_form, drug_resistance_form, past_regimens_formset, pst):
    	if vl_services.is_hiv_program(request):
    		try:
    			save_result = vl_services.save_sample_form(pst, request.user)
    			next_barcode = save_result.get('next_barcode')
    			if request.POST.get('from_page') == 'verify':
    				return redirect("/samples/verify_list/?verified=0")
    			elif request.POST.get('results_qc_id'):
    				return redirect("/results/dr_results/")
    			elif request.POST.get('from_page') == 'approvals':
    				return redirect("/samples/search/?search_val=%s&search_env=1&approvals=1" % pst.get('envelope_number'))
    			elif next_barcode:
    				return redirect('/samples/create?barcode=%s&page_type=%s' % (next_barcode, pst.get('page_type')))
    			return redirect('/samples/create?page_type=%s' % pst.get('page_type'))
    		except Exception as e:
    			sample_form.add_error('barcode', str(e))
    			return render_create_page(request, facilities, envelope_form, patient_form, preliminary_findings_form,sample_form, drug_resistance_form, past_regimens_formset, page_type)

    	sample = Sample.objects.filter(pk=pst.get('id')).first()
    	#response_data = save_form_using_external_api(pst,request.user.id,sample)
    	#status = response_data.get("status")
    	#if int(status) == 200:
    	#	next_barcode = sample_utils.get_next_barcode(sample.barcode,sample.sample_type)
    	#	return redirect('/samples/create?saved_sample=%s&barcode=%s&page_type=%s' % (sample.pk,next_barcode,pst.get('page_type')))
    	#else:
    	#	return HttpResponse('bikyagaanye')
    	try:
    		patient = SampleService.create_patient(patient_form, pst, request.user)
    		preliminary_findings = SampleService.create_preliminary_finidings(preliminary_findings_form,patient, pst, request.user)
    		sample = SampleService.update_sample(sample_form, pst, patient, request.user)
    		SampleService.create_drug_resistance(drug_resistance_form, pst, past_regimens_formset, sample)
    		next_barcode = sample_utils.get_next_barcode(sample.barcode,sample.sample_type)
    		
    		if request.POST.get('from_page') == 'verify':
    			return redirect("/samples/verify_list/?verified=0")
    		elif request.POST.get('results_qc_id'):
    			return redirect("/results/dr_results/")
    		elif request.POST.get('from_page') == 'approvals':
    			return redirect("/samples/search/?search_val=%s&search_env=1&approvals=1" %sample.envelope.envelope_number)
    		elif next_barcode:
    			return redirect('/samples/create?saved_sample=%s&barcode=%s&page_type=%s' % (sample.pk,next_barcode,pst.get('page_type')))
    		else:
    			return redirect('/samples/create?saved_sample=%s&page_type=%s' % (sample.pk,pst.get('page_type')))
    	except Exception as e:
    		print(e)
    		return HttpResponse(e)
    		sample_form.add_error('barcode', 'An error occurred while saving the sample. Please try again. Check if reception entered art number')
    		return render_create_page(request, facilities, envelope_form, patient_form, preliminary_findings_form,sample_form, drug_resistance_form, past_regimens_formset, page_type)
    else:
    	sample_form.add_error('form_number', 'Saving failed due to validation errors')
    	return render_create_page(request, facilities, envelope_form, patient_form, preliminary_findings_form,sample_form, drug_resistance_form, past_regimens_formset, page_type)

def save_form_using_external_api(pst,user_id,sample):
	form_data = pst.dict()
	form_data["created_by_id"]=user_id
	form_data["data_entered_by_id"]=user_id
	sanitized_art_no = utils.removeSpecialCharactersFromString(pst.get('hep_number'))
	unique_id = "%s-A-%s" %(pst.get('facility'), sanitized_art_no)
	form_data["sanitized_hep_number"]=sanitized_art_no
	form_data["unique_id"]=unique_id
	needs_verification = sample_utils.is_rec_and_entery_data_mataching(sample,pst.get('hep_number'),pst.get('facility'))
	sample.required_verification = needs_verification
	if needs_verification == 1:
		verified = 0
		required_verification = 1
	else:
		verified = 1
		required_verification = 0
	form_data["verified"] = verified
	form_data["required_verification"] = required_verification

	external_api_url = "http://localhost:8000/api/save_vl_form/"
	
	headers = {
		"User-Agent": "Django-App",
		"Content-Type": "application/json"
	}
	try:
		# Make the POST request
		response = requests.post(external_api_url, json=form_data, headers=headers,timeout=10,proxies={"http": None, "https": None})
		##response.raise_for_status()  # Raise an error for HTTP errors
		# Convert response to JSON
		response_data = response.json()
		# Extract the ID
		#sample_id = response_data.get("id")  # Assuming the API returns {"id": 123, "message": "Success"}
		return response_data
		#if sample_id:
		#	response_json = {"message": "User created successfully", "id": sample_id,"status":200}
		#else:
		#	response_json = {"error": "ID not found in response", "details": response_data,"status":400}
	except requests.Timeout:
		response_json = {"error": "Request timed out", "status":408}
		return response_json
	#except requests.RequestException as e:
	#	response_json = {"error": "API request failed", "details": str(e), "status":500}
	
	#print("Response Data:", response_json)
	#return JsonResponse(response_json, status=200 if "id" in response_json else 500)


def handle_get_request(request, facilities, saved_sample, page_type, PastRegimensFormSet,treatment_indication_options,treatment_indication_selected_options,selected_treatment_ids):
    barcode = ''
    db_alias = get_dropdown_db_alias(request)
    if request.GET.get('barcode'):
    	barcode = request.GET.get('barcode')

    envelope_form = EnvelopeForm(initial={'envelope_number': sample_utils.initial_env_number()})
    patient_form = PatientForm
    preliminary_findings_form = PreliminaryFindingsForm
    sample_form = SampleForm(initial={'barcode': barcode,'locator_category': 'V', 'date_collected': datetime.now().strftime("%d/%m/%Y")}, db_alias=db_alias)
    drug_resistance_form = DrugResistanceRequestForm
    past_regimens_formset = bind_past_regimens_formset(PastRegimensFormSet(queryset=PastRegimens.objects.none()), db_alias)
    return render_create_page(request, facilities, envelope_form, patient_form,preliminary_findings_form, sample_form, drug_resistance_form, past_regimens_formset, page_type,treatment_indication_options,treatment_indication_selected_options,selected_treatment_ids)

def render_create_page(request, facilities, envelope_form, patient_form, preliminary_findings_form,sample_form, drug_resistance_form, past_regimens_formset, page_type='',treatment_indication_options=None,treatment_indication_selected_options=None,selected_treatment_ids=None):
    pending_entry = PendingEntryQueue.objects.all()
    sample = ''
    saved_sample = request.GET.get('saved_sample')
    if saved_sample:
    	sample = Sample.objects.filter(pk=saved_sample).first()
    context = {
        'envelope_form': envelope_form,
        'patient_form': patient_form,
        'sample_form': sample_form,
        'drug_resistance_form': drug_resistance_form,
        'past_regimens_formset': past_regimens_formset,
        'regimens': get_regimens_qs(request),
        'facilities': facilities,
        'null_dob': None,
		'null_treatment_initiation_date':None,
		'facilities':facilities,
		'page_type':page_type,
		'sample':sample,
		'pending_entry':pending_entry,
		'pending_entry_count':len(pending_entry),
		'min_no_envelopes_pending':settings.MIN_NO_ENVELOPES_PENDING,
		'treatment_indication_options': utils.TREATMENT_INFO_OPTIONS,
		'preliminary_findings_form' : preliminary_findings_form,
    }
    return render(request, 'samples/create.html', context)

@permission_required('samples.add_sample', login_url='/login/')

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
	
	
@transaction.atomic
def receive(request):
	if vl_services.is_hiv_program(request):
		if request.method == 'POST':
			try:
				sample = vl_services.receive_sample(request.POST, request.user)
				return redirect('/samples/receive?saved_sample=%s&env_id=%s&current_tr_code=%s' % (
					sample.id,
					sample.envelope_id,
					request.POST.get('code', ''),
				))
			except Exception as e:
				form = SampleReceptionForm(request.POST)
				form.add_error('barcode', str(e))
				context = {
					'sample_reception_form': form,
					'tr_code_id': request.POST.get('tracking_code_id'),
					'env_id': request.POST.get('envelope_id'),
					'current_tr_code': request.POST.get('current_tr_code'),
					'reception_id': '',
					'locator_category': request.POST.get('locator_category', ''),
					'reception_hep_number': request.POST.get('reception_hep_number', ''),
					'facility_reference': request.POST.get('facility_reference', ''),
					'form_data': request.POST,
				}
				return render(request, 'samples/receive.html', context)
		form = SampleReceptionForm(initial={'locator_category':'V', 'date_collected': datetime.now().date(), 'date_received': datetime.now().date()})
		return render(request, 'samples/receive.html', {
			'sample_reception_form': form,
			'tr_code_id': request.GET.get('tr_code_id'),
			'env_id': request.GET.get('env_id'),
			'current_tr_code': request.GET.get('current_tr_code'),
			'reception_id':'',
			'locator_category':'',
			'reception_hep_number': '',
			'facility_reference': '',
			'form_data':'',
		})

	saved_sample = request.GET.get('saved_sample')
	tr_code_id = request.GET.get('tr_code_id')
	page_type = request.GET.get('page_type')
	env_id = request.GET.get('env_id')
	current_tr_code = request.GET.get('current_tr_code')

	if request.method == 'POST':
		form_data = request.POST
		pst = request.POST
		accepted = pst.get('locator_category')
		rejection_reason_id = pst.get('rejection_reason_id')
		page_type = pst.get('page_type')
		if(accepted=='R' and not rejection_reason_id):
			return HttpResponse("rejection reason required for rejected samples")

		sample_reception_form = SampleReceptionForm(pst)
		#valid_sample = sample_reception_form.is_valid()
		#return HttpResponse(valid_sample)
		#if valid_sample:
		tr_code_id = request.POST.get('tracking_code_id')
		env_id = sample_utils.get_envelope_id(request)
		session_program_code = get_session_program_code(request)
		if env_id is None:
			sample_reception_form.add_error('barcode', 'Envelope was not found, did you accession it?')
		else:
			mismatch_message = lock_envelope_to_session_program(request, env_id)
			if mismatch_message:
				sample_reception_form.add_error('barcode', mismatch_message)
		if sample_reception_form.is_valid():
			date_collected = sample_reception_form.cleaned_data.get('date_collected')
			if tr_code_id == ''  or (current_tr_code != '' and pst.get('code') != current_tr_code) :
				tr = TrackingCode.objects.filter(code=pst.get('code')).first()
				if tr is None:
					tr = TrackingCode()
					tr.code = pst.get('code')
					tr.creation_by_id = request.user.id
					tr.save()

					#updat sample tracking with details receipt
					data = {
					"barcode":pst.get('code'),
		            "user_id":1,
		            "numberofsamples":4,
		            "is_tracked_from_facility":0,
		            "transfer_to":settings.REF_LAB_ID,
		            "ref_lab_id":settings.REF_LAB_ID,
		            "is_to_be_transfered":0,
		            "receipt_date":"",
		            "name_of_receiver":"Kakembo John"
					}
					
				tr_code_id = tr.id
			#get the facility_patient
			#save the sample and its first identifier

			sanitized_art_no = utils.removeSpecialCharactersFromString(request.POST.get('reception_hep_number'))
			unique_id = "%s-A-%s" %(request.POST.get('facility'), sanitized_art_no)
			#return HttpResponse(unique_id)
			facility_pat = FacilityPatient.objects.filter(unique_id=unique_id).first()
			fac_pat = facility_pat if facility_pat else None
			facility_ref = request.POST.get('facility_reference')
			facility_reference = None if facility_ref == '' else facility_ref
			form_number = request.POST.get('barcode') if facility_ref == '' else facility_ref

			if pst.get('locator_category') == 'R':
				stage = 7
			else: 
				stage = 0
			s = ''
			if facility_reference is  not None:
				s = Sample.objects.filter(facility_reference=facility_reference).first()
			if s:
				s.tracking_code_id = tr_code_id
				s.locator_category = request.POST.get('locator_category')
				s.envelope_id = env_id
				s.verified = 1
				s.stage = 0
				s.locator_position=request.POST.get('locator_position')
				s.barcode=request.POST.get('barcode')
				s.date_collected = date_collected
				#s.date_received = request.POST.get('date_received')
				s.date_received = datetime.now()
				s.received_by = request.user
				if session_program_code:
					s.program_code = session_program_code
				s.save()
			else:
				s = Sample(tracking_code_id = tr_code_id,locator_category = request.POST.get('locator_category'),locator_position=request.POST.get('locator_position'),
					barcode=request.POST.get('barcode'),created_by =request.user,stage=stage,
					form_number=form_number,facility_id = request.POST.get('facility'),
					sample_type=request.POST.get('sample_type'),date_collected=date_collected,date_received=datetime.now(), envelope_id = env_id,received_by = request.user,reception_hep_number=request.POST.get('reception_hep_number'),facility_reference=facility_reference,facility_patient = fac_pat,verified=0)
				if session_program_code:
					s.program_code = session_program_code
				s.save()

			update_envelope_program_code(env_id, get_session_program_code(request))
			sample_utils.update_envelope_status(s,'received')
			#save the corresponding verification object
			v = Verification()
			v.pat_edits = 0
			v.sample_edits = 0
			v.sample = s
			accepted = pst.get('locator_category')
			v.accepted = True if accepted == 'V' else False
			if(accepted=='R'):
				#save the patient object
				patient = Patient()
				patient.facility_id = request.POST.get('facility')
				patient.hep_number=request.POST.get('reception_hep_number')
				patient.created_by_id= request.user.id
				patient.save()
				v.rejection_reason_id = pst.get('rejection_reason_id')
				if not v.rejection_reason_id:
					return HttpResponse("rejection reason required for rejected samples")
				#release the rejection by default
				sample_utils.release_rejected_sample(s, request.user.id)
				s.verified = 1
				s.is_data_entered = 1
				s.patient = patient
				s.save()
			else:
				v.rejection_reason_id = None

			v.verified_by = request.user
			v.save()

			# if the sample has been tested, update it
			ws = WorksheetSample.objects.filter(instrument_id=s.barcode).first()
			if ws and ws.sample_id is None:
				ws.sample = s
				ws.save()				
			d_reception = s.envelope.created_at.strftime('%Y-%m-%d')
			return redirect('/samples/receive?saved_sample=%s&tr_code_id=%s&env_id=%s&current_tr_code=%s&date_received=%s&page_type=%s' %(s.pk, tr_code_id,env_id,pst.get('code'),d_reception,page_type))	
	else:
		form_data = ''
		d = datetime.now()
		sample_reception_form = SampleReceptionForm(initial={'locator_category':'V', 'date_collected': datetime.now().date(), 'date_received': datetime.now().date()})

	context = {
		'sample_reception_form': sample_reception_form,
		'tr_code_id': tr_code_id,
		'env_id':env_id,
		'current_tr_code':current_tr_code,
		'reception_id':'',
		'locator_category':'',
		'reception_hep_number': '',
		'facility_reference': '',
		'form_data':form_data
	}

	if saved_sample:
		sample = Sample.objects.filter(pk=saved_sample).first()
		context.update({'sample':sample,'tr_code_id':tr_code_id,'env_id':env_id,})

	return render(request, 'samples/receive.html', context)

@transaction.atomic
def reject_sample(request):
	rejection_reason_id = request.POST.get('rejection_reason_id')

	sample_identifier_id = request.POST.get('sample_identifier_id')
	worksheet_id = request.POST.get('worksheet_id')
	if sample_identifier_id:
		worksheet_id = request.POST.get('worksheet_id')
		ws = WorksheetSample.objects.get(pk=request.POST.get('ws_id'))
		ws.stage = 7
		ws.save()

		s = Sample.objects.get(pk=sample_identifier_id)
		s.rejected_by_id = request.user.id
		s.stage = 7
		s.rejected_at = datetime.now().date()
		s.save()
		
	
	if rejection_reason_id and s.id:
		v = Verification.objects.filter(sample_id=s.id).first()
		if not v:
			v = Verification()
			v.sample_id = s.id
		v.accepted = False		
		v.rejection_reason_id = request.POST.get('rejection_reason_id')
		if not v.rejection_reason_id:
			return HttpResponse("rejection reason required for rejected samples")
		v.verified_by = request.user
		v.save()
		v.sample.locator_category = 'R'
		v.sample.save()
	return redirect("/worksheets/show/%d" %int(worksheet_id))

def get_envelope_details(request):
	envelope_number = request.GET.get('envelope_number')
	if vl_services.is_hiv_program(request):
		return HttpResponse(json.dumps(vl_services.get_envelope_details(envelope_number)))
	ret = []
	envelope = Envelope.objects.filter(id__gte=settings.ENVELOPE_SAMPLES_CUT_OFF,envelope_number=envelope_number).first()
	if envelope is None:
		envelope = Envelope.objects.filter(envelope_number=envelope_number).first()
	env_status_update = request.GET.get('env_status_update')
	env_id = ''
	date_received = ''
	err_msg = ''
	program_mismatch = False
	if envelope:
		err_msg = get_program_mismatch_message(request, envelope.program_code, 'envelope')
		if err_msg:
			program_mismatch = True
		else:
			env_id = envelope.id
			update_env_status(envelope,env_status_update)
			date_received = envelope.created_at.strftime('%Y-%m-%d')
	else:
		err_msg = ''

	ret = {
		'envelope_id': env_id,
		'date_received':date_received,
		'program_mismatch': program_mismatch,
		'err_msg': err_msg,
		'program_code': envelope.program_code if envelope else ''
		}
	return HttpResponse(json.dumps(ret))
def get_envelope_status_for_lab(request):
	envelope_number = request.GET.get('envelope_number')
	
	envelope = Envelope.objects.filter(id__gte=settings.ENVELOPE_SAMPLES_CUT_OFF,envelope_number=envelope_number).first()
	if envelope is None:
		#envelope was not received
		return HttpResponse(1)
	else:
		s_identifier = SampleIdentifier.objects.filter(env=envelope).first()
		if s_identifier is None:
			return HttpResponse(2)
		else:
			return HttpResponse(3)


def update_env_status(envelope,update_env_status):
	if update_env_status == 'has_result':
		envelope.has_result = 1
	if update_env_status == 'received':
		env_queue = PendingReceptionQueue.objects.filter(envelope = envelope).first()
		if env_queue:
			env_queue.delete()
		#update the data entry que - if has result
		if envelope.has_result and envelope.is_received == 0:
			does_exist = PendingEntryQueue.objects.filter(envelope = envelope).first()
			if does_exist is None:
				ent_queue = PendingEntryQueue()
				ent_queue.envelope = envelope
				ent_queue.envelope_number = envelope.envelope_number
				ent_queue.status = 1
				ent_queue.save()

	envelope.save()
	return True

def get_tracking_code_details(request):
	code = request.GET.get('code')
	if vl_services.is_hiv_program(request):
		tr = vl_services.get_or_create_tracking_code(code, request.user)
		return HttpResponse(json.dumps({'tracking_code_id': tr.id}))
	ret = []
	tr = TrackingCode.objects.filter(code=code).first()
	if tr is None:
		tr = TrackingCode()
		tr.code = code
		tr.creation_by_id = request.user.id
		tr.save()
		#now update the sample tracking system
		data = {
		"barcode":request.GET.get('code'),
        "user_id":1,
        "numberofsamples":1,
        "is_tracked_from_facility":0,
        "transfer_to":settings.REF_LAB_ID,
        "ref_lab_id":settings.REF_LAB_ID,
        "is_to_be_transfered":0,
        "receipt_date":"",
        "name_of_receiver":"Kakembo John"
		}
		#request_type = "POST"
		api_url = settings.SAMPLE_TRACKING_URL
		response = requests.request("POST", settings.SAMPLE_TRACKING_URL, data=data)
	
	ret = {
		'tracking_code_id': tr.id
		}
	return HttpResponse(json.dumps(ret))

@transaction.atomic
def receive_batch(request,ret_to_fun = 0):
	if vl_services.is_hiv_program(request):
		if request.method == 'POST' or ret_to_fun:
			try:
				sample = vl_services.receive_sample(request.POST, request.user)
				ret = {
					'saved_sample': sample.id,
					'env_id': sample.envelope_id,
					'tracking_code_id': sample.tracking_code_id,
					's_barcode': sample.barcode,
					'err_msg': '',
				}
				if ret_to_fun:
					return sample
				return HttpResponse(json.dumps(ret))
			except Exception as e:
				ret = {
					'saved_sample': '',
					'env_id': request.POST.get('envelope_id'),
					'tracking_code_id': request.POST.get('tracking_code_id'),
					's_barcode': request.POST.get('the_barcode', ''),
					'err_msg': str(e),
				}
				return HttpResponse(json.dumps(ret))
		saved_sample = request.GET.get('saved_sample')
		tr_code_id = request.GET.get('tr_code_id')
		env_id = request.GET.get('env_id')
		current_tr_code = request.GET.get('current_tr_code') or ''
		sample_reception_form = SampleReceptionForm(initial={'locator_category':'V', 'date_collected': datetime.now().date(), 'date_received': datetime.now().date()})
		context = {
			'sample_reception_form': sample_reception_form,
			'tr_code_id': tr_code_id,
			'env_id':env_id,
			'current_tr_code':current_tr_code,
			'reception_id':'',
			'pending_reception':[],
			'pending_reception_count':0,
			'min_no_envelopes_pending':settings.MIN_NO_ENVELOPES_PENDING,
			'envelope_samples': vl_services.get_envelope_samples(env_id),
			'last_received_barcode': request.GET.get('last_barcode', ''),
		}
		if saved_sample:
			sample = vl_services.get_adapted_sample(saved_sample)
			if sample and not env_id and sample.envelope_id:
				env_id = sample.envelope_id
			if sample and not tr_code_id and getattr(sample, 'tracking_code_id', None):
				tr_code_id = sample.tracking_code_id
			context.update({
				'sample': sample,
				'tr_code_id': tr_code_id,
				'env_id': env_id,
				'envelope_samples': vl_services.get_envelope_samples(sample.envelope_id if sample else env_id),
				'last_received_barcode': sample.barcode if sample and sample.barcode else request.GET.get('last_barcode', ''),
			})
		return render(request, 'samples/receive_bactch.html', context)
	
	saved_sample = request.GET.get('saved_sample')
	tr_code_id = request.GET.get('tr_code_id')
	env_id = request.GET.get('env_id')
	current_tr_code = request.GET.get('current_tr_code')
	patient_id = None
	if current_tr_code is None:
		current_tr_code = ''
	if request.method == 'POST' or ret_to_fun:
		pst = request.POST
		date_collected = posted_date(request.POST, 'date_collected')
		sample_reception_form = SampleReceptionForm(pst)
		tr_code_id = request.POST.get('tracking_code_id')
		env_id = sample_utils.resolve_posted_envelope_id(request)
		session_program_code = get_session_program_code(request)
		mismatch_message = lock_envelope_to_session_program(request, env_id)
		if mismatch_message:
			ret = {
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': request.POST.get('the_barcode', ''),
				'err_msg': mismatch_message,
			}
			return HttpResponse(json.dumps(ret))
		saved_id = request.POST.get('saved_id')		
		sample_only = request.POST.get('sample_only')
		facility_ref = request.POST.get('facility_reference')
		form_number = request.POST.get('barcode') if facility_ref == '' else facility_ref		
		if request.POST.get('facility') is None:
			sample_reception_form.add_error('facility','The facility is required')
			ret = {
				'saved_sample': '',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				'err_msg':'Please select the facility'
			}
		
		sanitized_art_no = utils.removeSpecialCharactersFromString(request.POST.get('reception_hep_number'))
		unique_id = "%s-A-%s" %(request.POST.get('facility'), sanitized_art_no)
		facility_pat = FacilityPatient.objects.filter(unique_id=unique_id).first()
		fac_pat = facility_pat if facility_pat else None
		#save the sample and its first identifier
		
		
		if saved_id:
			mg = saved_id
			s = Sample.objects.get(pk=saved_id)
			if not env_id and s.envelope_id:
				env_id = s.envelope_id
			s.tracking_code_id = tr_code_id
			s.locator_category = 'V'
			s.locator_position = request.POST.get('the_position')
			s.barcode = request.POST.get('the_barcode')
			s.reception_hep_number = request.POST.get('reception_hep_number')
			s.facility_id = request.POST.get('facility')
			_set_sample_type_from_request_or_envelope(s, request, env_id)
			s.facility_patient = fac_pat
			if session_program_code:
				s.program_code = session_program_code
			if env_id:
				s.envelope_id = env_id
			s.stage = 0
			s.date_collected = date_collected
			s.date_received = datetime.now()
			s.form_number = form_number
			s.facility_reference = facility_ref
			if sample_only:
				s.is_data_entered = 1
				s.verified = 1
			else:
				s.is_data_entered = 0
				s.verified = 0
			s.received_by = request.user
			s.save()
			update_envelope_program_code(env_id, get_session_program_code(request))
		else:
			if sample_only == '1':
				data_entered_val = 1
				verified = 1
				patient = Patient()
				patient.hep_number = request.POST.get('reception_hep_number')
				patient.facility_id = request.POST.get('facility')
				patient.created_by = request.user
				patient.save()
				patient_id = patient.id
			else:
				data_entered_val = 0
				verified = 0

			#if lab ran samples before reception, update the sample instead
			lab_sample = Sample.objects.filter(barcode=request.POST.get('the_barcode')).first()
			s = Sample(tracking_code_id = tr_code_id,locator_category = 'V',locator_position=request.POST.get('the_position'),
			barcode=request.POST.get('the_barcode'),created_by =request.user,date_received = datetime.now(),
			form_number=form_number,reception_hep_number = request.POST.get('reception_hep_number'),facility_id = request.POST.get('facility'),
			sample_type=_posted_sample_type(request),date_collected=date_collected,stage=0,is_data_entered=data_entered_val,patient_id=patient_id, received_by = request.user,envelope_id = env_id,facility_patient = fac_pat,verified=verified,facility_reference = facility_ref)
			_set_sample_type_from_request_or_envelope(s, request, env_id)
			if session_program_code:
				s.program_code = session_program_code
			#if lab_sample:
				#s.id = lab_sample.id
			s.save()

		update_envelope_program_code(env_id, get_session_program_code(request))
		sample_utils.update_envelope_status(s,'received')

		#save the corresponding verification object
		sample_utils.save_verification_details(s,request)
		sample_utils.update_worksheet_sample(s)

		# if the sample has been tested, updated it
		sample_utils.update_result_models(s)
		if ret_to_fun:
			return s	
		ret = {
				'saved_sample': s.id,
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':s.barcode,
				'err_msg':''
			}

		return HttpResponse(json.dumps(ret))

	else:
		d = datetime.now()
		sample_reception_form = SampleReceptionForm(initial={'locator_category':'V', 'date_collected': datetime.now().date(), 'date_received': datetime.now().date()})

	pending_reception = PendingReceptionQueue.objects.all()
	context = {
		'sample_reception_form': sample_reception_form,
		'tr_code_id': tr_code_id,
		'env_id':env_id,
		'current_tr_code':current_tr_code,
		'reception_id':'',
		'pending_reception':pending_reception,
		'pending_reception_count':pending_reception.count(),
		'min_no_envelopes_pending':settings.MIN_NO_ENVELOPES_PENDING,
		'envelope_samples': [],
		'last_received_barcode': request.GET.get('last_barcode', ''),
	}
	
	if saved_sample:
		sample = Sample.objects.filter(pk=saved_sample).first()
		if sample and not env_id and sample.envelope_id:
			env_id = sample.envelope_id
		if sample and not tr_code_id and sample.tracking_code_id:
			tr_code_id = sample.tracking_code_id
		envelope_samples = sample.envelope.sample_set.all().order_by('locator_position') if sample and sample.envelope_id else []
		context.update({'sample':sample,'tr_code_id':tr_code_id,'env_id':env_id,'envelope_samples': envelope_samples,'last_received_barcode': sample.barcode if sample and sample.barcode else request.GET.get('last_barcode', '')})
	elif env_id:
		envelope = Envelope.objects.filter(pk=env_id).first()
		context.update({'envelope_samples': envelope.sample_set.all().order_by('locator_position') if envelope else []})

	return render(request, 'samples/receive_bactch.html', context)
	
@transaction.atomic
def receive_hie(request):
	
	saved_sample = request.GET.get('saved_sample')
	tr_code_id = request.GET.get('tr_code_id')
	env_id = request.GET.get('env_id')
	current_tr_code = request.GET.get('current_tr_code')
	facility_reference = request.GET.get('facility_reference')
	if facility_reference is not None:
		if vl_services.is_hiv_program(request):
			return HttpResponse(json.dumps(vl_services.get_receive_hie_details(facility_reference)))
		
		s = Sample.objects.filter(facility_reference=facility_reference).first()
		mismatch_message = get_program_mismatch_message(request, get_sample_program_code(s), 'sample')
		if mismatch_message:
			hep_number = ''
			date_collected = ''
			err_msg = mismatch_message
		elif s and s.patient_id and s.date_received is None:
			hep_number = s.patient.hep_number
			date_collected = s.date_collected.strftime('%Y-%m-%d') if s.date_collected else ''
			err_msg = ''
		elif s and s.date_received is not None:
			hep_number = ''
			date_collected = ''
			err_msg = 'Already received'
		else:
			hep_number = ''
			date_collected = ''
			err_msg = 'Not found'
		ret = {
			'hep_number': hep_number,
			'date_collected': date_collected,
			'err_msg': err_msg
		}
		return HttpResponse(json.dumps(ret))

	if current_tr_code is None:
		current_tr_code = ''
	if request.method == 'POST':
		pst = request.POST
		date_collected = posted_date(request.POST, 'date_collected')
		sample_reception_form = SampleReceptionForm(pst)
		tr_code_id = request.POST.get('tracking_code_id')
		facility_reference = request.POST.get('facility_reference')
		env_id = int(request.POST.get('envelope_id'))
		mismatch_message = lock_envelope_to_session_program(request, env_id)
		if mismatch_message:
			ret = {
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': request.POST.get('the_barcode'),
				'receipt_type': 'not_allowed',
				'err_msg': mismatch_message
			}
			return HttpResponse(json.dumps(ret))
		hep_number = request.POST.get('reception_hep_number')
		saved_id = request.POST.get('saved_id')				
		
		#s = Sample.objects.filter(Q(facility_reference=facility_reference) | Q(form_number=facility_reference)).first()
		s = Sample.objects.filter(facility_reference=facility_reference).first()
		sample_program_mismatch = get_program_mismatch_message(request, get_sample_program_code(s), 'sample')
		if sample_program_mismatch:
			ret = {
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': request.POST.get('the_barcode'),
				'receipt_type': 'not_allowed',
				'err_msg': sample_program_mismatch
			}
			return HttpResponse(json.dumps(ret))
				
		if s and s.date_received is None:
			s.tracking_code_id = tr_code_id
			s.locator_category = 'V'
			s.envelope_id = env_id
			s.verified = 1
			s.is_data_entered = 1
			s.stage = 0
			s.locator_position=request.POST.get('the_position')
			s.barcode=request.POST.get('the_barcode')
			s.sample_type=request.POST.get('sample_type')
			s.date_collected = date_collected
			#s.date_received = request.POST.get('date_received')
			s.date_received = datetime.now()
			s.received_by_id = request.user.id
			s.save()
			update_envelope_program_code(env_id, get_session_program_code(request))
			sample_utils.save_verification_details(s,request)

			ws = WorksheetSample.objects.filter(other_instrument_id=s.barcode).first()
			if ws:
				#if ws.sample is None:
				ws.sample = s
				ws.sample_type=request.POST.get('sample_type')
				ws.save()
			ret = {
				'saved_sample': s.id,
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':s.barcode,
				'receipt_type':'hie',
				'err_msg':'saved'
			}
		elif s and s.date_received is not None:
			#save as normal sample
			ret = {
				'saved_sample': '',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':s.barcode,
				'receipt_type':'not_allowed',
				'err_msg':'on'+s.barcode
			}
		elif hep_number is not None and hep_number != '':
			#save as normal sample
			s = receive_batch(request,1)
			ret = {
				'saved_sample': s.id,
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':s.barcode,
				'receipt_type':'non_hie',
				'err_msg':'saved, non HIE'
			}
		
		else:
			ret = {
				'saved_sample': '',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':request.POST.get('the_barcode'),
				'receipt_type':'not_at_all',
				'err_msg':'not found'
			}

		return HttpResponse(json.dumps(ret))
		
	else:
		d = datetime.now()
		sample_reception_form = SampleReceptionForm(initial={'locator_category':'V', 'date_collected': datetime.now().date(), 'date_received': datetime.now().date()})

	context = {
		'sample_reception_form': sample_reception_form,
		'tr_code_id': tr_code_id,
		'env_id':env_id,
		'current_tr_code':current_tr_code,
		'reception_id':'',
	}

	if saved_sample:
		sample = Sample.objects.filter(pk=saved_sample).first()
		#return HttpResponse(sample)
		context.update({'sample':sample,'tr_code_id':tr_code_id,'env_id':env_id,})

	return render(request, 'samples/receive_hie.html', context)

@transaction.atomic
def create_range(request):		
	users = User.objects.all()
	if vl_services.is_hiv_program(request):
		if request.method == 'POST':
			try:
				vl_services.create_range(request.POST, request.user)
				return redirect('/samples/create_range/')
			except Exception as e:
				return HttpResponse(str(e), status=400)
		return render(request, 'samples/create_range.html', {
			'users':users,
			'years': range(int((datetime.now().strftime('%y')))-1, int((datetime.now().strftime('%y')))+1),
			'months': utils.get_months(),
			'logged_in_user_id': request.user.id,
		})
	if request.method == 'POST':
		year_month = request.POST.get('year')+request.POST.get('month')
		l_limit = int(request.POST.get('lower_limit'))
		u_limit = int(request.POST.get('upper_limit'))
		number_of_envs = (u_limit - l_limit) + 1
		if number_of_envs <= 0:
			return HttpResponse('Upper limit must be greater than or equal to lower limit', status=400)
		sample_type = request.POST.get('sample_type')
		program_code = request.POST.get('program_code')
		now = datetime.now()
		env_range = EnvelopeRange()
		env_range.year_month = year_month	
		env_range.lower_limit = request.POST.get('lower_limit')	
		env_range.upper_limit = request.POST.get('upper_limit')	
		env_range.sample_type = sample_type	
		env_range.accessioned_by_id = request.POST.get('accessioned_by')	
		#env_range.accessioned_at = request.POST.get('accessioned_at')	
		env_range.accessioned_at = now.date()	
		env_range.entered_by = request.user	
		env_range.created_at = now
		env_range.save()

		for lim in range(l_limit, u_limit + 1):
			env_number = year_month+'-'+str(lim).zfill(4)
			envelope = Envelope.objects.select_for_update().filter(envelope_number=env_number).first()
			if envelope is None:
				envelope = Envelope(envelope_number=env_number)

			envelope.sample_type = sample_type
			envelope.program_code = program_code
			envelope.accessioned_at = now
			envelope.envelope_range = env_range
			envelope.accessioner = request.user
			envelope.assignment_by = request.user
			envelope.save()

			EnvelopeAssignment.objects.get_or_create(
				the_envelope=envelope,
				assigned_to_id=request.user.id,
				assigned_by=request.user,
				type=1,
			)
			
	context = {
		'users':users,
		'years': range(int((datetime.now().strftime('%y')))-1, int((datetime.now().strftime('%y')))+1),
		'months': utils.get_months(),
		'logged_in_user_id': request.user.id,
	}
	
	return render(request, 'samples/create_range.html', context)

@permission_required('samples.change_sample', login_url='/login/')
def edit_received(request, reception_id):
	if request.method == 'POST':
		accepted = request.POST.get('locator_category')
		rejection_reason_id = request.POST.get('rejection_reason_id')
		facility_id = request.POST.get('facility')
		hep_number = request.POST.get('reception_hep_number')
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
			sample_reception.facility_id = facility_id
			sample_reception.reception_hep_number = hep_number
			sample_reception.date_collected = posted_date(request.POST, 'date_collected')
			sample_reception.tracking_code_id = tr.id
			if(accepted=='R'):
				sample_reception.verification.rejection_reason_id = rejection_reason_id
				sample_reception.verification.accepted = False
				sample_reception.locator_category = 'R'
			else:
				sample_reception.verification.rejection_reason_id = None
				sample_reception.verification.accepted = True
			sample_reception.verification.verified_by = request.user
			sample_reception.save()
			update_envelope_program_code(sample_reception.envelope_id, request.POST.get('program_code'))
			sample_reception.verification.save()
		if sample_reception.patient_id:
			sample_reception.patient.hep_number = hep_number
			sample_reception.patient.facility_id = facility_id
			unique_id = "%s-A-%s" %(facility_id, utils.removeSpecialCharactersFromString(hep_number))
			sample_reception.patient.unique_id = unique_id
			sample_reception.patient.save()
		return redirect("/samples/show/%d" %sample_reception.pk)
	else:
		sample_reception = Sample.objects.get(pk=reception_id)
		context = {
			'sample_reception_form':SampleReceptionForm(instance=sample_reception),
			'current_tr_code':sample_reception.tracking_code.code,
			'reception_id':reception_id,
			'locator_category':sample_reception.locator_category,
			'reception_hep_number':sample_reception.reception_hep_number,
			'facility_reference':sample_reception.facility_reference,
		}
		return render(request, 'samples/receive.html', context)

@permission_required('samples.change_sample', login_url='/login/')
def edit(request, sample_id):
	sample = Sample.objects.get(pk=sample_id)
	patient = sample.patient if sample.patient_id else Patient(
		facility_id=sample.facility_id,
		hep_number=sample.reception_hep_number,
	)
	count_dr = 0
	drug_resistance = None
	date_received = sample.date_received
	preliminary_findings_instance = None
	try:
		drug_resistance = sample.drugresistancerequest
		count_dr = PastRegimens.objects.filter(drug_resistance_request=drug_resistance).count()
	except :
		pass
	try:
		preliminary_findings_instance = PreliminaryFindings.objects.filter(patient_id=sample.patient_id).order_by('-id').first()
	except:
		pass
	
	PastRegimensFormSet = modelformset_factory(PastRegimens, form=PastRegimensForm, 
							extra=(5-count_dr))

	
	intervene = request.GET.get('intervene')
	envelope_form = EnvelopeForm(instance=sample.envelope)
	patient_form = PatientForm(instance=patient)
	preliminary_findings = PreliminaryFindingsForm(instance=preliminary_findings_instance)
	if patient:
		sample.facility = patient.facility
	db_alias = get_dropdown_db_alias(request)
	sample_form = SampleForm(instance=sample, db_alias=db_alias)
	drug_resistance_form = DrugResistanceRequestForm(instance=drug_resistance)
	past_regimens_formset = bind_past_regimens_formset(
		PastRegimensFormSet(queryset=PastRegimens.objects.filter(drug_resistance_request=drug_resistance)),
		db_alias,
	)
	facilities = get_facilities_qs(request)

	context = {
		'sample_id': sample_id,
		'patient_form': patient_form,
		'preliminary_findings': preliminary_findings,
		'preliminary_findings_form': preliminary_findings,
		'sample_form': sample_form,
		'vsi': sample.vl_sample_id,
		'drug_resistance_form': drug_resistance_form,
		'past_regimens_formset': past_regimens_formset,
		'facilities': facilities,
		'regimens': get_regimens_qs(request),
		'intervene': intervene,
		'date_received': date_received,
		'from_page': request.GET.get('from_page'),
		'page_type': 2,
		'facilities': facilities,
		'treatment_indication_options': utils.TREATMENT_INFO_OPTIONS,
		'selected_treatment_ids': '',
	}
		
	return render(request, 'samples/create.html', context)


def does_form_number_exist(request, form_number):
	if Sample.objects.filter(form_number = form_number).exists():
		#check if this is an HIE form
		#Sample.objects.get(form_number = form_number)
		#Sample.objects.filter(barcode = request.GET.get('barcode')).first()
		#return HttpResponse('truth is true')
		return HttpResponse(form_number)
	else:
		return HttpResponse('')

def get_district_hub(request, facility_id):
	district_hub = sample_utils.get_district_hub_by_facility(
		facility_id,
		get_dropdown_db_alias(request),
	)
	return HttpResponse(district_hub)

def get_patient(request):

	#district_hub = sample_utils.get_district_hub_by_facility(facility_id)
	facility_id = request.GET.get('facility_id')
	hep_number = request.GET.get('hep_number')
	#facility = Facility.objects.get(pk=facility_id)
	ret = {}
	#for now turn off this feature
	#return HttpResponse(json.dumps(ret))
	unique_id = "%s-A-%s" %(facility_id, hep_number.replace(' ','').replace('-','').replace('/',''))
	#patient = FacilityPatient.objects.filter( Q(facility_id=facility_id,unique_id=unique_id)).first()
	patient = Patient.objects.filter(unique_id=unique_id).order_by('-created_at').first()

	if patient:
		treatment_initiation = ''
		if patient.treatment_initiation_date:
			treatment_initiation = patient.treatment_initiation_date.strftime("%m/%d/%Y").__str__()
		dob = ''
		if patient.dob:
			dob = patient.dob.strftime("%m/%d/%Y").__str__()
		ret = {
			'patient_id':patient.id,
			'treatment_initiation_date':treatment_initiation,
			'dob': dob,
			'gender':patient.gender,
			'other_id':patient.other_id,
			'is_facility_clean': '',
			}
	else:
		ret = {
				'is_facility_clean': ''
			}
		
	return HttpResponse(json.dumps(ret))

def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()

def get_barcode_details(request):
	barcode = request.GET.get('barcode')
	ret = []
	sample = Sample.objects.filter(id__gte=settings.SAMPLES_CUT_OFF,barcode=barcode).first()
	if sample:
		#rec_date = sample.envelope.created_at
		rec_date = sample.created_at
		err_msg = get_program_mismatch_message(request, get_sample_program_code(sample), 'sample')
		ret = {
			'reception_facility': sample.facility_id,
			's_id': sample.id,
			'is_data_entered': sample.is_data_entered,
			'reception_hep_number': sample.reception_hep_number,
			'date_received': "{}-{}-{}".format(rec_date.year, rec_date.month, rec_date.day),
			'program_mismatch': bool(err_msg),
			'err_msg': err_msg,
			}
	
	return HttpResponse(json.dumps(ret))

def show(request, sample_id):
	sample = Sample.objects.get(pk=sample_id)
	patient = sample.patient if sample.patient_id else Patient(
		facility_id=sample.facility_id,
		hep_number=sample.reception_hep_number,
	)
	drug_resistance = None
	try:
		drug_resistance = sample.drugresistancerequest
	except :
		pass

	PastRegimensFormSet = modelformset_factory(PastRegimens, form=PastRegimensForm)

	context = {
		'sample_id': sample_id,
		
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
	sample_without_results = request.GET.get('sample_without_results')
	hie_samples_pending_reception = request.GET.get('hie_samples_pending_reception')

	return render(request, 'samples/list.html', {
		'global_search':search_val,
		'is_data_entered':is_data_entered,
		'sample_without_results':sample_without_results,
		'hie_samples_pending_reception':hie_samples_pending_reception,
	})

def update_patient_parent(request):
	parent_patients = Patient.objects.filter(is_the_clean_patient=1, facility_id=1526)[:100]
	cursor = connections['default'].cursor()
	for parent_patient in parent_patients:

		#assign update each patient with this facility_id and unique_id to all that don't have a parent

		patients_for_parent = Patient.objects.filter(unique_id=parent_patient.unique_id,facility_id=parent_patient.facility_id)
		if patients_for_parent.count > 0:
			for patient in patients_for_parent:
				connections['default'].cursor().execute("UPDATE vl_patients SET parent_id=%s WHERE id=%s",[parent_patient.id,patient.id])
				
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
				hep_number = request.POST.get('hep_number')
				facility_id = request.POST.get('facility_id')
				unique_id = "%s-A-%s" %(facility_id, hep_number.replace(' ','').replace('-','').replace('/',''))
				merge_old_patient = Patient.objects.filter(unique_id=unique_id,facility_id=facility_id).first()

				if merge_old_patient:
					#if transfered, create the historical record
					if p_type == 'transfer':
						patient_transfer_history = patientTransferHistory()
						patient_transfer_history.old_hep_number = merge_old_patient.hep_number
						patient_transfer_history.current_hep_number = patient.hep_number
						patient_transfer_history.old_facility_id  = merge_old_patient.facility_id
						patient_transfer_history.current_facility_id = patient.facility_id
						patient_transfer_history.created_at = datetime.now()
						patient_transfer_history.save()
						#assign the old patient the new art number
						merge_old_patient.hep_number = patient.hep_number
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
@transaction.atomic
def verify(request, sample_id):
	if request.method == 'POST':
		sample = Sample.objects.get(pk=sample_id)
		sample.verified = 1
		sample.verified_at = datetime.now().date()
		sample.verifier = request.user
		sample.save()
		#if there is a result, release it
		result = Result.objects.filter(sample_id=sample.id).first()
		if result is not None and result.resultsqc.released == 0:
			result.resultsqc.released = 1
			result.resultsqc.released_at = datetime.now()
			result.resultsqc.save()
		return HttpResponse('verified')
	else:
		return HttpResponse('not allowed')

@permission_required('samples.add_verification', login_url='/login/')
def remove(request, sample_id):
	sample = Sample.objects.get(pk=sample_id)
	#remove sample id from identifiers and worksheet samples
	#connections['default'].cursor().execute("UPDATE vl_sample_identifiers SET sample_id=null WHERE sample_id=%s",[sample.id])
	connections['default'].cursor().execute("DELETE from vl_worksheet_samples WHERE sample_id=%s",[sample.id])
	#now remove sample
	#return envelope to lab
	sample.envelope.is_lab_completed = 0
	sample.envelope.processed_by_id = None
	sample.envelope.save()
	ws = WorksheetSample.objects.filter(sample_id = sample.id).first()
	#is sample is hie, only remove from envelope otherwise delete
	if sample.facility_reference:
		sample.locator_position = None
		sample.locator_category = None
		sample.date_received = None
		sample.envelope_id = None
		sample.save()
	else:
		sample.delete() 

@permission_required('samples.delete_sampleapprovalstats', login_url='/login/')
@transaction.atomic
def switch_samples(request):
	r = request.POST
	env_id = r.get('env_id')
	if env_id is not None:
		#nullify barcode n locator_positions for samples on this envelope to avoid errors of duplication
		Sample.objects.filter(envelope_id=env_id).update(barcode=None,locator_position=None)
	new_barcode = r.get('new_barcode')
	sample_id = r.get('sample_id')
	if new_barcode:
		sample = Sample.objects.get(pk = sample_id)	
		sample.barcode = new_barcode
		sample.locator_position = r.get('locator_posn')
		#if data is not yet entered, nulify form_number to avoid cases of repeat form_number
		if sample.is_data_entered == 0:
			sample.form_number = None
		sample.save()

		if sample.facility_reference is None:
			print('fac ref is empty')
			ws = WorksheetSample.objects.filter(sample_id = sample_id).first()
			if ws:
				ws.instrument_id = new_barcode
				ws.save()
	return HttpResponse('saved')

@permission_required('samples.add_verification', login_url='/login/')
def detach_sample(request):
	s_id = request.POST.get('sample_id')
	sample = Sample.objects.get(pk=s_id)
	sample.locator_category =None
	sample.locator_position =None
	sample.date_received =None
	sample.barcode =None
	sample.save()
	ws = WorksheetSample.objects.filter(sample_id = sample_id).first()
	if ws:
		ws.other_instrument_id = None
		ws.save()
	return HttpResponse('detached')

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
	pat_edits = int(r.get('pat_edits'))
	sample_edits = int(r.get('sample_edits'))
	if(pat_edits>0):
		p = Patient.objects.get(pk=r.get('patient_id'))
		p.hep_number = r.get('hep_number', '')
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

	if(not Sample.objects.filter(envelope=s.envelope, verified=False).count()):
		envelope = Envelope.objects.get(pk=s.envelope.pk)
		envelope.stage = 2
		envelope.save()

	return HttpResponse("saved")


@permission_required('samples.add_verification', login_url='/login/')
def verify_list(request):
	r_tab = request.GET.get('tab')
	facility_id = request.GET.get('facility_id')
	verified = int(request.GET.get('verified'))
	envelope_id = request.GET.get('envelope_id')
	db_alias = get_dropdown_db_alias(request)
	facilities = Facility.objects.using(db_alias).all()
	if verified:
		filters = Q(verified = 1,is_data_entered = 1,required_verification = 1)
	else:
		filters = Q(verified = 0,is_data_entered = 1,envelope_id__isnull=False)
	if envelope_id:
		filters = filters & Q(envelope_id = envelope_id)
	
	if facility_id:
		filters = filters & Q(facility_id=int(facility_id))
	#return HttpResponse(filters)
	samples = programs.filter_queryset_by_program(request, Sample.objects.using(db_alias).filter(filters), 'program_code').order_by('barcode')
	
	page = request.GET.get('page', 1)
	paginator = Paginator(samples, 100)
	try:
		samples = paginator.page(page)
	except PageNotAnInteger:
		samples = paginator.page(1)
	except EmptyPage:
		samples = paginator.page(paginator.num_pages)
	context = {'samples':samples,'facilities':facilities}
	return render(request, 'samples/verify_list.html', context)

@permission_required('samples.add_verification', login_url='/login/')
def receive_package(request):
	r_tab = request.GET.get('tab')
	facility_id = request.GET.get('facility_id')
	verified = int(request.GET.get('verified'))
	envelope_id = request.GET.get('envelope_id')
	facilities = Facility.objects.all()
	
	filters = Q(status=0)|Q(status=1)|Q(status=2)
	if facility_id:
		filters = filters & Q(facility_id=int(facility_id))
	#return HttpResponse(filters)
	packages = TrackingCode.objects.filter(filters).order_by('code')
	
	page = request.GET.get('page', 1)
	paginator = Paginator(packages, 100)
	try:
		packages = paginator.page(page)
	except PageNotAnInteger:
		packages = paginator.page(1)
	except EmptyPage:
		packages = paginator.page(paginator.num_pages)
	context = {'packages':packages,'facilities':facilities}
	return render(request, 'samples/receive_package.html', context)

def verify_list_old(request):
	search_val = request.GET.get('search_val')
	verified = request.GET.get('verified')
	context = {
		'verified':verified,
		'global_search':search_val,
	}
	if(verified=='0'):
		pending_qs = programs.filter_queryset_by_program(request, Sample.objects.filter(created_at__gte=date(settings.LIST_CUT_OFF_YEAR, settings.LIST_CUT_OFF_MONTH,settings.LIST_CUT_OFF_DATE),verified=False,envelope__sample_medical_lab=request.user.userprofile.medical_lab_id), 'program_code')
		context.update({
			'pending': pending_qs.count(),
			'pending_dbs': pending_qs.filter(sample_type='D').count(),
			'pending_plasma': pending_qs.filter(sample_type='P').count(),
			})
	

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
				'hep_number': s.patient.hep_number,
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
	hep_number = request.GET.get('hep_number')
	if hep_number == '':
		return HttpResponse(json.dumps(ret))
	unique_id = "%s-A-%s" %(facility_id, hep_number.replace(' ','').replace('-','').replace('/',''))
	#samples = Sample.objects.filter( Q(patient__unique_id=unique_id)|Q(facility_id=facility_id,patient__hep_number=hep_number)).order_by('-date_collected')[:3]
	#samples = Sample.objects.filter( Q(patient__unique_id=unique_id)).order_by('-date_collected')[:3]
	#samples = Sample.objects.filter(Q(patient__unique_id=unique_id)).select_related('patient').only('form_number', 'date_collected', 'patient__hep_number', 'patient__other_id').order_by('-date_collected')[:3]

	samples = (
    Sample.objects
    .filter(patient__unique_id=unique_id)
    .select_related('patient')  # Joins patient data in single query
    .prefetch_related('result')  # Efficiently gets related results
    .only(  # Only fetch fields we actually use
        'form_number',
        'date_collected',
        'patient__hep_number',
        'patient__other_id',
        'patient__id',
        'patient__gender',
        'patient__dob'
    	).order_by('-date_collected')[:3]
	)
	
	# Prepare response data
	ret = []
	for s in samples:
		# Get result if it exists (already prefetched)
		result = getattr(s, 'result', None)
		ret.append({
	        'form_number': s.form_number,
	        'date_collected': utils.local_date(s.date_collected),
	        'hep_number': s.patient.hep_number,  # No additional query needed
	        'other_id': s.patient.other_id,
	        'patient_id': s.patient.id,
	        'gender': s.patient.gender,
	        'dob': utils.local_date(s.patient.dob),
	        'result': result.result_alphanumeric if result else '',
	        'test_date': utils.local_date(result.test_date) if result else '',
	    })
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
		date_rejected_fro = request.GET.get('date_rejected_fro',date.today().strftime("%Y-%m-1"))
		date_rejected_to = request.GET.get('date_rejected_to',date.today().strftime("%Y-%m-%d"))

		released = request.GET.get('released', '0')
		if released == '3':
			rlsd = 3
		else:
			rlsd = True if released=='1' else None

		rejects = programs.filter_queryset_by_program(request, Verification.objects.filter(accepted=False, sample__rejectedsamplesrelease__released=rlsd,  sample__date_received__gte=date_rejected_fro, sample__date_received__lte=date_rejected_to), 'sample__program_code')
		context = {	'rejects':rejects,
					'date_rejected_fro':date_rejected_fro,
					'date_rejected_to':date_rejected_to,
					'released':released,}

		return render(request, "samples/release_rejects.html", context)

@permission_required('results.add_result', login_url='/login/')
def received(request):
	samples = programs.filter_queryset_by_program(request, Sample.objects.filter(created_at__gte=date(settings.LIST_CUT_OFF_YEAR, settings.LIST_CUT_OFF_MONTH,settings.LIST_CUT_OFF_DATE),is_data_entered=0), 'program_code').order_by('-created_at')[:1000]
	context = {'samples': samples}
	return render(request, 'samples/received_samples.html', context)


def intervene_list(request):
	intervene_rejects = programs.filter_queryset_by_program(request, RejectedSamplesRelease.objects.filter(released=False,sample__envelope__sample_medical_lab=utils.user_lab(request)), 'sample__program_code')[:500]
	return render(request, 'samples/intervene_list.html', {'intervene_rejects':intervene_rejects})

def search(request):
	if vl_services.is_hiv_program(request):
		search = request.GET.get('search_val')
		approvals = request.GET.get('approvals')
		remove_sample = request.GET.get('remove_sample')
		switch_sample = request.GET.get('switch_sample')
		with_results = request.GET.get('with_results')
		search_env = request.GET.get('search_env')
		search_sample = request.GET.get('search_sample')
		samples = vl_services.search_samples(search, search_env=bool(search_env), search_sample=bool(search_sample))
		if switch_sample:
			return render(request, 'samples/switch_samples.html', {'samples':samples, 'approvals':approvals,'switch_sample':switch_sample,'envelope_id':''})
		elif with_results:
			return render(request, 'samples/with_results.html', {'samples':samples, 'approvals':approvals,'with_results':with_results,'envelope_id':''})
		return render(request, 'samples/search.html', {
			'samples':samples,
			'approvals':approvals,
			'remove_sample':remove_sample,
			'switch_sample':switch_sample,
		})
	cond = Q()
	search = request.GET.get('search_val')
	approvals = request.GET.get('approvals')
	remove_sample = request.GET.get('remove_sample')
	switch_sample = request.GET.get('switch_sample')
	with_results = request.GET.get('with_results')
	search_env = request.GET.get('search_env')
	search_sample = request.GET.get('search_sample')
	env_id = ''
	samples = None
	db_alias = get_dropdown_db_alias(request)
	if search:
		search = search.strip()
		if search_env:
			env = Envelope.objects.using(db_alias).filter(sample_utils.env_cond(search)).first()
			
			if env:
				env_id = env.id
				search = search.replace("-","")
				samples = Sample.objects.using(db_alias).filter(envelope=env).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"})

		else:
			if search_sample:
				direct_lookup = (
					sample_utils.exact_or_legacy_duplicate_cond('facility_reference', search) |
					sample_utils.exact_or_legacy_duplicate_cond('barcode', search) |
					sample_utils.exact_or_legacy_duplicate_cond('form_number', search)
				)
				samples = Sample.objects.using(db_alias).filter(direct_lookup).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"})

			else:
				fn_cond = Q(form_number__icontains=search)
				loc_cond = sample_utils.locator_cond(search)
				cond = fn_cond | loc_cond if loc_cond else fn_cond
				samples = Sample.objects.using(db_alias).filter(cond).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"})

	if samples is not None:
		filtered_samples = programs.filter_queryset_by_program(request, samples, 'program_code')
		if not search_sample or filtered_samples.exists():
			samples = filtered_samples
		samples = samples[:300]
	
	if switch_sample:
		return render(request, 'samples/switch_samples.html', {'samples':samples, 'approvals':approvals,'switch_sample':switch_sample,'envelope_id':env_id})
	elif with_results:
		return render(request, 'samples/with_results.html', {'samples':samples, 'approvals':approvals,'with_results':with_results,'envelope_id':env_id})
	else:
		return render(request, 'samples/search.html', {
			'samples':samples,
			'approvals':approvals,
			'remove_sample':remove_sample,
			'switch_sample':switch_sample,
		})

def envelope_list(request):
	return render(request, 'samples/envelope_list.html')


def facility_hep_numbers(request, facility_id):
	facility_samples = Sample.objects.filter(facility=facility_id).order_by('-pk')
	ret = []
	for s in facility_samples:
		if s.patient.hep_number not in ret:
			ret.append(s.patient.hep_number)
	return HttpResponse(json.dumps(ret))

def reverse_approval(request, verification_id):
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

def range_list(request):
	search_val = request.GET.get('search_val')
	return render(request, 'samples/range_list.html', {'global_search':search_val })

class RangeJson(BaseDatatableView):
	model = EnvelopeRange
	columns = ['year_month','lower_limit','upper_limit','sample_type','accessioned_by','accessioned_at','entered_by','links']
	order_columns = ['year_month','lower_limit','upper_limit']
	max_display_length = 500
					
	def render_column(self, row, column):
		if column == 'accessioned_by':
			return row.accessioned_by.first_name+' '+row.accessioned_by.last_name
		elif column == 'entered_by':
			return row.entered_by.first_name+' '+row.entered_by.last_name
		elif column == 'accessioned_at':
			return utils.set_page_date_only_format(row.accessioned_at)
		elif column =='links':
			links = utils.dropdown_links([
					{"label":"View envelopes","url":"/samples/range_envelopes/?type=1&range_id={0}".format(row.pk)},
					])
			return links
					
		else:
			return super(RangeJson, self).render_column(row, column)


	def filter_queryset(self, qs):
		search = self.request.GET.get(u'search[value]', None)
		global_search = self.request.GET.get('global_search', None)
		
		qs_params = Q()
		if search:
			qs_params = Q(year_month=search) | Q(lower_limit=search) | Q(upper_limit=search)
		return qs.filter(qs_params).order_by('year_month')		

@transaction.atomic
def range_envelopes(request):

	if request.method == 'POST':
		envelope_ids = request.POST.getlist('envelope_ids')
		p_type = request.POST.getlist('type')
		processor = int(request.POST.get('accessioner_id'))
		assignment_type = int(request.POST.get('type'))
		for env_id in envelope_ids:
			envelope = Envelope.objects.get(pk=env_id)
			if p_type == '1':
				envelope.accessioned_at = datetime.now().date()
				envelope.accessioner_id = processor
				envelope.assignment_by = request.user
			else:
				envelope.processed_by_id = processor				
				envelope.accessioned_at = datetime.now().date()
				envelope.lab_assignment_by = request.user
			envelope.save()

			env_assignment = EnvelopeAssignment()
			env_assignment.the_envelope = envelope
			env_assignment.assigned_to_id= processor
			env_assignment.type = assignment_type
			env_assignment.assigned_by = request.user
			env_assignment.save()
			if p_type == '1':
				return redirect('/samples/range_envelopes/?type=%s&range_id=%d' %(assignment_type,int(request.POST.get('range_id'))))				
			else:
				return redirect('/samples/range_envelopes/?type=%s&wksht_id=%d' %(assignment_type,int(request.POST.get('wksht_id'))))

	else:
		users = utils.get_users()
		range_id = request.GET.get('range_id') 
		wksht_id = request.GET.get('wksht_id')
		p_type = request.GET.get('type')
		if p_type == '1':
			envs = Envelope.objects.filter(envelope_range_id = int(range_id)).order_by('envelope_number')
		else:
			wksht_id = int(wksht_id)
			#envs = Envelope.objects.raw('SELECT envelope_number, e.id, processed_at FROM vl_worksheet_samples ws INNER JOIN vl_sample_identifiers si ON si.id = ws.sample_identifier_id INNER JOIN vl_envelopes e ON e.id = si.env_id INNER JOIN auth_user u ON u.id = e.processed_by_id WHERE ws.worksheet_id = %d GROUP BY e.id' %(wksht_id))
			envs = Envelope.objects.raw('select envelope_number, e.id from vl_worksheet_samples ws INNER JOIN vl_sample_identifiers s ON s.id = ws.sample_identifier_id and ws.worksheet_id = %d INNER JOIN vl_envelopes e ON e.id = s.env_id where ws.worksheet_id = %d GROUP BY e.id' %(wksht_id,wksht_id))
			
		page = request.GET.get('page', 1)
		paginator = Paginator(envs, 10)
		try:
			envelopes = paginator.page(page)
		except PageNotAnInteger:
			envelopes = paginator.page(1)
		except EmptyPage:
			envelopes = paginator.page(paginator.num_pages)
		context = {'envelopes':envelopes,'users':users}
		return render(request, 'samples/range_envelopes.html', context)

@transaction.atomic
def merge_envelopes(request):
	if request.method == 'POST':
		s_env = Envelope.objects.filter(envelope_number=request.POST.get('source_envelope')).first()
		d_env = Envelope.objects.filter(envelope_number=request.POST.get('destination_envelope')).first()
		if s_env.sample_type == d_env.sample_type:
			no_sourse_samples = Sample.objects.filter(envelope=s_env).count()
			no_destination_samples = Sample.objects.filter(envelope=s_env).count()
			#return HttpResponse(no_sourse_samples)
	#else:		
	return render(request, 'samples/merge_envelopes.html')
	
@transaction.atomic
def receive_sample_only(request):
	
	saved_sample = request.GET.get('saved_sample')
	tr_code_id = request.GET.get('tr_code_id')
	env_id = request.GET.get('env_id')
	current_tr_code = request.GET.get('current_tr_code')
	if current_tr_code is None:
		current_tr_code = ''
	if request.method == 'POST':
		if vl_services.is_hiv_program(request):
			try:
				sample = vl_services.receive_sample_only(request.POST, request.user)
				ret = {
					'saved_sample': sample.id,
					'env_id': sample.envelope_id,
					'tracking_code_id': sample.tracking_code_id,
					's_barcode': sample.barcode,
					'receipt_type': 'hie',
					'message_type': 'success',
					'err_msg': 'saved'
				}
				return HttpResponse(json.dumps(ret))
			except Exception as e:
				ret = {
					'saved_sample':'',
					'env_id':request.POST.get('envelope_id'),
					'tracking_code_id':request.POST.get('tracking_code_id'),
					's_barcode':request.POST.get('the_barcode', ''),
					'receipt_type':'hie',
					'message_type':'err',
					'err_msg':str(e)
				}
				return HttpResponse(json.dumps(ret))
		pst = request.POST
		date_collected = posted_date(request.POST, 'date_collected')
		sample_reception_form = SampleReceptionForm(pst)
		tr_code_id = request.POST.get('tracking_code_id')
		facility_reference = request.POST.get('facility_reference')
		env_id = int(request.POST.get('envelope_id'))
		session_program_code = get_session_program_code(request)
		mismatch_message = lock_envelope_to_session_program(request, env_id)
		if mismatch_message:
			ret = {
				'saved_sample':'',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':request.POST.get('the_barcode'),
				'receipt_type':'hie',
				'message_type':'err',
				'err_msg':mismatch_message
			}
			return HttpResponse(json.dumps(ret))
		hep_number = request.POST.get('reception_hep_number')
		saved_id = request.POST.get('saved_id')		
		#sample = Sample.objects.filter(barcode=request.POST.get('the_barcode')).first()
		sample = Sample.objects.filter(facility_reference=facility_reference).first()
		sample_program_mismatch = get_program_mismatch_message(request, get_sample_program_code(sample), 'sample')
		if sample_program_mismatch:
			ret = {
				'saved_sample':'',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':request.POST.get('the_barcode'),
				'receipt_type':'hie',
				'message_type':'err',
				'err_msg':sample_program_mismatch
			}
			return HttpResponse(json.dumps(ret))
		if sample is None:
			if not request.POST.get('reception_hep_number'):
				ret = {
					'saved_sample':'',
					'env_id':'',
					'tracking_code_id':'',
					's_barcode':'',
					'receipt_type':'hie',
					'message_type':'err',
					'err_msg':''
				}
				return HttpResponse(json.dumps(ret)) 
			sample = Sample()
			patient = Patient()

			patient.hep_number = request.POST.get('reception_hep_number')
			patient.facility_id = request.POST.get('facility')
			patient.created_by = request.user
			patient.save()

			sample.reception_hep_number = request.POST.get('reception_hep_number')
			sample.facility_reference = facility_reference
			sample.form_number = facility_reference
			sample.facility_id = request.POST.get('facility')
			sample.created_by = request.user
			sample.received_by_id = request.user.id
			sample.date_received = datetime.now()
			sample.stage = 0
			sample.patient = patient
		if sample:
			#check if sample already received
			if sample.envelope_id:
				ret = {
						'saved_sample': sample.id,
						'env_id':env_id,
						'tracking_code_id':tr_code_id,
						's_barcode':request.POST.get('the_barcode'),
						'receipt_type':'hie',
						'message_type':'err',
						'err_msg':'already on '+sample.barcode
					}

				return HttpResponse(json.dumps(ret)) 

			#check if hep_numbers match
			if sample.patient.hep_number is None:
				sample.patient.hep_number = hep_number
				sample.patient.save()
			else:
				sanitized_input_art_no = utils.removeSpecialCharactersFromString(hep_number)
				sanitized_sample_art_no = utils.removeSpecialCharactersFromString(sample.patient.hep_number)
				if sanitized_input_art_no != sanitized_sample_art_no:
					ret = {
						'saved_sample': sample.id,
						'env_id':env_id,
						'tracking_code_id':tr_code_id,
						's_barcode':request.POST.get('the_barcode'),
						'receipt_type':'hie',
						'message_type':'err',
						'err_msg':'miss match with '+sample.patient.hep_number
					}
					return HttpResponse(json.dumps(ret)) 
		sample.tracking_code_id = tr_code_id
		sample.locator_category = 'V'
		sample.envelope_id = env_id
		sample.verified = 1
		sample.is_data_entered = 1
		sample.only_sample_received = 1
		sample.required_verification = 0
		sample.stage = 0
		sample.received_by = request.user
		sample.locator_position=request.POST.get('the_position')
		sample.barcode=request.POST.get('the_barcode')
		_set_sample_type_from_request_or_envelope(sample, request, env_id)
		sample.date_collected = date_collected
		sample.date_received = datetime.now()
		if session_program_code:
			sample.program_code = session_program_code
		sample.save()
		update_envelope_program_code(env_id, get_session_program_code(request))

		sample_utils.save_verification_details(sample,request)

		ret = {
			'saved_sample': sample.id,
			'env_id':env_id,
			'tracking_code_id':tr_code_id,
			's_barcode':sample.barcode,
			'receipt_type':'hie',
			'message_type':'success',
			'err_msg':'saved'
		}

		return HttpResponse(json.dumps(ret))
		
	else:
		d = datetime.now()
		sample_reception_form = SampleReceptionForm(initial={'locator_category':'V', 'date_collected': datetime.now().date(), 'date_received': datetime.now().date()})
		envelope_samples = []
		if vl_services.is_hiv_program(request):
			envelope_samples = vl_services.get_envelope_samples(env_id)
		elif env_id:
			envelope = Envelope.objects.filter(pk=env_id).first()
			envelope_samples = envelope.sample_set.all().order_by('barcode') if envelope else []

		context = {
			'sample_reception_form': sample_reception_form,
			'tr_code_id': tr_code_id,
			'env_id':env_id,
			'current_tr_code':current_tr_code,
			'reception_id':'',
			'message_type':'',
			'envelope_samples': envelope_samples,
			'last_received_barcode': request.GET.get('last_barcode', ''),
		}

	if saved_sample:
		if vl_services.is_hiv_program(request):
			sample = vl_services.get_adapted_sample(saved_sample)
			envelope_samples = vl_services.get_envelope_samples(sample.envelope_id if sample else env_id)
			last_received_barcode = sample.barcode if sample and sample.barcode else request.GET.get('last_barcode', '')
			context.update({'sample':sample,'tr_code_id':tr_code_id,'env_id':env_id,'envelope_samples': envelope_samples,'last_received_barcode': last_received_barcode})
		else:
			sample = Sample.objects.filter(pk=saved_sample).first()
			envelope_samples = sample.envelope.sample_set.all().order_by('barcode') if sample and sample.envelope_id else []
			last_received_barcode = sample.barcode if sample and sample.barcode else request.GET.get('last_barcode', '')
			context.update({'sample':sample,'tr_code_id':tr_code_id,'env_id':env_id,'envelope_samples': envelope_samples,'last_received_barcode': last_received_barcode})

	return render(request, 'samples/receive_sample_only.html', context)

@permission_required('results.add_resultsqc', login_url='/login/')
def release_sample_only_results(request):
	if request.method == 'POST':

		search_string = request.POST.get('search_string', '')  # e.g., '2504-5015,2504-5016' or '2504-5015'

		# Split into list and remove whitespace (if any)
		envelope_numbers = [num.strip() for num in search_string.split(',') if num.strip()]

		samples = Sample.objects.select_related('envelope').filter(envelope__envelope_number__in=envelope_numbers)
		with transaction.atomic():
			for sample in samples:
				print(sample)
				if not sample.patient_id:
					# Create a new patient
					patient = Patient.objects.create(facility_id=sample.facility_id,hep_number=sample.reception_hep_number,created_by_id = sample.created_by_id)
					# Assign the new patient to the sample
					sample.patient = patient
					sample.only_sample_received = 1
					sample.is_data_entered = 1
					sample.verified = 1
					sample.save()
					sample_utils.save_verification_details(sample,request)
				if hasattr(sample, 'result') and sample.result:
					rqc = sample.result.resultsqc
					if not rqc.released:
						other_params = {
							'released': True,
							'comments': 'manual',
							'released_by_id': request.user.id,
							'released_at': datetime.now(),
						}
						rqc, rqc_created = ResultsQC.objects.update_or_create(result=sample.result, defaults=other_params)
		return redirect('/samples/release_sample_only_results/')
		
	else:

		return render(request, 'samples/release_sample_only_resuts.html')

def download_envelope_results(request):
	samples_without_results = Sample.objects.filter(envelope_id=request.GET.get('env_id'))
		
		# Create CSV response
	response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="samples_with_results.csv"'},
        )
	writer = csv.writer(response)
	# Write header
	writer.writerow([
        'Facility Ref',
		'Lab Ref',
		'Facility',
		'District',	
		'Patient ART #',
		'Date of Birth',
		'Sex',
		'current Regimen',
		'Result', 
		'Test Date'
        # Add other sample fields you want to export
    ])

	# Write data
	for sample in samples_without_results:
		if sample.patient_id:
			fac = sample.patient.facility 
			dist = sample.patient.facility.district 
			art_no = sample.patient.hep_number
			dob = sample.patient.dob
			sex = sample.patient.gender
			
		else:
			fac = sample.facility
			dist = '' 
			art_no = s.reception_hep_number
			dob = ''
			sex = ''
		
		writer.writerow([
            sample.facility_reference,
            sample.barcode,
            fac,
            dist,
            art_no,
            dob,
            sex,
            sample.current_regimen,
            sample.result.result_alphanumeric,
            sample.result.test_date
            # Add other sample fields
        ])
	return response
	
