from datetime import date, datetime
import json
from django.db.models import Q

from home import utils
from backend.models import Facility
from .models import Sample, Envelope, Patient,Verification
from samples.models import Sample, Envelope,PendingReceptionQueue,RejectedSamplesRelease
from worksheets.models import WorksheetSample
from results.models import Result
from django.http import HttpResponse


def locator_id_exists(data, sample_id=None):
	env = Envelope.objects.filter(envelope_number=data.get('envelope_number')).first()
	loc_exists = False
	if env:
		fltr = Q(envelope=env,locator_position=data.get('locator_position'))
		fltr = ~Q(pk=sample_id) & fltr if sample_id else fltr
		loc_exists = Sample.objects.filter(fltr).first()
	return loc_exists

def initiation_date_valid(data):
	tx_initiation_date = data.get('treatment_initiation_date')
	dob = data.get('dob')
	collection_date = data.get('date_collected')
	valid = True
	if tx_initiation_date and dob and tx_initiation_date < dob and collection_date < tx_initiation_date:
		valid = False
	return valid

def collection_date_valid(data):
	tx_collection_date = data.get('date_collected')
	dob = data.get('dob')
	valid = True
	if tx_collection_date and dob and tx_collection_date < dob:
		valid = False
	return valid

def reception_date_valid(data):
	tx_collection_date = data.get('date_collected')
	reception_date = data.get('date_received')
	valid = True
	if tx_collection_date and reception_date and reception_date < tx_collection_date:
		valid = False
	return valid

def initial_env_number():
	return "%s%s-" %(utils.year('yy'), utils.month('mm'))


def envelope_number_from_barcode(barcode):
	if barcode and len(barcode) >= 8 and barcode[:8].isdigit():
		return "%s-%s" % (barcode[:4], barcode[4:8])
	return None


def resolve_posted_envelope_id(request):
	env_id = request.POST.get('envelope_id')
	if env_id:
		return env_id

	envelope_number = request.POST.get('envelope_number')
	if not envelope_number:
		envelope_number = envelope_number_from_barcode(request.POST.get('the_barcode'))

	if envelope_number:
		envelope = Envelope.objects.filter(envelope_number=envelope_number).first()
		if envelope:
			return envelope.id

	return get_envelope_id(request)

def create_sample_id():
	# smpl_id = 0

	# try:
	# 	samples = Sample.objects.values("vl_sample_id").order_by("-created_at")[:1]
	# 	vl_sample_id = samples[0].get('vl_sample_id')
	# 	arr = vl_sample_id.split('/')
	# 	smpl_id = int(arr[0])
	# except:
	# 	pass
	
	# smpl_id = str(smpl_id+1)
	# smpl_id = smpl_id.zfill(6)
	s_count = Sample.objects.filter(created_at__year=utils.year(),created_at__month=utils.month()).count()
	s_count += 1
	return "%s/%s%s" %(str(s_count).zfill(6), utils.year('yy'), utils.month('mm'))

def get_facility_by_form(form_number):
	facility_id = 0
	try:
		form = ClinicalRequestForm.objects.get(form_number=form_number)
		facility_id = form.dispatch.facility.id
	except:
		pass

	return facility_id

def get_district_hub_by_facility(facility_id, db_alias='default'):
	ret = {}
	try:
		facility = Facility.objects.using(db_alias).select_related('district', 'hub').get(pk=facility_id)
		ret = {
			'district': getattr(facility.district, 'district', ''),
			'hub': getattr(facility.hub, 'hub', ''),
			}
	except:
		pass

	return json.dumps(ret)


 
def locator_cond(search=""):
	cond = False
	try:
		if search[0] == 'R' or search[0] =='V':
			search = search[1:]

		if "/" in search:
			search_arr = search.split("/")
			cond = Q(
				envelope__envelope_number__icontains=search_arr[0],
				locator_position=search_arr[1]
				)
		else:
			cond = Q(envelope__envelope_number__icontains=search)
	except:
		pass
	return cond

def env_cond(search=""):
	cond = False
	try:
		if search[0] == 'R' or search[0] =='V':
			search = search[1:]

		if "/" in search:
			search_arr = search.split("/")
			cond = Q(envelope_number=search_arr[0])
		else:
			cond = Q(envelope_number=search)
	except:
		pass
	return cond

def exact_or_legacy_duplicate_cond(field_name, search_value):
	value = (search_value or '').strip()
	if not value:
		return Q()
	return Q(**{field_name: value}) | Q(**{field_name: '%s*' % value})

def generate_ref_number():
	return datetime.datetime.today().strftime("%y%m%d%H%M%S")

def set_dates_as_mysql(post_data):
	pst = post_data.copy()
	pst['date_collected'] =  utils.get_mysql_from_uk_date(pst.get('date_collected'))
	if pst['dob']:
		pst['dob'] =  utils.get_mysql_from_uk_date(pst.get('dob'))
	if pst['treatment_initiation_date']:
		pst['treatment_initiation_date'] =  utils.get_mysql_from_uk_date(pst.get('treatment_initiation_date'))
	if pst['last_test_date']:
		pst['last_test_date'] =  utils.get_mysql_from_uk_date(pst.get('last_test_date'))
	return pst

