import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django_datatables_view.base_datatable_view import BaseDatatableView
#from django.views.generic import TemplateView

from backend.models import Appendix,Facility
from .models import Patient, Sample, PatientPhone, Envelope, Verification
from forms import *
from home import utils
from . import utils as sample_utils

# Create your views here.

ENVS_LIMIT = 1000
SAMPLES_LIMIT = 1000

def create(request):
	if request.method == 'POST':
		patient_form = PatientForm(request.POST)
		phone_form = PatientPhoneForm(request.POST)
		envelope_form = EnvelopeForm(request.POST)
		sample_form = SampleForm(request.POST)

		valid_patient = patient_form.is_valid()
		valid_phone = phone_form.is_valid()
		valid_envelope = envelope_form.is_valid()
		valid_sample = sample_form.is_valid()

		if valid_patient and valid_phone and valid_envelope and valid_sample:
			facility = patient_form.cleaned_data.get('facility')
			art_number = patient_form.cleaned_data.get('art_number')
			unique_id = "%s-A-%s" %(facility, art_number)
			patient_form.cleaned_data.update({'created_by': request.user})
			patient, pat_created = Patient.objects.get_or_create(
						unique_id=unique_id,
						defaults=patient_form.cleaned_data
						)

			phone, phone_created = PatientPhone.objects.get_or_create(
						patient=patient,
						**phone_form.cleaned_data
						)

			envelope, env_created = Envelope.objects.get_or_create(
						**envelope_form.cleaned_data
						)

			sample = sample_form.save(commit=False)
			sample.patient = patient
			sample.patient_unique_id = patient.unique_id
			sample.envelope = envelope
			sample.vl_sample_id = sample_utils.create_sample_id()
			vl_testing = request.POST.get('vl_testing', '')
			sample.routine_monitoring = True if vl_testing=='routine' else False
			sample.repeat_testing = True if vl_testing=='repeat' else False
			sample.suspected_treatment_failure = True if vl_testing=='suspected' else False	
			sample.created_by = request.user
			sample.save()
			return redirect('samples/create')

	else:
		envelope_form = EnvelopeForm(initial={'envelope_number': sample_utils.initial_env_number()})
		phone_form = PatientPhoneForm
		patient_form = PatientForm
		sample_form = SampleForm(initial={'locator_category':'V'})

	context = {
		'envelope_form': envelope_form,
		'phone_form': phone_form,
		'patient_form': patient_form,
		'sample_form': sample_form,
		'facilities': Facility.objects.all(),
		'regimens': Appendix.objects.filter(appendix_category=3),
	}
		
	return render(request, 'samples/create.html', context)

def edit(request, sample_id):
	sample = Sample.objects.get(pk=sample_id)
	patient = sample.patient
	envelope = sample.envelope
	if request.method == 'POST':
		patient_form = PatientForm(request.POST, instance=patient)
		#phone_form = PatientPhoneForm(request.POST, )
		envelope_form = EnvelopeForm(request.POST, instance=envelope)
		sample_form = SampleForm(request.POST, instance=sample)

		valid_patient = patient_form.is_valid()
		#valid_phone = phone_form.is_valid()
		valid_envelope = envelope_form.is_valid()
		valid_sample = sample_form.is_valid()

		if valid_patient and valid_envelope and valid_sample:
			patient_form.save()
			envelope.save()
			sample.save()
			return redirect('/samples/list')

	else:
		envelope_form = EnvelopeForm(instance=sample.envelope)
		phone_form = PatientPhoneForm()
		patient_form = PatientForm(instance=patient)
		sample_form = SampleForm(instance=sample)

	context = {
		'sample_id': sample_id,
		'envelope_form': envelope_form,
		'phone_form': phone_form,
		'patient_form': patient_form,
		'sample_form': sample_form,
		'facilities': Facility.objects.all(),
		'regimens': Appendix.objects.filter(appendix_category=3),
	}
		
	return render(request, 'samples/create.html', context)


def get_facility(request, form_number):
	facility_id = sample_utils.get_facility_by_form(form_number)
	return HttpResponse(facility_id)

def show(request, sample_id):
	return render(request, 'samples/show.html', {'sample': get_object_or_404(Sample, pk=sample_id)})

