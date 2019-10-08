from datetime import *
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from django.db import IntegrityError
from django.contrib.auth.models import User

from backend.models import MedicalLab


ATTRS = {'class':'form-control input-sm w-md', 'required':'true'}
ATTRS_OPTIONAL = {'class':'form-control input-sm w-md', }
ATTRS2 = {'class':'form-control input-sm w-xs', 'required':'true'}
ATTRS2_OPTIONAL = {'class':'form-control input-sm w-xs', }
ATTRS_DATE = {'class':'form-control input-sm w-xs date', }
TREATMENT_INFO_OPTIONS = "{'84':'Cirrhosis/APRI &gt; 2', '85':'ALT/AST Persistently abnormal', '86':'Viral Load &gt; 20,000 IU/ML','87':'HIV Co-Infection'}"


#These utils are to hold raw python functions that can be used in views mainly

#automatically generate drop downs so that your template is a bit clean
def select(name="", data={}, selected_val="", more={}):
	# data to be a dictionary having 3 parts
	# data['k_col'] is the key column - to be used as value
	# data['v_col'] is the value column --to be used as label
	# data['items'] the actual data as an array from database to be displayed for selection
	more_attrs = "";
	for k,v in more.items():
		more_attrs += " %s='%s' " % (k, v)

	select_tag = "<select name='%s' id='%s' %s class='form-control input-xs w-md' required>" % (name, name, more_attrs)
	select_tag += "<option value=''></option>"

	k_col = data.get('k_col','')
	v_col = data.get('v_col','')

	for item in data.get('items', []):
		val = item[k_col]
		label = item[v_col]
		selected = "selected='true'" if selected_val==val else ""
		select_tag += "<option %s value='%s'>%s</option>" % (selected, val, label)
	
	select_tag += "</select>"
	return select_tag

def select2(name="", data={}, selected_val="", more={}):
	more_attrs = "";
	for k,v in more.items():
		more_attrs += " %s='%s' " % (k, v)

	select_tag = "<select name='%s' %s required>" % (name, more_attrs)
	select_tag += "<option value=''></option>"

	k_col = data.get('k_col','')
	v_col = data.get('v_col','')

	for item in data.get('items', []):
		val = item.get(k_col)
		label = item.get(v_col)
		selected = "selected='true'" if selected_val==val else ""
		select_tag += "<option %s value='%s'>%s</option>" % (selected, val, label)
	
	select_tag += "</select>"
	return select_tag

#r represents request.POST
def get_date(r, date_field):
	date_val = r.get(date_field, None)
	ret = None if(date_val=='') else date_val
	return ret


def local_date(date_val, format = "%d-%b-%Y"):
	format = "%Y-%m-%d"
	ret = ''
	try:
		ret = date_val.strftime(format)
	except:
		ret = ''

	return ret;
def display_date(date_val):
	format = "%d-%b-%Y"
	ret = ''
	try:
		ret = date_val.strftime(format)
	except:
		ret = ''

	return ret;

def local_datetime(date_val, format = "%d-%b-%Y"):
	format = "%Y-%m-%d %H:%M:%S"
	ret = ''
	try:
		ret = date_val.strftime(format)
	except:
		ret = ''

	return ret;
def display_date_spaced(date_val):
	format = "%d %b %Y"
	ret = ''
	try:
		ret = date_val.strftime(format)
	except:
		ret = ''

	return ret;

def dictfetchall(cursor):
	"Return all rows from a cursor as a dict"
	columns = [col[0] for col in cursor.description]
	return [
		dict(zip(columns, row))
		for row in cursor.fetchall()
	]


def __get_or_create_user(username, email, password, *args, **kwargs):
	user = User.objects.filter(email=email).first()
	if not user:
		user = User.objects.create_user(username, email, password)

	return user


def get_or_create_user(email):
	#email = email if email != '@guest' else 'guest@guest.guest'
	#c_user = email.partition('@')
	email = email
	username = email
	password = email
	user = __get_or_create_user(username, email, password)
	return user


def delete_item(d, key):
	try:
		del d[key]
	except:
		pass
	
	return d

def now():
	return timezone.now()

def year(format=""):
	if format == 'yyyy':
		year = now().strftime('%Y')
	elif format == 'yy':
		year = now().strftime('%y')
	else:
		year = now().year
	return year

def month(format=""):
	if format == 'mm':
		month = now().strftime('%m')
	else:
		month = now().month
	return month

def dropdown_links(links):
	ret = """<div class="btn-group">
				<button type="button" class="btn btn-xs btn-danger dropdown-toggle" data-toggle="dropdown" aria-expanded="false">
					Options 
					<span class="caret"></span>
				</button>
				<ul class="dropdown-menu" role="menu">
					%s
				</ul>
			</div>"""

	links_str = ""
	for link in links:
		li = "<li><a href='%s'>%s</a></li>" %(link.get('url'), link.get('label'))
		links_str = links_str + li

	return ret %links_str

def btn_link(*args):
	url,label = args
	return "<a class='btn btn-xs btn-danger' href='%s'>%s</a>" %(url, label)

def eq(a,b):
	return a.upper() == b.upper()

def non_future_dates(Form, date_list):
	date_today = date.today()
	for i in date_list:
		i_date = Form.cleaned_data.get(i)
		if i_date != None and str(i_date) > str(date_today):
			Form.add_error(i, "%s can not be in the future" %(i.replace("_"," "),) )

def user_lab(request):
	med_lab = MedicalLab.objects.get(pk=1)
	try:
		med_lab = request.user.userprofile.medical_lab
	except:
		pass
	return med_lab

def isnan(x):
	return str(x) == str(1e400*0)

def today_range():
	today_min = datetime.combine(date.today(), time.min)
	today_max = datetime.combine(date.today(), time.max)
	return (today_min, today_max)

def last_month():
	this_m = datetime.today().month
	last_m = this_m-1
	if last_m==0:
		month = 12
		year = datetime.today().year-1
	else:
		month = last_m
		year = datetime.today().year	
	return {'year':year, 'month':month}

def compare_dates(**kwargs):
	first_date = kwargs.get('first_date')
	second_date = kwargs.get('second_date')
	operator = kwargs.get('operator')
	ret = False
	if first_date and second_date and operator:
		if operator == 'eq':
			ret = first_date == second_date
		elif operator == 'lt':
			ret = first_date < second_date
		elif operator == 'gt':
			ret = first_date > second_date
		elif operator == 'lte':
			ret = first_date <= second_date
		elif operator == 'gte':
			ret = first_date >= second_date
		else:
			ret = False
	return ret

def getattr_ornone(obj, attr):
	if hasattr(obj, attr):
		return getattr(obj, attr)
	else:
		return None

def get_gender(gender):
	if(gender == 'M'):
		return 'Male'
	elif(gender == 'F'):
		return 'Female'
	else:
		return 'Left Blank'

def get_drug_name(val):
	if(val == 1):
		return 'Tenofovir'
	elif(val == 2):
		return Entecavir
	else:
		return ''
def translate_yes_no(opt):
	if(opt == 'Y'):
		return 'Yes'
	elif(opt == 'N'):
		return 'No'
	else:
		return ''
