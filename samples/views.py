import json
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
#from django.views.generic import TemplateView

from backend.models import Appendix,Facility
from .models import Patient, Sample, PatientPhone, Envelope, Verification
from home import utils

# Create your views here.

def create(request):
	facilities = Facility.objects.values('id', 'facility').order_by('facility')
	
	context = {
		"facilities": facilities,
		"facility_dropdown": utils.select("facility_id",{'k_col':'id', 'v_col':'facility', 'items':facilities }),
		"regimens_dropdown": appendix_select("current_regimen_id", 3),
		"tx_indication_dropdown": appendix_select("treatment_indication_id", 6),
		"f_reason_dropdown": appendix_select("failure_reason_id", 2),
		"vl_testing_dropdown": appendix_select("viral_load_testing_id", 8),
		"tb_tx_phase_dropdown": appendix_select("tb_treatment_phase_id", 5, "form-control input-xs w-md optional"),
		"adherence_dropdown": appendix_select("arv_adherence_id", 1, "form-control input-xs w-md optional"),

	}
	return render(request, 'samples/create.html', context)

def save(request):
	r = request.POST
	
	unique_id = "%s-A-%s" %(r.get('facility_id', 0), r.get('art_number', ''))
	p, pat_created = Patient.objects.get_or_create(
		unique_id=unique_id,
		art_number=r.get('art_number', ''),
		other_id=r.get('other_id', ''),
		gender=r.get('gender', ''),
		dob=utils.get_date(r, 'dob'),
		defaults={'created_by_id':1},
		)

	phone = r.get('patient_phone', None)
	if(phone!=None):
		pat_phone, pp_created = PatientPhone.objects.get_or_create(patient_id=p.id, phone=phone)

	enve,env_created = Envelope.objects.get_or_create(envelope_number=r.get('locator_envelope', ''))

	s = Sample()
	s.patient_id = p.id
	s.patient_unique_id = p.unique_id
	s.locator_category = r.get('locator_category', '')
	s.envelope_id = enve.id
	s.locator_position = r.get('locator_position', '')
	s.vl_sample_id = "8"
	s.form_number = r.get('form_number', '')
	s.facility_id = r.get('facility_id', 0)
	s.current_regimen_id = r.get('current_regimen_id', 0)
	s.pregnant = r.get('pregnant', '')
	#s.anc_number = r.get('anc_number', '')
	s.anc_number = 'pool'
	s.breast_feeding = r.get('breast_feeding', '')
	s.active_tb_status = r.get('active_tb_status', '')
	s.date_collected = utils.get_date(r, 'date_collected')
	s.date_received = utils.get_date(r, 'date_received')
	s.treatment_inlast_sixmonths = r.get('treatment_inlast_sixmonths', '')
	s.treatment_initiation_date = utils.get_date(r, 'treatment_initiation_date')
	s.sample_type = r.get('sample_type', '')
	s.viral_load_testing_id = r.get('viral_load_testing_id', 0)
	s.treatment_indication_id = r.get('treatment_indication_id', 0)
	s.treatment_indication_other = r.get('treatment_indication_other', '')
	#s.treatment_line_id = r.get('treatment_line_id', 0)
	s.treatment_line_id = 1
	s.failure_reason_id = r.get('failure_reason_id', 0)
	s.tb_treatment_phase_id = r.get('tb_treatment_phase_id', 0)
	s.arv_adherence_id = r.get('arv_adherence_id', 0)

	vl_tesing = r.get('vl_tesing', '')

	s.routine_monitoring = True if vl_tesing=='routine' else False
	s.routine_monitoring_last_test_date = utils.get_date(r, 'routine_monitoring_last_test_date')
	s.routine_monitoring_last_value = r.get('routine_monitoring_last_value', '')
	s.routine_monitoring_last_sample_type = r.get('routine_monitoring_last_sample_type', None)

	s.repeat_testing = True if vl_tesing=='repeat' else False
	s.repeat_testing_last_test_date = utils.get_date(r, 'repeat_testing_last_test_date')
	s.repeat_testing_last_value = r.get('repeat_testing_last_value', '')
	s.repeat_testing_last_sample_type = r.get('repeat_testing_last_sample_type', None)

	s.suspected_treatment_failure = True if vl_tesing=='suspected' else False
	s.suspected_treatment_failure_last_test_date = utils.get_date(r, 'suspected_treatment_failure_last_test_date')
	s.suspected_treatment_failure_last_value = r.get('suspected_treatment_failure_last_value', '')
	s.suspected_treatment_failure_last_sample_type = r.get('suspected_treatment_failure_last_sample_type', None)

	s.created_by_id = 1

	s.save()	

	return render(request, 'samples/create.html', {'success_message':'Sample details successfully saved',})
	
	
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


def appendices_json(cat_id):
	appendices = Appendix.objects.values('id', 'appendix').filter(appendix_category_id=cat_id)
	ret={}
	for a in appendices:
		ret[a['id']] = a['appendix']
	return json.dumps(ret)
		