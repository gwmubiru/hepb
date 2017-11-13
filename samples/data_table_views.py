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
		'facility', 'facility.hub', 'facility.district', 
		'sample_type', 'form_number', 'locator_position', 
		'date_collected', 'date_received', 'treatment_initiation_date',
		'patient.art_number','patient.other_id','verified', 'pk']

	order_columns = [
		'facility', 'facility.hub', 'facility.district', 
		'sample_type', 'form_number', 'locator_position', 
		'date_collected', 'date_received', 'treatment_initiation_date',
		'patient.art_number','patient.other_id','verified', '']

	max_display_length = 500		

	def render_column(self, row, column):
		verified = self.request.GET.get('verified')
		if column == 'facility':
			return '{0}'.format(row.facility.facility)
		elif column == 'facility.hub':
			return '%s' %(row.facility.hub.hub)
		elif column == 'facility.district':
			return '%s' %(row.facility.district.district)
		elif column == 'locator_position':
			return '{0}{1}/{2}'.format(row.locator_category, 
									   row.envelope.envelope_number, 
									   row.locator_position)
		elif column == 'pk':
			if verified:
				l = "/samples/verify/{0}".format(row.pk)
				links = "<a class='btn btn-xs btn-danger' href='%s'>verify</a>" %l
			else:
				url0 = "/samples/show/{0}".format(row.pk)
				url1 = "/samples/edit/{0}".format(row.pk)
				links = utils.dropdown_links([
					{"label":"view", "url":url0},
					{"label":"edit", "url":url1},
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
			h_cond = Q(facility__hub__hub__icontains=search)
			fn_cond = Q(form_number__icontains=search)
			loc_cond = sample_utils.locator_cond(search)
			st_cond = Q(sample_type=search[0])
			qs_params = f_cond | h_cond | fn_cond | st_cond
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
		
