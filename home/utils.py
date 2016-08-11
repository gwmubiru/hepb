from django.db import IntegrityError
from django.contrib.auth.models import User

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

def dictfetchall(cursor):
	"Return all rows from a cursor as a dict"
	columns = [col[0] for col in cursor.description]
	return [
		dict(zip(columns, row))
		for row in cursor.fetchall()
	]


def get_or_create_user(username, email, password, *args, **kwargs):
	try:
		user = User.objects.create_user(username, email, password)
	except IntegrityError:
		user = User.objects.get(username=username, email=email)

	return user