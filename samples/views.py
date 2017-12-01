import json
from datetime import date as dt
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse

from django.db.models import Q
from django.forms import modelformset_factory
#from django.views.generic import TemplateView

from backend.models import Appendix,Facility,MedicalLab
from .models import Patient, Sample, PatientPhone, Envelope, Verification, Clinician, LabTech, PastRegimens, DrugResistanceRequest, RejectedSamplesRelease
from forms import *
from home import utils
from . import utils as sample_utils

# Create your views here.

ENVS_LIMIT = 1000
SAMPLES_LIMIT = 1000

@permission_required('samples.add_sample', login_url='/login/')
def create(request):
	saved_sample = request.GET.get('saved_sample')
	PastRegimensFormSet = modelformset_factory(PastRegimens, form=PastRegimensForm, extra=5)
	if request.method == 'POST':
		patient_form = PatientForm(request.POST)
		phone_form = PatientPhoneForm(request.POST)
		envelope_form = EnvelopeForm(request.POST)
		clinician_form = ClinicianForm(request.POST)
		lab_tech_form = LabTechForm(request.POST)
		sample_form = SampleForm(request.POST)
		drug_resistance_form = DrugResistanceRequestForm(request.POST)		
		past_regimens_formset =PastRegimensFormSet(request.POST)

		valid_patient = patient_form.is_valid()
		valid_phone = phone_form.is_valid()
		valid_envelope = envelope_form.is_valid()
		valid_sample = sample_form.is_valid()
		valid_clinician = clinician_form.is_valid()
		valid_lab_tech = lab_tech_form.is_valid()
		valid_dr = drug_resistance_form.is_valid()
		valid_past_regimens = past_regimens_formset.is_valid()

		if sample_utils.locator_id_exists(request.POST):
			sample_form.add_error('locator_position', 'Duplicate Locator ID')
		elif not sample_utils.initiation_date_valid(request.POST):
			sample_form.add_error('treatment_initiation_date', 'Initiation date can not be < DoB')
		elif valid_patient and valid_phone and valid_envelope and valid_sample and valid_clinician and valid_lab_tech and valid_dr and valid_past_regimens:
			facility = sample_form.cleaned_data.get('facility')
			art_number = patient_form.cleaned_data.get('art_number')
			unique_id = "%s-A-%s" %(facility.pk, art_number)
			patient_form.cleaned_data.update({'created_by': request.user})
			patient, pat_created = Patient.objects.get_or_create(
						unique_id=unique_id,
						defaults=patient_form.cleaned_data
						)

			patient.simple_art_number = art_number.replace(' ','').replace('-','').replace('/','')
			patient.save()

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
			sample.vl_sample_id = sample_utils.create_sample_id()
			sample.created_by = request.user

			sample.sample_medical_lab = utils.user_lab(request)
			
			sample.save()

			drug_resistance = drug_resistance_form.save(commit=False)
			drug_resistance.sample = sample
			drug_resistance.save()

			past_regimens = past_regimens_formset.save(commit=False)
			for past_regimen in past_regimens:
				past_regimen.drug_resistance_request = drug_resistance
				past_regimen.save()

			return redirect('/samples/create?saved_sample=%s' %sample.pk)
		else:
			sample_form.add_error('locator_category', 'Form saving failed')

	else:
		envelope_form = EnvelopeForm(initial={'envelope_number': sample_utils.initial_env_number()})
		clinician_form = ClinicianForm
		lab_tech_form = LabTechForm
		phone_form = PatientPhoneForm
		patient_form = PatientForm
		sample_form = SampleForm(initial={'locator_category':'V', 'date_received': timezone.now().date()})
		drug_resistance_form = DrugResistanceRequestForm
		past_regimens_formset = PastRegimensFormSet(queryset=PastRegimens.objects.none())

	context = {
		'clinician_form':clinician_form,
		'lab_tech_form':lab_tech_form,
		'envelope_form': envelope_form,
		'phone_form': phone_form,
		'patient_form': patient_form,
		'sample_form': sample_form,
		'drug_resistance_form': drug_resistance_form,
		'past_regimens_formset': past_regimens_formset,
		#'facilities': Facility.objects.all(),
		'regimens': Appendix.objects.filter(appendix_category=3),
	}

	if saved_sample:
		sample = Sample.objects.filter(pk=saved_sample).first()
		context.update({'sample':sample})
		
	return render(request, 'samples/create.html', context)

