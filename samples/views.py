import json, os, glob, calendar
from datetime import date as dt, datetime as dtime
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse

from django.db.models import Q
from django.forms import modelformset_factory
#from django.views.generic import TemplateView

from backend.models import Appendix,Facility,MedicalLab
from .models import *
from forms import *
from home import utils
from . import utils as sample_utils
#from inspect import getmembers
#from pprint import pprint
from django.db import connection
# Create your views here.

ENVS_LIMIT = 1000
SAMPLES_LIMIT = 1000

@permission_required('samples.add_sample', login_url='/login/')
def create(request):
	saved_sample = request.GET.get('saved_sample')
	PastRegimensFormSet = modelformset_factory(PastRegimens, form=PastRegimensForm, extra=5)
	treatment_indication_options = utils.TREATMENT_INFO_OPTIONS
	treatment_indication_selected_options = ''
	selected_treatment_ids = ''
	if request.method == 'POST':
		pst = request.POST
		patient_form = PatientForm(request.POST)
		phone_form = PatientPhoneForm(request.POST)
		envelope_form = EnvelopeForm(request.POST)
		clinician_form = ClinicianForm(request.POST)
		lab_tech_form = LabTechForm(request.POST)
		sample_form = SampleForm(request.POST)
		preliminary_findings = PreliminaryFindingsForm(request.POST)
		valid_patient = patient_form.is_valid()
		valid_phone = phone_form.is_valid()
		valid_envelope = envelope_form.is_valid()
		valid_sample = sample_form.is_valid()
		valid_clinician = clinician_form.is_valid()
		valid_lab_tech = lab_tech_form.is_valid()
		valid_preliminary_findings = preliminary_findings.is_valid()
		indication_for_treatment = pst.getlist('treatment_indication');

		null_dob = pst.get('null_dob')
		#null_treatment_initiation_date = pst.get('null_treatment_initiation_date')

		if not pst.get('dob') and not null_dob:
			patient_form.add_error('dob', 'Date is blank')

		#if not pst.get('treatment_initiation_date') and not null_treatment_initiation_date:
		#	sample_form.add_error('treatment_initiation_date', 'Date is blank')

		loc_exists = sample_utils.locator_id_exists(request.POST)

		if loc_exists:
			loc_by = loc_exists.created_by
			loc_on = loc_exists.created_at
			sample_form.add_error('locator_position', 'Locator ID already created by %s on %s'%(loc_by,loc_on))
		elif not sample_utils.initiation_date_valid(request.POST):
			sample_form.add_error('treatment_initiation_date', 'Initiation date can not be < DoB')
		elif valid_patient and valid_phone and valid_envelope and valid_sample and valid_clinician and valid_lab_tech and valid_preliminary_findings:
			facility = sample_form.cleaned_data.get('facility')
			
			hep_number = patient_form.cleaned_data.get('hep_number')
			unique_id = "%s-A-%s" %(facility.pk, hep_number.replace(' ','').replace('-','').replace('/',''))
			
			patient = patient_form.save(commit=False)
			patient.unique_id = unique_id
			patient.created_by = request.user
			patient.save()
			#now that we have the patient, let us save the preliminary investigations
			prel_findings = preliminary_findings.save(commit=False)
			prel_findings.patient = patient
			prel_findings.save();

			#HttpResponse([90,78,45])
			#now save the  treatment indication
			for val in indication_for_treatment:
				indication_for_treatment_obj = PatientTreatmentIndication()
				indication_for_treatment_obj.patient = patient
				indication_for_treatment_obj.treatment_indication_id = val
				indication_for_treatment_obj.save()

			clinician_form.cleaned_data.update({'facility':facility})
			cl_data = clinician_form.cleaned_data
			clinician, clinician_created = Clinician.objects.update_or_create(
						facility=facility, cname=cl_data.get('cname'), defaults={'cphone':cl_data.get('cphone')})

			lab_tech_form.cleaned_data.update({'facility':facility})
			lt_data = lab_tech_form.cleaned_data
			lab_tech, lab_tech_created = LabTech.objects.update_or_create(
						facility=facility, lname=lt_data.get('lname'), defaults={'lphone':lt_data.get('lphone')})

			ph_number = phone_form.cleaned_data.get('phone')
			if ph_number:
				phone, phone_created = PatientPhone.objects.get_or_create(patient=patient,**phone_form.cleaned_data)

			envelope, env_created = Envelope.objects.get_or_create(
						envelope_number=envelope_form.cleaned_data.get('envelope_number'),
						defaults={'sample_type': sample_form.cleaned_data.get('sample_type'),'sample_medical_lab':utils.user_lab(request)}
						)

			sample = sample_form.save(commit=False)
			sample.clinician = clinician
			sample.lab_tech = lab_tech
			sample.patient = patient
			sample.patient_unique_id = patient.unique_id
			sample.envelope = envelope
			#sample.vl_sample_id = sample_utils.create_sample_id()
			sample.created_by = request.user
			sample.sample_medical_lab = utils.user_lab(request)
			envep_no = request.POST.get('envelope_number')
			env_type = int(envep_no[-4:])
			if env_type >= 900 and env_type < 1000:
				sample.is_study_sample = 1
			else:
				sample.is_study_sample = 0
			sample.save()

			return redirect('/samples/create?saved_sample=%s' %sample.pk)
		else:
			sample_form.add_error('form_number', 'Saving failed')
	else:
		envelope_form = EnvelopeForm(initial={'envelope_number': sample_utils.initial_env_number()})
		clinician_form = ClinicianForm
		lab_tech_form = LabTechForm
		phone_form = PatientPhoneForm
		patient_form = PatientForm
		preliminary_findings = PreliminaryFindingsForm
		sample_form = SampleForm(initial={'locator_category':'V', 'date_received': timezone.now().date(), 'date_collected': timezone.now().date()})
		#null_treatment_initiation_date = None
		null_dob = None

	context = {
		'clinician_form':clinician_form,
		'lab_tech_form':lab_tech_form,
		'envelope_form': envelope_form,
		'phone_form': phone_form,
		'patient_form': patient_form,
		'sample_form': sample_form,
		'preliminary_findings':preliminary_findings,
		'null_dob': null_dob,
		'treatment_indication_selected_options': treatment_indication_selected_options,
		'treatment_indication_options': treatment_indication_options,
		'selected_treatment_ids': selected_treatment_ids,
		#'null_treatment_initiation_date':null_treatment_initiation_date
	}

	if saved_sample:
		sample = Sample.objects.filter(pk=saved_sample).first()
		context.update({'sample':sample})
		
	return render(request, 'samples/create.html', context)

