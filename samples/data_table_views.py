from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q

from .models import Sample, Envelope
from home import utils
import utils as sample_utils

class ListJson(BaseDatatableView):
	# <th>Facility</th>
	# 			<th>Hub</th>
	# 			<th>District</th>
	# 			<th>Sample Type</th>
	# 			<th>Form Number</th>
	# 			<th>Locator ID</th>
	# 			<th>Date Collected</th>
	# 			<th>Date Received</th>
	# 			<th>Initiation Date</th>
	# 			<th>ART Number</th>
	# 			<th>Other ID</th>
	# 			<th>Verified</th>
	# 			<th>...</th>

	model = Sample
	columns = [
		'form_number', 'locator_position', 'sample_type', 'date_collected','treatment_initiation_date',
		'date_received', 'patient.art_number','patient.other_id', 'facility.district', 'facility', 'verified', 'pk']

	order_columns = [
		'facility', 'facility.district', 
		'sample_type', 'form_number', 'locator_position', 
		'date_collected', 'date_received', 'treatment_initiation_date',
		'patient.art_number','patient.other_id','verified', '']

	max_display_length = 500		

	def render_column(self, row, column):
		verified = self.request.GET.get('verified')
		verify_url =  "/samples/verify/{0}".format(row.pk)
		show_url = "/samples/show/{0}".format(row.pk)
		edit_url = "/samples/edit/{0}".format(row.pk)
		l = verify_url if verified else show_url
		if column == 'facility':
			return '{0}'.format(row.facility.facility)
		elif column == 'facility.district':
			return '%s' %(row.facility.district.district)
		elif column == 'form_number':
			return "<a href='%s' target='_blank'>%s</a>" %(show_url,row.form_number)
		elif column == 'locator_position':
			locator_id = '{0}{1}/{2}'.format(row.locator_category, 
									   row.envelope.envelope_number, 
									   row.locator_position)
			return "<a href='%s' target='_blank'>%s</a>" %(show_url,locator_id)
		elif column == 'verified':
			if row.verified:
				try:
					return "accepted" if row.verification else "rejected" 
				except: 
					return ""
			else:
				return "pending"
		elif column == 'pk':
			if verified:
				links = "<a class='btn btn-xs btn-danger' href='%s'>approve</a>" %verify_url
			else:
				links = utils.dropdown_links([
					{"label":"view", "url":show_url},
					{"label":"edit", "url":edit_url},
					])
				
			return links
		else:
			return super(ListJson, self).render_column(row, column)

	def filter_queryset(self, qs):
		search = self.request.GET.get(u'search[value]', None)
		global_search = self.request.GET.get('global_search', None)

		if global_search:
			search = global_search
		
		if search:
			f_cond = Q(facility__facility__icontains=search)
			#h_cond = Q(facility__hub__hub__icontains=search)
			fn_cond = Q(form_number__icontains=search)
			loc_cond = sample_utils.locator_cond(search)
			st_cond = Q(sample_type=search[0])
			qs_params = f_cond | fn_cond | st_cond
			qs_params = qs_params | loc_cond if loc_cond else qs_params
			qs = qs.filter(qs_params)

		verified = self.request.GET.get('verified')
		if verified=='0' or verified=='1':
			qs = qs.filter(verified=verified)
		return qs.filter(envelope__sample_medical_lab=utils.user_lab(self.request))
		

class VerifyListJson(BaseDatatableView):
	model = Envelope
	columns = ['envelope_number', 'pk']
	order_columns = ['envelope_number', '']

	def render_column(self, row, column):
		if(column == 'pk'):
			url = "/samples/verify/{0}".format(row.pk)
			return utils.btn_link(url, 'Verify')
		else:
			return super(VerifyListJson, self).render_column(row, column)



class ClassName(object):
	"""docstring for ClassName"""
	def __init__(self, arg):
		super(ClassName, self).__init__()
		self.arg = arg
		
