from home import utils
from worksheets.models import Worksheet

def create_worksheet_ref_number(user):
	num = 0
	initials = "%s%s" % (user.first_name[0],user.last_name[0])
	try:
		num = Worksheet.objects.filter(created_at__year=utils.year(), created_at__month=utils.month()).count()
	except:
		pass
	
	num = str(num+1)
	num = num.zfill(4)
	return "%s%s%s%s" %(utils.year('yy'), utils.month('mm'), initials.upper() , num)