def set_page_dates_format(post_data):
	pst = post_data
	pst['date_collected'] =  utils.set_page_dates_format(pst.get('date_collected'))
	if pst['dob']:
		pst['dob'] =  utils.set_page_dates_format(pst.get('dob'))
	if pst['treatment_initiation_date']:
		pst['treatment_initiation_date'] =  utils.set_page_dates_format(pst.get('treatment_initiation_date'))
	if pst['last_test_date']:
		pst['last_test_date'] =  utils.set_page_dates_format(pst.get('last_test_date'))
	return pst
def get_next_barcode(barcode,sample_type):
	next_barcode = int(barcode)+1
	position = int(barcode[-2:])+1
	ret_barc = 'kl'
	if sample_type == 'P' and position < 100:
		ret_barc = next_barcode
	if sample_type == 'D' and position < 21:
		ret_barc = next_barcode
	return  ret_barc

def update_envelope_status(sample,status):

	if sample.locator_position == '01':
		#mark the envelope_received
		if status == 'received':
			sample.envelope.is_received = 1
		if status == 'is_data_entered':
			sample.envelope.is_data_entered = 1
				
		sample.envelope.save()
	return True

#s is the sample instance
def update_result_models(s):
	ws = WorksheetSample.objects.filter(instrument_id=s.barcode).first()
	if ws:
		if ws.sample_id is None:
			ws.sample = s
			ws.save()
			ws.sample_identifier.sample = s
			ws.sample_identifier.save()
			#check there is a result
		rst = Result.objects.filter(worksheet_sample_id=ws.id).first()
		if rst:
			if rst.sample_id is None:
				rst.sample = s 
				rst.save()
			#If result is not yet released, release it
			if rst.resultsqc.released == False and s.verified:
				rst.resultsqc.released = True
				rst.resultsqc.released_at = datetime.now()
				rst.resultsqc.save()

def is_rec_and_entery_data_mataching(sample,request_art, request_facility_id):
	rec_raw_hep_number = sample.reception_hep_number or ""
	reception_hep_number = utils.removeSpecialCharactersFromString(rec_raw_hep_number)
	req_request_art = request_art or ""
	data_entry_hep_number = utils.removeSpecialCharactersFromString(req_request_art)
	
	if (reception_hep_number.lower() == data_entry_hep_number.lower()) and (sample.facility_id == int(request_facility_id)):
		return 0
	return 1

def get_envelope(envelope_number,sample_type,user_lab,env_status_update):
	ret = []
	envelope = Envelope.objects.filter(envelope_number=envelope_number).first()
	if envelope is None:
		envelope = Envelope()
		envelope.envelope_number=envelope_number
		envelope.sample_type=sample_type
		envelope.sample_medical_lab=user_lab
		envelope.stage=2
		envelope.save()
		#if from worksheet create, update the queue
		if env_status_update == 'has_result':
			recep_queue = PendingReceptionQueue()
			recep_queue.envelope = envelope
			recep_queue.status =1
			recep_queue.envelope_number =envelope_number
			recep_queue.save()
			
	if env_status_update == 'has_result':
		envelope.has_result = 1
		envelope.save()

	return envelope

def get_envelope_id(request):
	env_id = request.POST.get('envelope_id')
	if env_id == '' or env_id is None:
		envelope = Envelope.objects.filter(envelope_number=request.POST.get('envelope_number')).first()
		if envelope is None:
			envelope = Envelope()
			envelope.envelope_number=request.POST.get('envelope_number')
			envelope.sample_type=request.POST.get('sample_type')
			envelope.sample_medical_lab=utils.user_lab(request)
			envelope.stage=2
			envelope.is_received=1
			#envelope.save()
		env_id = envelope.id
		#clear the reception que
		env_queue = PendingReceptionQueue.objects.filter(envelope = envelope)
		if env_queue:
			env_queue.delete()
	return env_id

def save_verification_details(sample,request):
	v = Verification.objects.filter(sample=sample).first()
	v = v if v else Verification()
	v.pat_edits = 0
	v.sample_edits = 0
	v.sample = sample
	
	v.accepted = True 		
	v.rejection_reason_id = None

	v.verified_by = request.user
	v.save()
	return True
	
def update_worksheet_sample(s):
	# if the sample has been tested, updated it
	ws = WorksheetSample.objects.filter(instrument_id=s.barcode).first()
	if ws and ws.sample_id is None:
		ws.sample = s
		ws.save()

	return True

def release_rejected_sample(sample, user_id):
	other_params = {
		'released': 1,
		'reject_released_by_id':  user_id,
		'released_at': datetime.now().date(),
	}
	rsr, rsr_created = RejectedSamplesRelease.objects.update_or_create(sample=sample, defaults=other_params)
	return True
