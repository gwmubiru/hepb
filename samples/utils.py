import json

from home import utils
from backend.models import Facility
from .models import Sample,ClinicalRequestForm, Envelope

def locator_id_exists(data):
	env = Envelope.objects.filter(envelope_number=data.get('envelope_number')).first()
	loc_exists = False
	if env:
		loc_exists = Sample.objects.filter(envelope=env, locator_position=data.get('locator_position')).exists()
	return loc_exists	

def initial_env_number():
	return "%s%s-" %(utils.year('yy'), utils.month('mm'))

def create_sample_id():
	smpl_id = 0

	try:
		samples = Sample.objects.values("vl_sample_id").order_by("-created_at")[:1]
		vl_sample_id = samples[0].get('vl_sample_id')
		arr = vl_sample_id.split('/')
		smpl_id = int(arr[0])
	except:
		pass
	
	smpl_id = str(smpl_id+1)
	smpl_id = smpl_id.zfill(6)
	return "%s/%s%s" %(smpl_id, utils.year('yy'), utils.month('mm'))

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