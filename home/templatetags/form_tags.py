import ast, datetime
from django.db.models import Q
from django import template
from django.utils.safestring import mark_safe
from samples.models import Sample, Verification
from home import utils
from backend.models import Appendix,Facility
from django.http import HttpResponse

register = template.Library()


@register.simple_tag
def input(name="", value="", more="{}"):
	more = ast.literal_eval(more)
	more_attrs = "";
	for k,v in more.items():
		more_attrs += " %s='%s' " % (k, v)
	
	input_tag = "<input type='text' name='%s' value='%s' id='%s' %s class='form-control input-xs w-md' required >" % (name, value, name, more_attrs)
	return mark_safe(input_tag)


@register.simple_tag
def select(name="", data="{}", selected_val="", more="{}"):
	more = ast.literal_eval(more)
	more_attrs = "";
	for k,v in more.items():
		more_attrs += " %s='%s' " % (k, v)

	select_tag = "<select name='%s' id='%s'  %s class='form-control input-xs w-md' required>" % (name, name, more_attrs)

	data = ast.literal_eval(data)
	select_tag += "<option value=''></option>"
	for val,label in data.items():
		selected = "selected" if selected_val==val else ""
		select_tag += "<option value='%s' %s>%s</option>" % (val, selected, label)
	
	select_tag += "</select>"
	return mark_safe(select_tag)

@register.simple_tag
def checkbox(name="", selected_vals="", data="{}"):
	checkbox_tag = "";
	data = ast.literal_eval(data)
	for val,label in data.items():
		if selected_vals:
			if selected_vals.count(int(val)) > 0 :
				is_checked = "checked='checked'"
			else:
				is_checked = ""
			checkbox_tag += "<label class='checkbox-inline'> <input %s type='checkbox' name='%s' value='%s' id='%s' class='treatment_indication' tabindex='1'> %s </label>" % (is_checked, name, val,val,label)
		else:
			checkbox_tag += "<label class='checkbox-inline'> <input type='checkbox' name='%s' value='%s' id='%s' class='treatment_indication' tabindex='1'> %s </label>" % (name, val,val,label)
	
	return mark_safe(checkbox_tag)


@register.simple_tag
def yesno_select(name="", selected_val="", more="{'class':'form-control input-xs w-xs'}"):
	return select(name, "{'Y':'Yes', 'N':'No', 'L':'Left Blank'}", selected_val, more)
	

@register.simple_tag
def required_asta():
	return mark_safe("<span class='required_asta'>*</span>")


@register.simple_tag
def format_date(date_val, format = "%Y-%m-%d"):
	ret = ''
	try:
		ret = date_val.strftime(format)
	except:
		ret = ''

	return ret;


@register.simple_tag
def check_list(val="", choices="{}"):
	ret = ""
	checked = "<span class='glyphicon glyphicon-check print-check'></span>"
	unchecked = "<span class='glyphicon glyphicon-unchecked print-uncheck'></span>"
	choices = ast.literal_eval(choices)
	for k,lbl in choices.items():
		prefix = checked if k == val else unchecked
		ret += " %s %s " % (prefix, lbl)

	return ret

@register.simple_tag
def dropdown_links(links={}):
	links = ast.literal_eval(links)
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

	return mark_safe(ret %links_str)

@register.simple_tag
def quick_stats(request, contenttype, when='today', who='me', extra=''):
	#quick_stats request 'samples' 'all' 'all'
	#when: today, this_month, last_month, all
	#who: me, all
	#contenttype: samples, approvals
	today = datetime.datetime.today()
	last_month = utils.last_month()
	quick_stat = ''
	when_fltr = Q()
	if when == 'today':
		when_fltr = Q(created_at__range=utils.today_range())
	elif when == 'this_month':
		when_fltr = Q(created_at__year=today.year, created_at__month=today.month)
	elif when == 'last_month':
		when_fltr = Q(created_at__year=last_month.get('year'), created_at__month=last_month.get('month'))
	else:
		when_fltr = Q()

	who_fltr = Q()
	if who == 'me':
		who_fltr = Q(created_by=request.user) if contenttype=='samples' else Q(verified_by=request.user)
	else:
		who_fltr = Q()

	if contenttype == 'samples':
		quick_stat = Sample.objects.filter(who_fltr,when_fltr).count()
	elif contenttype == 'approvals':
		if extra=='pending':
			quick_stat = Sample.objects.filter(who_fltr,when_fltr,Q(verified=False)).count()
		elif extra=='completed':
			quick_stat = Sample.objects.filter(who_fltr,when_fltr,Q(verified=True)).count()
		else:
			quick_stat = Verification.objects.filter(who_fltr,when_fltr).count()
	return quick_stat

# def filter_queryset(self, qs):
# 		search = self.request.GET.get(u'search[value]', None)
# 		global_search = self.request.GET.get('global_search', None)

# 		if global_search:
# 			search = global_search
		
# 		if search:
# 			f_cond = Q(facility__facility__icontains=search)
# 			h_cond = Q(facility__hub__hub__icontains=search)
# 			fn_cond = Q(form_number__icontains=search)
# 			loc_cond = sample_utils.locator_cond(search)
# 			st_cond = Q(sample_type=search[0])
# 			qs_params = f_cond | h_cond | fn_cond | st_cond
# 			qs_params = qs_params | loc_cond if loc_cond else qs_params
# 			qs = qs.filter(qs_params)

# 		verified = self.request.GET.get('verified')
# 		if verified=='0' or verified=='1':
# 			qs = qs.filter(verified=verified)
# 		return qs.filter(envelope__sample_medical_lab=utils.user_lab(self.request))

@register.simple_tag
def mod(num, val):
	ans = val % num
	return num if ans==0 else ans
@register.simple_tag
def facility_dropdown():	
	facilities = Facility.objects.values('id', 'facility').filter(active=True)
	select_tag = "<option value=''></option>"
	selected_val = ""
	for facility in facilities:
		select_tag += "<option value='%s'>%s</option>" % (facility['id'], facility['facility'])
	return mark_safe(select_tag)