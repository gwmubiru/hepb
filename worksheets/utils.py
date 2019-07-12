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
	batch_counter = worksheet_bar_code.batch_counter
	bar_code_counter = worksheet_bar_code.bar_code_counter
	batch_prefix = worksheet_bar_code.batch_prefix
	codes_list = []
	for i in range(85):
		#increment the bar_code (0001 series) by 1
		bar_code = (batch_prefix + (str(batch_counter).zfill(2)) +(str(bar_code_counter)).zfill(4))
		bar_code_counter = bar_code_counter+1
		#batch counter does not exceed 99
		if(batch_counter == 99):
			batch_counter = 1
			batch_prefix = chr(ord(batch_prefix)+1)
		if(bar_code_counter == 9999):
			bar_code_counter = 1
			batch_counter = batch_counter+1
		codes_list.append(bar_code)
	#truncate table and add the last generated bar codes
	#have not seen django truncate equivalent but this delete() can work
	WorksheetBarCode.objects.all().delete()
	barcode = WorksheetBarCode()
	barcode.batch_prefix = batch_prefix
	barcode.batch_counter = batch_counter
	barcode.bar_code_counter = bar_code_counter
	barcode.bar_code = bar_code
	barcode.save()
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