@permission_required('samples.change_sample', login_url='/login/')

def edit(request, sample_id):
	treatment_indication_options = utils.TREATMENT_INFO_OPTIONS
	treatment_indication_selected_options = ''
	sample = Sample.objects.get(pk=sample_id)
	patient = sample.patient
	envelope = sample.envelope
	clinician = sample.clinician
	lab_tech = sample.lab_tech
	prel_findings = PreliminaryFindings.objects.get(patient = patient.id)
	count_dr = 0
	drug_resistance = None
	pst = request.POST
	#get the treatment info for patient
	#treatment_indication_objects = PatientTreatmentIndication.objects.values('treatment_indication_id')
	#print(treatment_indication_objects)
	treatment_indication_objects = PatientTreatmentIndication.objects.filter(patient = patient)
	selected_treatment_ids = ''
	if treatment_indication_objects:
		selected_treatment_ids = sample_utils.getListFromObjects(treatment_indication_objects)
	
	if request.method == 'POST':
		intervene = request.POST.get('intervene')
		patient_form = PatientForm(request.POST, instance=patient)
		envelope_form = EnvelopeForm(request.POST, instance=envelope)
		sample_form = SampleForm(request.POST, instance=sample)
		clinician_form = ClinicianForm(request.POST, instance=clinician)
		lab_tech_form = LabTechForm(request.POST, instance=lab_tech)
		prel_findings_form = PreliminaryFindingsForm(request.POST, instance=prel_findings)
		
		valid_patient = patient_form.is_valid()
		#valid_phone = phone_form.is_valid()
		valid_envelope = envelope_form.is_valid()
		valid_sample = sample_form.is_valid()
		valid_prem_findings = prel_findings_form.is_valid()

		if sample_utils.locator_id_exists(request.POST, sample_id):
			sample_form.add_error('locator_position', 'Duplicate Locator ID')
		elif not sample_utils.initiation_date_valid(request.POST):
			sample_form.add_error('treatment_initiation_date', 'Initiation date can not be < DoB')
		elif valid_patient and valid_envelope and valid_sample and clinician_form.is_valid() and lab_tech_form.is_valid() and valid_prem_findings:
			patient_form.save()
			#envelope_form.save()
			envelope, env_created = Envelope.objects.update_or_create(
						envelope_number=envelope_form.cleaned_data.get('envelope_number'),						
						defaults={'sample_type': sample_form.cleaned_data.get('sample_type'),'sample_medical_lab':utils.user_lab(request)}
						)

			sample = sample_form.save(commit=False)
			sample.updated_by = request.user
			sample.envelope = envelope

			facility = sample.facility
			clinician_form.cleaned_data.update({'facility':facility})
			cl_data = clinician_form.cleaned_data
			clinician, clinician_created = Clinician.objects.update_or_create(
						facility=facility, cname=cl_data.get('cname'), defaults={'cphone':cl_data.get('cphone')})

			lab_tech_form.cleaned_data.update({'facility':facility})
			lt_data = lab_tech_form.cleaned_data
			lab_tech, lab_tech_created = LabTech.objects.update_or_create(
						facility=facility, lname=lt_data.get('lname'), defaults={'lphone':lt_data.get('lphone')})

			#save the treatment indication
			indication_for_treatment = pst.getlist('treatment_indication');
			#remove any previously added treatment infor for this patient
			conn = connection.cursor()
			# Raw SQL delete, using params for protection against SQL injection
			conn.execute("DELETE FROM vl_patient_treatment_indication WHERE patient_id = %s", [patient.id])
			if indication_for_treatment:
				for val in indication_for_treatment:
					indication_for_treatment_obj = PatientTreatmentIndication()
					indication_for_treatment_obj.patient = patient
					indication_for_treatment_obj.treatment_indication_id = val
					indication_for_treatment_obj.save()

			sample.clinician = clinician
			sample.lab_tech = lab_tech

			prel_findings_form.save()
			
			sample.sample_medical_lab = utils.user_lab(request)
			sample.save()			

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
		clinician_form = ClinicianForm(instance=clinician)
		lab_tech_form = LabTechForm(instance=lab_tech)
		prel_findings = PreliminaryFindingsForm(instance=prel_findings)

		
	context = {
		'clinician_form':clinician_form,
		'lab_tech_form':lab_tech_form,
		'sample_id': sample_id,
		'envelope_form': envelope_form,
		'patient_form': patient_form,
		'sample_form': sample_form,
		'vsi': sample.vl_sample_id,
		'preliminary_findings':prel_findings,
		#'facilities': Facility.objects.all(),
		'regimens': Appendix.objects.filter(appendix_category=3),
		'intervene': intervene,
		'treatment_indication_selected_options': treatment_indication_selected_options,
		'treatment_indication_options': treatment_indication_options,
		'selected_treatment_ids':selected_treatment_ids
	}
		
	return render(request, 'samples/create.html', context)


