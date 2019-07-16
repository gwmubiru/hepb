from home import utils
from worksheets.models import Worksheet, WorksheetBarCode

# def create_worksheet_ref_number(user):
# 	num = 0
# 	initials = 'XX'	
# 	try:
# 		initials = "%s%s" % (user.first_name[0],user.last_name[0])
# 	except:
# 		pass

# 	try:
# 		num = Worksheet.objects.filter(created_at__year=utils.year(), created_at__month=utils.month()).count()
# 	except:
# 		pass
	
# 	num = str(num+1)
# 	num = num.zfill(4)
# 	return "%s%s%s%s" %(utils.year('yy'), utils.month('mm'), initials.upper() , num)


def bar_code_generator():
	worksheet_bar_code = WorksheetBarCode.objects.latest('id')
	batch_prefix1 = worksheet_bar_code.batch_prefix1
	batch_prefix2 = worksheet_bar_code.batch_prefix2
	bar_code_counter = worksheet_bar_code.bar_code_counter
	codes_list = []
	for i in range(85):
		#increment the bar_code (0001 series) by 1
		bar_code = (batch_prefix1 + batch_prefix2 +(str(bar_code_counter)).zfill(4))
		#batch counter does not exceed 99
		if(bar_code_counter == 9999 and batch_prefix2 != 'Z'):
			bar_code_counter = 1
			batch_prefix2 = chr(ord(batch_prefix2)+1)
		if(batch_prefix2 == 'Z' and batch_prefix1 != 'Z'):
			batch_prefix1 = chr(ord(batch_prefix1)+1)
		codes_list.append(bar_code)
		bar_code_counter += 1
	#WorksheetBarCode.objects.all().delete()
	#barcode = WorksheetBarCode()
	worksheet_bar_code.batch_prefix1 = batch_prefix1
	worksheet_bar_code.batch_prefix2 = batch_prefix2
	worksheet_bar_code.bar_code_counter = bar_code_counter
	#delete the previously save bar code
	#WorksheetBarCode.object.filter(pk=worksheet_bar_code.id).delete()
	worksheet_bar_code.save()
	return codes_list

def create_worksheet_ref_number(worksheet_type, sample_type):
	num = 0
	wt = 'XX'
	if worksheet_type == 'A':
		wt = 'AB'
	elif worksheet_type == 'R':
		wt = 'CT'
	elif worksheet_type == 'C':
		wt = 'C8'	
	elif worksheet_type == 'H':
		wt = 'HL'

	w = Worksheet.objects.filter(created_at__year=utils.year(), created_at__month=utils.month()).last()

	if w:
		num = int(w.worksheet_reference_number[7:11])

	num = str(num+1)
	num = num.zfill(4)
	return "%s%s%s%s%s" %(utils.year('yy'), utils.month('mm'), wt, sample_type , num)
	
def sample_limit(worksheet_type):
	if worksheet_type == 'A':
		limit = 93
	elif worksheet_type == 'R':
		limit = 21
	elif worksheet_type == 'C':
		limit = 20
	elif worksheet_type == 'H':
		limit = 94
	else:
		limit = 21
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