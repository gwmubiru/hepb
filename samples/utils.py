from django.db.models import F

from home import utils
from .models import Sample,ClinicalRequestForm

def initial_env_number():
	return "%s%s-" %(utils.year('yy'), utils.month('mm'))

def create_sample_id():
	smpl_id = 0

	try:
		sample = Sample.objects.get(
			created_at__year=utils.year(),
			created_at__month=utils.month()
			)
		arr = sample.vl_sample_id.split('/')
		smpl_id = int(arr[0])
	except:
		pass
	
	smpl_id = str(smpl_id+1)
	smpl_id = smpl_id.zfill(6)
	return F("%s/%s%s" %(smpl_id, utils.year('yy'), utils.month('mm')))

def get_facility_by_form(form_number):
	facility_id = 0
	try:
		form = ClinicalRequestForm.objects.get(form_number=form_number)
		facility_id = form.dispatch.facility.id
	except:
		pass

	return facility_id