from home import utils
from worksheets.models import Worksheet,WorksheetEnvelope
from samples.models import Sample, Envelope
import re


def create_worksheet_ref_number(sample_type,worksheet_id):
	num = 0

	w = Worksheet.objects.filter(created_at__year=utils.year(), created_at__month=utils.month(), id__lte = worksheet_id).count()
	
	if w:
		num = w
	num = str(num +1)
	num = num.zfill(3)

	return "%s%s%s%s" %(utils.year('yy'), utils.month('mm'), sample_type , num)
	
def sample_limit(machine_type):
	if machine_type == 'A':
		limit = 93
	elif machine_type == 'R':
		limit = 21
	elif machine_type == 'C':
		limit = 20
	elif machine_type == 'H':
		limit = 94
	else:
		limit = 94
	return limit

def sample_pads(worksheet):
	if worksheet.machine_type == 'H':
		i = 0
	elif worksheet.include_calibrators:
		i = 11
	else:
		i = 3
	return i
def random_codes():
	return 51254

def get_worksheet_envelopes(wksht_id,obj_str = ''):
	envelopes = Envelope.objects.raw('select envelope_number, e.id from vl_worksheet_samples ws INNER JOIN vl_samples s ON s.id = ws.sample_id and ws.worksheet_id = %s INNER JOIN vl_envelopes e ON e.id = s.envelope_id where ws.worksheet_id = %s GROUP BY e.id' %(wksht_id,wksht_id))
	if(obj_str == 'obj'):
		return envelopes
	env_str = ''
	separator = ','
	for envelope in envelopes:
		if envelope == envelopes[-1]:
			separator = ''
		env_str = env_str+'<a href="/samples/search/?search_val=%s&search_env=1" style="margin-left:5px;">%s</a>%s'%(envelope.envelope_number,envelope.envelope_number,separator)
	return env_str


def generate_barcodes(envelope_number,sample_type):
	max_num = 99 if sample_type == 'P' else 20
	env_num = re.sub('[^A-Za-z0-9]+', '', envelope_number)
	barcodes = []
	for i in range(max_num):
		i = i+1
		app_str = '0'+str(i) if i < 10 else str(i)
		barcodes.append(env_num+app_str)
	return barcodes

def create_worksheet_envelope(envelope_id,worksheet_id,user_id):
	worksheet, created = WorksheetEnvelope.objects.update_or_create(
		envelope_id = envelope_id,
		worksheet_id = worksheet_id,
		the_creator_id = user_id,
		defaults={'envelope_id': envelope_id,'worksheet_id':worksheet_id}
	)
	return True