def get_facility(request, form_number):
	facility_id = sample_utils.get_facility_by_form(form_number)
	return HttpResponse(facility_id)

def get_district_hub(request, facility_id):
	district_hub = sample_utils.get_district_hub_by_facility(facility_id)
	return HttpResponse(district_hub)

def show(request, sample_id):
	sample = Sample.objects.get(pk=sample_id)
	patient = sample.patient
	envelope = sample.envelope
	drug_resistance = None
	prel_findings = PreliminaryFindings.objects.get(patient = patient.id)
	treatment_indication_options = utils.TREATMENT_INFO_OPTIONS
	treatment_indication_objects = PatientTreatmentIndication.objects.filter(patient = patient)
	selected_treatment_ids = ''
	if treatment_indication_objects:
		selected_treatment_ids = sample_utils.getListFromObjects(treatment_indication_objects)
	PastRegimensFormSet = modelformset_factory(PastRegimens, form=PastRegimensForm)

	context = {
		'clinician_form': ClinicianForm(instance=sample.clinician),
		'lab_tech_form': LabTechForm(instance=sample.lab_tech),
		'sample_id': sample_id,
		'envelope_form': EnvelopeForm(instance=sample.envelope),
		'phone_form': PatientPhoneForm(),
		'patient_form': PatientForm(instance=patient),
		'sample_form': SampleForm(instance=sample),
		'preliminary_findings':PreliminaryFindingsForm(instance=prel_findings),
		'vl_sample_id': sample.vl_sample_id,
		'treatment_indication_options':treatment_indication_options,
		'selected_treatment_ids':selected_treatment_ids,
	}

	return render(request, 'samples/show.html', context)

