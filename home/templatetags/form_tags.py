import ast
from django import template
from django.utils.safestring import mark_safe

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
		selected = "selected='true'" if selected_val==val else ""
		select_tag += "<option %s value='%s'>%s</option>" % (selected, val, label)
	
	select_tag += "</select>"
	return mark_safe(select_tag)


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