def list(request):
	return render(request, 'samples/list.html')
	

def appendix_select(name="", cat_id=0, clss='form-control input-xs w-md'):
	apendices = Appendix.objects.values('id','appendix')
	more = {'class': clss}
	return utils.select(name,{'k_col':'id', 'v_col':'appendix', 'items':apendices.filter(appendix_category_id=cat_id)},"",more)

def verify(request, envelope_id):
	facilities = Facility.objects.values('id', 'facility').order_by('facility')
	context = {
		'envelope_id': envelope_id,
		"rejection_reasons": appendices_json(4),
		"facility_dropdown": utils.select( "facility_id",
										  {'k_col':'id', 'v_col':'facility', 'items':facilities },
										  "",
										  {'ng-model': 'v.facility_id'}),
	}
	return render(request, 'samples/verify.html', context)


def verify_envelope(request, envelope_id):	
	samples = Sample.objects.filter(envelope_id=envelope_id).order_by('locator_position')
	ret=[]
	for s in samples:
		ret.append({
				'patient_id': s.patient.id,
				'sample_id': s.id,
				'vl_sample_id': s.vl_sample_id,
				'locator_category': s.locator_category,
				'locator_position': s.locator_position,
				'envelope_number': s.envelope.envelope_number,
				'form_number': s.form_number,
				'sample_type':s.sample_type,
				'facility_id': s.facility_id,
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


def save_verify(request):
	r = request.GET;
	p = Patient.objects.get(pk=r['patient_id'])
	p.art_number = r.get('art_number', '')
	p.other_id = r.get('other_id', '')
	p.dob = utils.get_date(r, 'dob')
	p.gender = r.get('gender', '')
	p.save()

	s = Sample.objects.get(pk=r['sample_id'])
	s.facility_id = r.get('facility_id', 0)
	s.date_collected = utils.get_date(r, 'date_collected')
	s.treatment_initiation_date = utils.get_date(r, 'treatment_initiation_date')
	s.locator_category = r.get('locator_category', '')
	s.locator_position = r.get('locator_position', '')
	s.verified = 1;
	s.save()

	v = Verification()
	v.sample_id = r['sample_id']
	v.accepted = r.get('accepted', '')

	if(v.accepted==0):
		v.rejection_reason_id = r.get('rejection_reason_id', 0)

	v.verified_by_id = 1
	v_saved = v.save()

	return HttpResponse("saved")


def verify_list(request):

	search_val = request.GET.get('search_val', None)

	if search_val is not None:
		envelopes = Envelope.objects.filter(envelope_number__contains=search_val)
	else:
		envelopes = Envelope.objects.all()[:ENVS_LIMIT]
		

	return render(request, "samples/verify_list.html", {'envelopes': envelopes})

def appendices_json(cat_id):
	appendices = Appendix.objects.values('id', 'appendix').filter(appendix_category_id=cat_id)
	ret={}
	for a in appendices:
		ret[a['id']] = a['appendix']
	return json.dumps(ret)
		
class ListJson(BaseDatatableView):
	model = Sample
	columns = ['facility', 'facility.hub', 'form_number' ,'locator_position', 'vl_sample_id',  'date_collected', 'date_received', 'pk']
	order_columns = ['facility', 'facility.hub', 'form_number', 'locator_position', 'vl_sample_id', 'date_collected', 'date_received', ' ']
	max_display_length = 500

	def render_column(self, row, column):
		if column == 'facility':
			return '{0}'.format(row.facility)
		elif column == 'facility.hub':
			return '{0}'.format(row.facility.hub)
		elif column == 'locator_position':
			return '{0}{1}/{2}'.format(row.locator_category, 
									   row.envelope.envelope_number, 
									   row.locator_position)
		elif column == 'pk':
			#url0 = "/samples/show/{0}".format(row.pk)
			url0 = "#".format(row.pk)
			url1 = "/samples/edit/{0}".format(row.pk)
			links = utils.dropdown_links([
				{"label":"view", "url":url0},
				{"label":"edit", "url":url1},
				])
			return links
		else:
			return super(ListJson, self).render_column(row, column)