def list(request):
	search_val = request.GET.get('search_val')

	# if search_val:
	# 	samples = Sample.objects.filter(
	# 				Q(form_number__icontains=search_val)|
	# 				Q(vl_sample_id__icontains=search_val)|
	# 				sample_utils.locator_cond(search_val)
	# 				).order_by('-pk')[:1]
	# 	if samples:
	# 		sample = samples[0]
	# 		return redirect('/samples/show/%d' %sample.pk)

	return render(request, 'samples/list.html', {'global_search':search_val })
	

def appendix_select(name="", cat_id=0, clss='form-control input-xs w-md'):
	apendices = Appendix.objects.values('id','appendix')
	more = {'class': clss}
	return utils.select(name,{'k_col':'id', 'v_col':'appendix', 'items':apendices.filter(appendix_category_id=cat_id)},"",more)

@permission_required('samples.add_verification', login_url='/login/')
def verify(request, sample_id):
	facilities = Facility.objects.values('id', 'facility').order_by('facility')
	sample = Sample.objects.get(pk=sample_id);
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
				'dob': utils.local_date(s.patient.dob),
				'treatment_initiation_date': utils.local_date(s.treatment_initiation_date),
				'treatment_duration':"%s"%(s.treatment_duration) if s.treatment_duration else "",
				'sample_creator': s.created_by.username,
				'created_at': utils.local_date(s.created_at),
			})
	return HttpResponse(json.dumps(ret))


@permission_required('samples.add_verification', login_url='/login/')
def save_verify(request):
	r = request.POST
	p = Patient.objects.get(pk=r.get('patient_id'))
	p.hep_number = r.get('hep_number', '')
	p.other_id = r.get('other_id', '')
	p.dob = utils.get_date(r, 'dob')
	p.gender = r.get('gender', '')
	p.save()

	s = Sample.objects.get(pk=r.get('sample_id'))
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
	s.save()

	if s.in_worksheet:
		return HttpResponse("sample in worksheet already")

	v = Verification.objects.filter(sample=s).first()
	v = v if v else Verification()
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
			'pending': Sample.objects.filter(verified=False).count(),
			'pending_dbs': Sample.objects.filter(verified=False, sample_type='D').count(),
			'pending_plasma': Sample.objects.filter(verified=False, sample_type='P').count(),
			})
	else:
		context.update({
			'completed': Sample.objects.filter(verified=True).count(),
			'completed_dbs': Sample.objects.filter(verified=True, sample_type='D').count(),
			'completed_plasma': Sample.objects.filter(verified=True, sample_type='P').count(),
			})


	# if search_val:
	# 	envelopes = Envelope.objects.filter(envelope_number__contains=search_val).order_by('-pk')[:1]
	# 	if envelopes:
	# 		envelope = envelopes[0]
	# 		return redirect('/samples/verify/%d' %envelope.pk)

	return render(request, "samples/verify_list.html", context)

