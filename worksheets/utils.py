from home import utils
from worksheets.models import Worksheet

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

def create_worksheet_ref_number(worksheet_type, sample_type):
	num = 0
	wt = 'XX'
	if worksheet_type == 'A':
		wt = 'AB'
	elif worksheet_type == 'R':
		wt = 'CT'
	elif worksheet_type == 'C':
		wt = 'C8'	

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
	else:
		limit = 21
	return limit
