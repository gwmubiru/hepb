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