def appendices_json(cat_id):
	appendices = Appendix.objects.values('id', 'appendix').filter(appendix_category_id=cat_id)
	ret={}
	for a in appendices:
		ret[a['id']] = a['appendix']
	return json.dumps(ret)

def pat_hist(request, facility_id):
	ret = []
	#ret = [{'art_number':art_number, 'test_date':'2017-01-01', 'result':'TND'}, {'art_number':art_number, 'test_date':'2017-04-01', 'result':'TND'}]
	hep_number = request.GET.get('hep_number')
	if hep_number == '':
		return HttpResponse(json.dumps(ret))
	unique_id = "%s-A-%s" %(facility_id, hep_number.replace(' ','').replace('-','').replace('/',''))
	samples = Sample.objects.filter( Q(patient__unique_id=unique_id)|Q(facility_id=facility_id,patient__hep_number=hep_number)).order_by('-date_collected')[:3]
	
	for s in samples:
		ret.append({
				'form_number': s.form_number,				
				'date_collected': utils.local_date(s.date_collected),
				'hep_number': s.patient.hep_number,
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
		released = True if choice == 'release' else False
		comments = request.POST.get('comments')
		
		other_params = {
			'released': released,
			'comments': request.POST.get('comments'),
			'reject_released_by': request.user,
			'released_at': timezone.now(),
		}
		rsr, rsr_created = RejectedSamplesRelease.objects.update_or_create(sample=sample, defaults=other_params)			
		return HttpResponse("saved")
	else:
		date_rejected_fro = request.GET.get('date_rejected_fro',dt.today().strftime("%Y-%m-01"))
		date_rejected_to = request.GET.get('date_rejected_to',dt.today().strftime("%Y-%m-%d"))
		released = request.GET.get('released', 'N')
		rlsd = True if released=='Y' else None
		rejects = Verification.objects.filter(accepted=False, sample__rejectedsamplesrelease__released=rlsd,  sample__date_received__gte=date_rejected_fro, sample__date_received__lte=date_rejected_to)
		context = {	'rejects':rejects, 
					'date_rejected_fro':date_rejected_fro, 
					'date_rejected_to':date_rejected_to,
					'released':released,}
		return render(request, "samples/release_rejects.html", context)

def intervene_list(request):
	intervene_rejects = RejectedSamplesRelease.objects.filter(released=False)[:500]
	return render(request, 'samples/intervene_list.html', {'intervene_rejects':intervene_rejects})

def search(request):
	cond = Q()
	search = request.GET.get('search_val')
	approvals = request.GET.get('approvals')
	search_env = request.GET.get('search_env')
	result = request.GET.get('results')
	facility_id = request.GET.get('facility_id')
	
	if search:
		search = search.strip()
		if search_env:
			env = Envelope.objects.filter(sample_utils.env_cond(search)).first()
			samples = Sample.objects.filter(envelope=env).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"})[:300]
		elif result:
			unique_id = "%s-A-%s" %(facility_id, search.replace(' ','').replace('-','').replace('/',''))
			samples = Sample.objects.filter( Q(patient__unique_id=unique_id)|Q(facility_id=facility_id,patient__hep_number=search)).order_by('-date_collected')[:3]
			ret = []
			for s in samples:
				ret.append({
						'facility': s.facility.facility,
						'form_number': s.form_number,				
						'date_collected': utils.local_date(s.date_collected),
						'hep_number': s.patient.hep_number,
						'other_id': s.patient.other_id,
						'gender': s.patient.gender,
						'dob': utils.local_date(s.patient.dob),
						'result':"%s"%s.result.result_alphanumeric if hasattr(s, 'result') else '',
						'test_date':utils.local_date(s.result.test_date) if hasattr(s, 'result') else '',
			})
			return render(request, 'samples/search_prev_results.html', {'results':ret, 'facility_id':facility_id})
		else:
			if search.isdigit() or search[:-1].isdigit():
				samples = Sample.objects.filter(form_number=search)
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

def download(request, path):
	folder = "reports/drug_resistance" if request.GET.get('dr') else "reports"
	file_path = os.path.join(settings.MEDIA_ROOT, "%s/%s"%(folder,path))
	if os.path.exists(file_path):
		with open(file_path, 'rb') as fh:
			response = HttpResponse(fh.read(), content_type="application//x-zip-compressed")
	 	 	response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
	 	 	return response
	else:
		return HttpResponse("report missing")

def reports(request):
	#reports = os.listdir("media/reports/")
	if request.GET.get('dr'):
		path = "media/reports/drug_resistance/" 
	elif request.GET.get('detectables'):
		path = "media/reports/detectables/" 
	else:
		path = "media/reports/"
	reports = []
	for r in glob.glob("%s*.zip"%path):
		stats = os.stat(r)
		last_modified = dtime.fromtimestamp(stats.st_mtime)
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

def released_rejects(request):
	if request.method == 'POST':
		sample = Sample.objects.get(pk=request.POST.get('sample_pk'))
		choice = request.POST.get('choice')
		comments = request.POST.get('comments')
		
		other_params = {
			'comments': request.POST.get('comments'),
			'reject_released_by': request.user,
			'released_at': timezone.now(),
		}
		rsr, rsr_created = RejectedSamplesRelease.objects.update_or_create(sample=sample, defaults=other_params)			
		return HttpResponse("saved")
	else:
		date_rejected_fro = request.GET.get('date_rejected_fro',dt.today().strftime("%Y-%m-01"))
		date_rejected_to = request.GET.get('date_rejected_to',dt.today().strftime("%Y-%m-%d"))
		rejects = Verification.objects.filter(accepted=False, sample__rejectedsamplesrelease__released=1,  sample__date_received__gte=date_rejected_fro, sample__date_received__lte=date_rejected_to)
		context = {	'rejects':rejects, 
					'date_rejected_fro':date_rejected_fro, 
					'date_rejected_to':date_rejected_to}
		return render(request, "samples/released_rejects.html", context)

def print_rejects(request, sample_id):
	#result = Result.objects.filter(id=result_id).first()
	verification = Verification.objects.get(sample_id = sample_id)
	rejected_sample = RejectedSamplesRelease.objects.get(sample_id = sample_id)
	#mark the result printed
	rejected_sample.printed = 1
	rejected_sample.save()
	
	
	if rejected_sample.sample.sample_type == 'P':
		s_type = 'Plasma'
	else:
		s_type = 'DBS'
	context = {		
		'facility':rejected_sample.sample.facility.facility,
		'hub':rejected_sample.sample.facility.hub.hub,
		'district':rejected_sample.sample.facility.district.district,
		'form_number':rejected_sample.sample.form_number,
		'sample_type': s_type,
		'collection_date':utils.display_date(rejected_sample.sample.date_collected),
		'reception_date':utils.display_date(rejected_sample.sample.date_received),
		'hep_number':rejected_sample.sample.patient.hep_number,
		'other_id':rejected_sample.sample.patient.other_id,
		'sex': utils.get_gender(rejected_sample.sample.patient.gender),
		'patient_name': rejected_sample.sample.patient.name,
		'date_of_birth':utils.display_date(rejected_sample.sample.patient.dob),
		'drug_name': utils.get_drug_name(rejected_sample.sample.current_drug_name),
		'treatment_initiation': utils.display_date(rejected_sample.sample.treatment_initiation_date),
		'is_breastfeeding': utils.translate_yes_no(rejected_sample.sample.breast_feeding),
		'is_pregnant':utils.translate_yes_no(rejected_sample.sample.pregnant),
		'date_released': utils.display_date_spaced(rejected_sample.released_at),
		'rejection_reason': verification.rejection_reason,
	}
	#return HttpResponse(utils.display_date_spaced(rejected_sample.released_at))
	return render(request, 'samples/print_rejects.html', context)
