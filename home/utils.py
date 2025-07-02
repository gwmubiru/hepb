from datetime import *
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from django.db import IntegrityError
from django.contrib.auth.models import User
from datetime import date as dt, datetime as dtime
from backend.models import MedicalLab,Appendix
import re

ATTRS = {'class': 'form-control input-sm w-md', 'required': 'true'}
ATTRS_OPTIONAL = {'class': 'form-control input-sm w-md', }
ATTRS2 = {'class': 'form-control input-sm w-xs', 'required': 'true'}
ATTRS3 = {'class': 'form-control input-sm', 'required': 'true'}
ATTRS2_OPTIONAL = {'class': 'form-control input-sm w-xs', }
ATTRS_DATE = {'class': 'form-control input-sm w-xs date', }

# These utils are to hold raw python functions that can be used in views mainly

# automatically generate drop downs so that your template is a bit clean


def select(name="", data={}, selected_val="", more={}):
    # data to be a dictionary having 3 parts
    # data['k_col'] is the key column - to be used as value
    # data['v_col'] is the value column --to be used as label
    # data['items'] the actual data as an array from database to be displayed
    # for selection
    more_attrs = ""
    for k, v in more.items():
        more_attrs += " %s='%s' " % (k, v)

    select_tag = "<select name='%s' id='%s' %s class='form-control input-xs w-md' required>" % (
        name, name, more_attrs)
    select_tag += "<option value=''></option>"

    k_col = data.get('k_col', '')
    v_col = data.get('v_col', '')

    for item in data.get('items', []):
        val = item[k_col]
        label = item[v_col]
        selected = "selected='true'" if selected_val == val else ""
        select_tag += "<option %s value='%s'>%s</option>" % (
            selected, val, label)

    select_tag += "</select>"
    return select_tag


def select2(name="", data={}, selected_val="", more={}):
    more_attrs = ""
    for k, v in more.items():
        more_attrs += " %s='%s' " % (k, v)

    select_tag = "<select name='%s' %s required>" % (name, more_attrs)
    select_tag += "<option value=''></option>"

    k_col = data.get('k_col', '')
    v_col = data.get('v_col', '')

    for item in data.get('items', []):
        val = item.get(k_col)
        label = item.get(v_col)
        selected = "selected='true'" if selected_val == val else ""
        select_tag += "<option %s value='%s'>%s</option>" % (
            selected, val, label)

    select_tag += "</select>"
    return select_tag

# r represents request.POST


def get_date(r, date_field):
    date_val = r.get(date_field, None)
    ret = None if(date_val == '') else date_val
    return ret


def local_date(date_val, format="%d-%b-%Y"):
    format = "%Y-%m-%d"
    ret = ''
    try:
        ret = date_val.strftime(format)
    except BaseException:
        ret = ''

    return ret


def local_datetime(date_val, format="%d-%b-%Y"):
    format = "%Y-%m-%d %H:%M:%S"
    ret = ''
    try:
        ret = date_val.strftime(format)
    except BaseException:
        ret = ''

    return ret


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
    except BaseException:
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

def day(format=""):
    if format == 'dd':
        day = now().strftime('%d')
    else:
        day = now().day
    return day

def timestamp():
    return datetime.strftime(timezone.now(), '%Y%m%d%H%M%S')

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
        li = "<li><a href='%s'>%s</a></li>" % (
            link.get('url'), link.get('label'))
        links_str = links_str + li

    return ret % links_str


def btn_link(*args):
    url, label, sp_class = args
    return "<a class='btn btn-xs btn-danger %s' href='%s'>%s</a>" % (sp_class,url, label)


def eq(a, b):
    return a.upper() == b.upper()


def non_future_dates(Form, date_list):
    date_today = date.today()
    for i in date_list:
        i_date = Form.cleaned_data.get(i)
        if i_date is not None and str(i_date) > str(date_today):
            Form.add_error(i, "%s can not be in the future" %
                           (i.replace("_", " "),))


def user_lab(request):
    med_lab = MedicalLab.objects.get(pk=1)
    try:
        med_lab = request.user.userprofile.medical_lab
    except BaseException:
        pass
    return med_lab


def isnan(x):
    return str(x) == str(1e400 * 0)


def today_range():
    today_min = datetime.combine(date.today(), time.min)
    today_max = datetime.combine(date.today(), time.max)
    return (today_min, today_max)


def last_month():
    this_m = datetime.today().month
    last_m = this_m - 1
    if last_m == 0:
        month = 12
        year = datetime.today().year - 1
    else:
        month = last_m
        year = datetime.today().year
    return {'year': year, 'month': month}


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


def get_mysql_from_uk_date(date_str):
    #str_arr = date_str.split("/")
    #generated_date_str = str_arr[2]+'-'+str_arr[1]+'-'+str_arr[0]
    # return(dt. strptime(generated_date_str, '%y-%m-%d'))
    date_time_obj = datetime.strptime(date_str, '%d/%m/%Y')
    return date_time_obj.date()
    # return generated_date_str


def set_page_dates_format(date_obj):
    return str(date_obj.day).zfill(2) + '/' + \
        str(date_obj.month).zfill(2) + '/' + str(date_obj.year)+ ' ' +\
        str(date_obj.hour) + ':' + str(date_obj.minute) + ':' + str(date_obj.second)

def set_page_date_only_format(date_obj):
    return str(date_obj.day).zfill(2) + '/' + \
        str(date_obj.month).zfill(2) + '/' + str(date_obj.year)

def set_date_time_stamp(date_obj):
    return str(date_obj.year) + str(date_obj.month).zfill(2) +\
        str(date_obj.day).zfill(2) + \
        str(date_obj.hour)+ str(date_obj.minute) + str(date_obj.second)

def get_indices(arr, max_index, index):
    """This is a recursive function
    to find indices of a given number"""

    if max_index == 0:
        return arr
    else:
        arr.append(index)
        return get_indices(arr, max_index - 1, index + 1)

def timeConversion(s):
    a = ''
    if s[-2:] == "AM" :
        if s[:2] == '12':
            a = str('00' + s[2:8])
        else:
            a = s[:-2]
    else: 
        if s[:2] == '12':
            a = s[:-2]
        else:
            a = str(int(s[:2]) + 12) + s[2:8]
    return a


def removeSpecialCharactersFromString(str):
    return re.sub(r'[^a-zA-Z0-9]', '', str).lower()

def get_months():
    return ['01','02','03','04','05','06','07','08','09','10','11','12']

def get_users():
    return User.objects.all()

def getSupressionCutOff(sample_type):
    cut_off_dict = Appendix.objects.filter(appendix_category_id=9,tag=sample_type,is_active=True).values('id','appendix').first()
    return cut_off_dict;