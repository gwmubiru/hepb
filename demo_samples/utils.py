import datetime as dt
import json
from django.db.models import Q

from home import utils
from backend.models import Facility
from .models import Sample,ClinicalRequestForm, Envelope, Patient
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

def initial_env_number():
	return "%s%s-" %(utils.year('yy'), utils.month('mm'))

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

def get_district_hub_by_facility(facility_id):
	ret = {}
	try:
		facility = Facility.objects.get(pk=facility_id)
		ret = {
			'district': facility.district.district,
			'hub': facility.hub.hub,
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

def generate_ref_number():
	return dt.datetime.today().strftime("%y%m%d%H%M%S")

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