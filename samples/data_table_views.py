import json
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q
from django.db import models
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect

from .models import Sample, Envelope
from home import utils
import utils as sample_utils

class ListJson(BaseDatatableView):
	model = Sample
	columns = [
		'form_number', 'locator_position', 'sample_type', 'date_collected','treatment_initiation_date',
		'date_received', 'patient.name','patient.hep_number','patient.other_id', 'facility.district', 'facility', 'verified', 'pk']

	order_columns = [
		'facility', 'facility.district', 
		'sample_type', 'form_number', 'locator_position', 
		'date_collected', 'date_received', 'treatment_initiation_date',
		'patient.hep_number','patient.other_id','verified', '']

	max_display_length = 500		

	def render_column(self, row, column):
		verified = self.request.GET.get('verified')
		verify_url =  "/samples/verify/{0}".format(row.pk)
		show_url = "/samples/show/{0}".format(row.pk)
		edit_url = "/samples/edit/{0}".format(row.pk)
		l = verify_url if verified else show_url
		if column == 'facility':
			if(row.is_study_sample):
				return 'Study - '+'{0}'.format(row.facility.facility)
			else:
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
				links = "approved" if verified =="1" else links
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

		qs_params = Q()
		if search:
			#f_cond = Q(facility__facility__icontains=search)
			#h_cond = Q(facility__hub__hub__icontains=search)
			if  search.isdigit() or search[:-1].isdigit():
				return qs.filter(form_number=search)
			else:
				fn_cond = Q(form_number__icontains=search)
				loc_cond = sample_utils.locator_cond(search)
				#st_cond = Q(sample_type=search[0])
				qs_params = fn_cond | loc_cond if loc_cond else fn_cond

		#qs_params = qs_params & Q(envelope__sample_medical_lab=utils.user_lab(self.request))
		verified = self.request.GET.get('verified')
		qs_params = Q(verified=int(verified)) if verified=='0' or verified=='1' else qs_params
		if qs_params:
			return qs.filter(qs_params).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"}).order_by('-envelope__envelope_number','lposition_int')
		else:
			return qs.all().extra({'lposition_int': "CAST(locator_position as UNSIGNED)"}).order_by('-envelope__envelope_number','lposition_int')
		#return qs.filter(envelope__sample_medical_lab=utils.user_lab(self.request))
		

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


# class EnvelopeListJson(BaseDatatableView):
# 	model = Envelope
# 	columns = ['envelope_number', 'pk']
# 	order_columns = ['envelope_number', '']

# 	def render_column(self, row, column):
# 		if(column == 'pk'):
# 			url = "/samples/verify/{0}".format(row.pk)
# 			return utils.btn_link(url, 'Verify')
# 		else:
# 			return super(EnvelopeListJson, self).render_column(row, column)

def envelope_list_json(request):
	r = request.GET
	envelopes = __get_envelopes(r)
	envelopes_data = envelopes.get('envelopes_data')
	data = []
	for e in envelopes_data:
		data.append([
			"<a href='/samples/search/?search_val=%s&approvals=1&search_env=1'>%s</a>"%(e.envelope_number,e.envelope_number),
			e.s_count,e.p_count,
			e.c_count, utils.local_datetime(e.created_at),
			"<a href='/samples/search/?search_val=%s&approvals=1&search_env=1'>view</a>"%e.envelope_number,
			])

	return HttpResponse(json.dumps({
				"draw":r.get('draw'),
				"recordsTotal": envelopes.get('recordsTotal'),
				"recordsFiltered":envelopes.get('recordsFiltered'),
				"data":data,
				}))

def __get_envelopes(r):
	start = int(r.get('start'))
	length = int(r.get('length'))
	filter_query = Q()

	
	s_count = models.Count('sample')
	p_count = models.Count(models.Case(models.When(sample__verified=False, then=1)))
	c_count = models.Count(models.Case(models.When(sample__verified=True, then=1)))

	data = Envelope.objects.annotate(s_count=s_count, p_count=p_count, c_count=c_count).filter(filter_query).order_by('-created_at')[start:start+length]

	recordsTotal =  Envelope.objects.count()
	recordsFiltered = recordsTotal if not filter_query else Envelope.objects.filter(filter_query).count()
	return {'envelopes_data':data, 'recordsTotal':recordsTotal, 'recordsFiltered': recordsFiltered}


def vl_list(request):
	return render(request, 'samples/vl_list.html')

def vl_list_data(request):
	# columns = [
	# 	'form_number', 'locator_position', 'sample_type', 'date_collected','treatment_initiation_date',
	# 	'date_received', 'patient.art_number','patient.other_id', 'facility.district', 'facility', 'verified', 'pk']
	r = request.GET
	samples = __get_samples(r)
	samples_data = samples.get('samples_data')
	data = []
	for s in samples_data:
		data.append(
			[
			s.form_number,
			'{0}{1}/{2}'.format(s.locator_category, s.envelope.envelope_number, s.locator_position),
			s.get_sample_type_display(),
			utils.local_date(s.date_collected),
			utils.local_date(s.treatment_initiation_date),
			utils.local_date(s.date_received),
			s.patient.hep_number,
			s.patient.other_id,
			s.facility.district.district,
			s.facility.facility,
			__get_status(s),
			__get_links(s),			
			]
			)

	return HttpResponse(json.dumps({
				"draw":r.get('draw'),
				"recordsTotal": samples.get('recordsTotal'),
				"recordsFiltered":samples.get('recordsFiltered'),
				"data":data,
				}))

def __get_samples(r):
	start = int(r.get('start'))
	length = int(r.get('length'))
	filter_query = __get_filter_query(r)

	samples_data = Sample.objects.filter(filter_query).order_by('-envelope__envelope_number')[start:start+length]

	recordsTotal =  Sample.objects.count()
	recordsFiltered = recordsTotal if not filter_query else Sample.objects.filter(filter_query).count()
	return {'samples_data':samples_data, 'recordsTotal':recordsTotal, 'recordsFiltered': recordsFiltered}

def __get_filter_query(r):
	qs_params = Q()
	search = r.get(u'search[value]', None)
	global_search = r.get('global_search', None)

	if global_search:
		search = global_search.strip()
		
	if search:
		search = search.strip()
		#f_cond = Q(facility__facility__icontains=search)
		#h_cond = Q(facility__hub__hub__icontains=search)
		fn_cond = Q(form_number__icontains=search)
		loc_cond = sample_utils.locator_cond(search)
		#st_cond = Q(sample_type=search[0])
		#qs_params = fn_cond | loc_cond if loc_cond else fn_cond
		qs_params = fn_cond

	
	verified = r.get('verified')
	if verified=='0' or verified=='1':
		qs_params = Q(verified=int(verified))
	return qs_params


def __get_status(s):
	if hasattr(s, 'verification'):
		return 'accepted' if s.verification.accepted else 'rejected'
	else:
		return 'pending'

def __get_links(s):
	show_url = "/samples/show/{0}".format(s.pk)
	edit_url = "/samples/edit/{0}".format(s.pk)
	links = utils.dropdown_links([
			{"label":"view", "url":show_url},
			{"label":"edit", "url":edit_url},
			])

	return links