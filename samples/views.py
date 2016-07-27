from django.shortcuts import render
#from django.views.generic import TemplateView

from backend.models import Appendix,Facility
from .models import Patient, Sample, PatientPhone, Envelope
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
	p = Patient()
	p.unique_id = "%s-A-%s" %(r.get('facility_id', 0), r.get('art_number', ''))
	p.art_number = r.get('art_number', '')
	p.other_id = r.get('other_id', '')
	p.gender = r.get('gender', '')
	p.dob = utils.getDate(r, 'dob')
	p.created_by_id = 1
	p.save()

	phone = r.get('patient_phone', None)
	if(phone!=None):
		pat_phone = PatientPhone(patient_id=p.id, phone=phone)
		pat_phone.save()


	s = Sample()
	s.patient_id = p.id
	s.patient_unique_id = p.unique_id
	s.locator_category = r.get('locator_category', '')
	s.locator_envelope = r.get('locator_envelope', '')
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
	s.date_collected = utils.getDate(r, 'date_collected')
	s.date_received = utils.getDate(r, 'date_received')
	s.treatment_inlast_sixmonths = r.get('treatment_inlast_sixmonths', '')
	s.treatment_initiation_date = utils.getDate(r, 'treatment_initiation_date')
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
	s.routine_monitoring_last_test_date = utils.getDate(r, 'routine_monitoring_last_test_date')
	s.routine_monitoring_last_value = r.get('routine_monitoring_last_value', '')
	s.routine_monitoring_last_sample_type = r.get('routine_monitoring_last_sample_type', None)

	s.repeat_testing = True if vl_tesing=='repeat' else False
	s.repeat_testing_last_test_date = utils.getDate(r, 'repeat_testing_last_test_date')
	s.repeat_testing_last_value = r.get('repeat_testing_last_value', '')
	s.repeat_testing_last_sample_type = r.get('repeat_testing_last_sample_type', None)

	s.suspected_treatment_failure = True if vl_tesing=='suspected' else False
	s.suspected_treatment_failure_last_test_date = utils.getDate(r, 'suspected_treatment_failure_last_test_date')
	s.suspected_treatment_failure_last_value = r.get('suspected_treatment_failure_last_value', '')
	s.suspected_treatment_failure_last_sample_type = r.get('suspected_treatment_failure_last_sample_type', None)

	s.created_by_id = 1

	s.save()

	enve = Envelope.objects.get_or_create(envelope_number=s.locator_envelope)	

	return render(request, 'samples/create.html', {'success_message':'Sample details successfully saved',})
	
	
def appendix_select(name="", cat_id=0, clss='form-control input-xs w-md'):
	apendices = Appendix.objects.values('id','appendix')
	more = {'class': clss}
	return utils.select(name,{'k_col':'id', 'v_col':'appendix', 'items':apendices.filter(appendix_category_id=cat_id)},"",more)


# patient = models.ForeignKey(Patient)
# 	patient_unique_id = models.CharField(max_length=128)
# 	locator_category = models.CharField(max_length=1, choices=( ('V', 'V'), ('R', 'R') ))
# 	locator_envelope = models.CharField(max_length=10)
# 	locator_position = models.CharField(max_length=3)
# 	vl_sample_id = models.CharField(max_length=128)
# 	form_number = models.CharField(max_length=64)
# 	facility = models.ForeignKey(backend.Facility)
# 	current_regimen = models.ForeignKey(backend.Appendix, related_name='current_regimen')
# 	pregnant = models.CharField(max_length=1, choices=YES_NO_CHOICES)
# 	anc_number = models.CharField(max_length=64) #anc number for pregnant women
# 	breast_feeding = models.CharField(max_length=1, choices=YES_NO_CHOICES)
# 	active_tb_status = models.CharField(max_length=1, choices=YES_NO_CHOICES)
# 	date_collected = models.DateField() #Date on which the sample was collected from the patient
# 	date_received = models.DateField #Date received at CPHL
# 	treatment_inlast_sixmonths = models.CharField(max_length=1, choices=YES_NO_CHOICES)
# 	treatment_initiation_date = models.DateField()
# 	sample_type = models.CharField(max_length=1, choices=SAMPLE_TYPES)
# 	viral_load_testing = models.ForeignKey(backend.Appendix, related_name='viral_load_testing')
# 	treatment_indication = models.ForeignKey(backend.Appendix, related_name='treatment_indication')
# 	treatment_indication_other = models.CharField(max_length=64)
# 	treatment_line = models.ForeignKey(backend.Appendix, related_name='treatment_line')
# 	failure_reason = models.ForeignKey(backend.Appendix, related_name='failure_reason')
# 	tb_treatment_phase = models.ForeignKey(backend.Appendix, related_name='tb_treatment_phase')
# 	arv_adherence = models.ForeignKey(backend.Appendix, related_name='arv_adherence')
# 	routine_monitoring = models.BooleanField(default=False)