@permission_required('samples.change_sample', login_url='/login/')
def edit(request, sample_id):
	sample = Sample.objects.get(pk=sample_id)
	patient = sample.patient
	envelope = sample.envelope
	clinician = sample.clinician
	lab_tech = sample.lab_tech
	count_dr = 0
	drug_resistance = None
	try:
		drug_resistance = sample.drugresistancerequest
		count_dr = PastRegimens.objects.filter(drug_resistance_request=drug_resistance).count()
	except :
		pass
	
	
	PastRegimensFormSet = modelformset_factory(PastRegimens, form=PastRegimensForm, 
							extra=(5-count_dr))

	if request.method == 'POST':
		intervene = request.POST.get('intervene')
		patient_form = PatientForm(request.POST, instance=patient)
		#phone_form = PatientPhoneForm(request.POST, )
		envelope_form = EnvelopeForm(request.POST, instance=envelope)
		sample_form = SampleForm(request.POST, instance=sample)
		clinician_form = ClinicianForm(request.POST, instance=clinician)
		lab_tech_form = LabTechForm(request.POST, instance=lab_tech)
		drug_resistance_form = DrugResistanceRequestForm(request.POST, instance=drug_resistance)
		past_regimens_formset =PastRegimensFormSet(request.POST)

		valid_patient = patient_form.is_valid()
		#valid_phone = phone_form.is_valid()
		valid_envelope = envelope_form.is_valid()
		valid_sample = sample_form.is_valid()
		valid_dr = drug_resistance_form.is_valid()
		valid_past_regimens = past_regimens_formset.is_valid()

		if sample_utils.locator_id_exists(request.POST, sample_id):
			sample_form.add_error('locator_position', 'Duplicate Locator ID')
		elif not sample_utils.initiation_date_valid(request.POST):
			sample_form.add_error('treatment_initiation_date', 'Initiation date can not be < DoB')
		elif valid_patient and valid_envelope and valid_sample and clinician_form.is_valid() and lab_tech_form.is_valid() and valid_dr and valid_past_regimens:
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

			sample.clinician = clinician
			sample.lab_tech = lab_tech
			
			sample.sample_medical_lab = utils.user_lab(request)
			sample.save()

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
		clinician_form = ClinicianForm(instance=clinician)
		lab_tech_form = LabTechForm(instance=lab_tech)
		drug_resistance_form = DrugResistanceRequestForm(instance=drug_resistance)
		past_regimens_formset = PastRegimensFormSet(queryset=PastRegimens.objects.filter(drug_resistance_request=drug_resistance))

	context = {
		'clinician_form':clinician_form,
		'lab_tech_form':lab_tech_form,
		'sample_id': sample_id,
		'envelope_form': envelope_form,
		#'phone_form': phone_form,
		'patient_form': patient_form,
		'sample_form': sample_form,
		'vsi': sample.vl_sample_id,
		'drug_resistance_form': drug_resistance_form,
		'past_regimens_formset': past_regimens_formset,
		#'facilities': Facility.objects.all(),
		'regimens': Appendix.objects.filter(appendix_category=3),
		'intervene': intervene,
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
				'facility_name': s.facility.facility,
				'district': s.facility.district.district,
				'hub': s.facility.hub.hub,
				'date_collected': utils.local_date(s.date_collected),
				'art_number': s.patient.art_number,
				'other_id': s.patient.other_id,
				'gender': s.patient.gender,
				'dob': utils.local_date(s.patient.dob),
				'treatment_initiation_date': utils.local_date(s.treatment_initiation_date),
				'sample_creator': s.created_by.username,
				'created_at': utils.local_date(s.created_at),
			})
	return HttpResponse(json.dumps(ret))


@permission_required('samples.add_verification', login_url='/login/')
def save_verify(request):
	r = request.GET
	p = Patient.objects.get(pk=r.get('patient_id'))
	p.art_number = r.get('art_number', '')
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
		v.rejection_reason_id = r.get('rejection_reason_id', None)
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

	# if search_val:
	# 	envelopes = Envelope.objects.filter(envelope_number__contains=search_val).order_by('-pk')[:1]
	# 	if envelopes:
	# 		envelope = envelopes[0]
	# 		return redirect('/samples/verify/%d' %envelope.pk)

	return render(request, "samples/verify_list.html", {'verified':verified, 'global_search':search_val })

def appendices_json(cat_id):
	appendices = Appendix.objects.values('id', 'appendix').filter(appendix_category_id=cat_id)
	ret={}
	for a in appendices:
		ret[a['id']] = a['appendix']
	return json.dumps(ret)

def pat_hist(request, facility_id, art_number):
	#ret = [{'art_number':art_number, 'test_date':'2017-01-01', 'result':'TND'}, {'art_number':art_number, 'test_date':'2017-04-01', 'result':'TND'}]
	samples = Sample.objects.filter(patient__simple_art_number=art_number, facility=facility_id).order_by('date_collected')
	ret = []
	for s in samples:
		ret.append({
				'form_number': s.form_number,				
				'date_collected': utils.local_date(s.date_collected),
				'art_number': s.patient.art_number,
				'other_id': s.patient.other_id,
				'gender': s.patient.gender,
				'dob': utils.local_date(s.patient.dob),
				'result':"%s Copies/mL"%s.result.result_numeric,
				'test_date':utils.local_date(s.result.test_date),
			})

	return HttpResponse(json.dumps(ret))

def clinicians(request, facility_id):
	clinicians = Clinician.objects.filter(facility=facility_id)
	ret = []
	for c in clinicians:
		ret.append({'name':c.cname, 'phone':c.cphone})

	return HttpResponse(json.dumps(ret))

def lab_techs(request, facility_id):
	lab_techs = LabTech.objects.filter(facility=facility_id)
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
		date_rejected = request.GET.get('date_rejected',dt.today())
		rejects = Verification.objects.filter(accepted=False, created_at__date=date_rejected)
		return render(request, "samples/release_rejects.html", {'rejects':rejects, 'date_rejected':date_rejected.strftime("%Y-%m-%d")})

def intervene_list(request):
	intervene_rejects = RejectedSamplesRelease.objects.filter(released=False)[:500]
	return render(request, 'samples/intervene_list.html', {'intervene_rejects':intervene_rejects})

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