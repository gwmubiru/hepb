from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q

from .models import Sample, Envelope
from home import utils

def locator_cond(search=""):
	cond = False
	try:
		if len(search) >= 12:
			search_arr = search.split("/")
			cond = Q(
				envelope__envelope_number=search_arr[0][1:],
				locator_category=search_arr[0][:1],
				locator_position=search_arr[1]
				)
	except:
		pass
	return cond


class ListJson(BaseDatatableView):
	model = Sample
	columns = ['facility', 'facility.hub', 'form_number', 'locator_position', 'date_collected', 'date_received', 'pk']
	order_columns = ['facility', 'facility.hub', 'form_number', 'locator_position', 'date_collected', 'date_received', '']
	max_display_length = 500

	def render_column(self, row, column):
		if column == 'facility':
			return '{0}'.format(row.facility.facility)
		elif column == 'facility.hub':
			return '%s' %(row.facility.hub.hub)
		elif column == 'locator_position':
			return '{0}{1}/{2}'.format(row.locator_category, 
									   row.envelope.envelope_number, 
									   row.locator_position)
		elif column == 'pk':
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
		if search:
			f_cond = Q(facility__facility__istartswith=search)
			h_cond = Q(facility__hub__hub__istartswith=search)
			fn_cond = Q(form_number__istartswith=search)
			loc_cond = locator_cond(search)
			qs_params = f_cond | h_cond | fn_cond
			qs_params = qs_params | loc_cond if loc_cond else qs_params
			qs = qs.filter(qs_params)

		return qs
			# use parameters passed in GET request to filter queryset

			# simple example:
			# search = self.request.GET.get(u'search[value]', None)
			# if search:
			# 	qs = qs.filter(name__istartswith=search)

			# more advanced example using extra parameters
			# filter_customer = self.request.GET.get(u'customer', None)

			# if filter_customer:
			# 	customer_parts = filter_customer.split(' ')
			# 	qs_params = None
			# 	for part in customer_parts:
			# 		q = Q(customer_firstname__istartswith=part)|Q(customer_lastname__istartswith=part)
			# 		qs_params = qs_params | q if qs_params else q
			# 	qs = qs.filter(qs_params)
			# return qs

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
