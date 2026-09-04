import json
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from django.conf import settings
from django.db import models
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect

from .models import Sample, Envelope
from home import utils
from home import programs
from home import db_aliases
#import utils as sample_utils
from . import utils as sample_utils
from datetime import datetime, date, timedelta
import logging

class ListJson(BaseDatatableView):
	model = Sample
	columns = [
		'facility_reference','barcode', 'sample_type', 'program', 'date_collected','treatment_initiation_date',
		'date_received', 'patient.hep_number','patient.other_id', 'patient.facility.district', 'patient.facility', 'pk']

	order_columns = [
		'facility_reference',
		'barcode',
		'sample_type',
		'program_code',
		'date_collected',
		'treatment_initiation_date',
		'date_received',
		'patient__hep_number',
		'patient__other_id',
		'facility__district__district',
		'facility__facility',
		''
	]

	max_display_length = 500		

	def get_initial_queryset(self):
		db_alias = db_aliases.get_program_db_alias(programs.get_active_program_code(self.request))
		return (
			Sample.objects.using(db_alias)
			.select_related(
				'patient__facility__district',
				'facility__district',
				'sample_reception__facility__district',
				'tracking_code',
			)
			.all()
		)

	def _safe_related(self, obj, attr_path, default=''):
		try:
			current = obj
			for attr in attr_path.split('.'):
				current = getattr(current, attr)
				if current is None:
					return default
			return current if current is not None else default
		except (ObjectDoesNotExist, AttributeError):
			return default

	def _display_facility_name(self, row):
		patient_facility = self._safe_related(row, 'patient.facility.facility')
		reception_facility = self._safe_related(row, 'sample_reception.facility.facility')
		legacy_facility = self._safe_related(row, 'facility.facility')
		return patient_facility or reception_facility or legacy_facility

	def _display_district_name(self, row):
		patient_district = self._safe_related(row, 'patient.facility.district.district')
		reception_district = self._safe_related(row, 'sample_reception.facility.district.district')
		legacy_district = self._safe_related(row, 'facility.district.district')
		return patient_district or reception_district or legacy_district

	def render_column(self, row, column):
		verified = self.request.GET.get('verified')
		verify_url =  "/samples/verify/{0}".format(row.pk)
		show_url = "/samples/show/{0}".format(row.pk)
		edit_url = "/samples/edit/{0}".format(row.pk)
		#edit_received_url = "/samples/edit_received/{0}".format(row.pk)
		l = verify_url if verified else show_url
		if column == 'facility':
			facility_name = self._display_facility_name(row)
			if row.is_study_sample and facility_name:
				return 'Study - ' + facility_name
			return facility_name
		elif column == 'facility.district':
			return self._display_district_name(row)
		elif column == 'patient.hep_number':
			return self._safe_related(row, 'patient.hep_number')
		elif column == 'barcode':
			return "<a href='%s' target='_blank'>%s</a>" %(show_url,row.barcode)
		elif column == 'facility_reference':
			return row.facility_reference if row.facility_reference else row.form_number
		elif column == 'locator_position':
			locator_id = '{0}'.format(row.locator_category)
			return "<a href='%s' target='_blank'>%s</a>" %(show_url,locator_id)
		elif column == 'date_received':
			if row.date_received:
				#return row.envelope.created_at.strftime("%d/%m/%Y").__str__()
				return row.date_received.strftime("%d/%m/%Y").__str__()
			else:
				return ''
		elif column == 'program':
			return row.get_program_code_display() if row.program_code else ''
		elif column == 'date_collected' and row.date_collected:
			return row.date_collected.strftime("%d/%m/%Y").__str__()
		elif column == 'pk':
			if verified:
				links = "<a class='btn btn-xs btn-danger' href='%s'>approve</a>" %verify_url
				links = "approved" if verified =="1" else links
			else:
				if self.request.GET.get('is_data_entered') == 'W' or row.is_data_entered == 0:
					links = utils.dropdown_links([
					{"label":"edit received","url":"/samples/edit_received/{0}".format(row.pk)},
					])
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
		search = search.strip() if search else ''
		has_search = bool(search)
		is_data_entered = self.request.GET.get('is_data_entered')
		sample_without_results = self.request.GET.get('sample_without_results')
		hie_samples_pending_reception = self.request.GET.get('hie_samples_pending_reception')
		no_result = self.request.GET.get('no_result')
		tracking_code_id = self.request.GET.get('tracking_code_id')
		cut_off_date = date(settings.LIST_CUT_OFF_YEAR, settings.LIST_CUT_OFF_MONTH,settings.LIST_CUT_OFF_DATE)

		qs = qs.filter(created_at__gte=cut_off_date)
		if tracking_code_id:
			qs = qs.filter(tracking_code_id=tracking_code_id)
		elif is_data_entered == '0':
			qs = qs.filter(patient_id__isnull=True)
		elif sample_without_results == '0':
			qs = qs.filter(sampleidentifier__sample_id__isnull=True)
		elif is_data_entered == 'W':
			qs = qs.filter(locator_category='W')
		elif hie_samples_pending_reception == '1':
			qs = qs.filter(facility_reference__isnull=False, date_received__isnull=True)
		elif not has_search:
			qs = qs.filter(patient_id__isnull=False)
		qs = programs.filter_queryset_by_program(self.request, qs, 'program_code')
		if no_result:
			qs = qs.filter(id__gte=6000000,result__isnull=True)
		if search:
			if search.isdigit() or search[:-1].isdigit():
				qs = qs.filter(
					Q(form_number=search) |
					Q(barcode=search) |
					Q(barcode2=search) |
					Q(facility_reference=search)
				)
			else:
				qs = qs.filter(
					Q(form_number__startswith=search) |
					Q(barcode__startswith=search) |
					Q(barcode2__startswith=search) |
					Q(facility_reference__startswith=search)
				)
		return qs.order_by('-created_at')

class VerifyListJson(BaseDatatableView):
	model = Sample
	columns = ['form_number', 'barcode','patient.facility', 'patient.facility.district', 'patient.hep_number','patient.gender', 'date_collected',
		 'pk']
	order_columns = ['form_number', 'barcode']
	max_display_length = 500

	def get_initial_queryset(self):
		return Sample.objects.using(db_aliases.get_program_db_alias(programs.get_active_program_code(self.request))).all()
	def render_column(self, row, column):
		if(column == 'pk'):
			url = "/samples/verify/{0}".format(row.pk)
			return utils.btn_link(url, 'Verify','verify')
		else:
			return super(VerifyListJson, self).render_column(row, column)

	def filter_queryset(self, qs):
		search = self.request.GET.get(u'search[value]', None)
		verified = self.request.GET.get(u'verified[value]', None)
		global_search = self.request.GET.get('global_search', None)
		
		qs_params = Q(verified=0)
		if search:
			qs_params = Q(barcode=search) | Q(form_number=search) 
		qs = programs.filter_queryset_by_program(self.request, qs, 'program_code')
		return qs.filter(qs_params).order_by('barcode')





def envelope_list_json(request):
	r = request.GET
	envelopes = __get_envelopes(r,request)
	envelopes_data = envelopes.get('envelopes_data')
	data = []
	for e in envelopes_data:
		data.append([
			"<a href='/samples/search/?search_val=%s&approvals=1&search_env=1'>%s</a>"%(e.envelope_number,e.envelope_number),
			e.s_count,e.entered_count,e.p_count,
			utils.local_datetime(e.created_at),
			"<a href='/samples/search/?search_val=%s&approvals=1&search_env=1'>view</a>"%e.envelope_number,
			])

	return HttpResponse(json.dumps({
				"draw":r.get('draw'),
				"recordsTotal": envelopes.get('recordsTotal'),
				"recordsFiltered":envelopes.get('recordsFiltered'),
				"data":data,
				}))

def __get_envelopes(r,request):
	start = int(r.get('start'))
	length = int(r.get('length'))
	db_alias = db_aliases.get_program_db_alias(programs.get_active_program_code(request))
	f_query = Q(sample_medical_lab=utils.user_lab(request))
	active_program_code = programs.get_active_program_code(request)
	if active_program_code:
		f_query = f_query & Q(program_code=int(active_program_code))

	s_count = models.Count('sample',filter=Q(sample_medical_lab=utils.user_lab(request)))
	p_count = models.Count(models.Case(models.When(sample__verified=False, then=1)))
	entered_count = models.Count(models.Case(models.When(sample__is_data_entered=True, then=1)))

	data = Envelope.objects.using(db_alias).annotate(s_count=s_count, entered_count=entered_count, p_count=p_count,).filter(f_query).order_by('-created_at')[start:start+length]

	recordsTotal =  Envelope.objects.using(db_alias).count()
	recordsFiltered = recordsTotal if not f_query else Envelope.objects.using(db_alias).filter(f_query).count()
	return {'envelopes_data':data, 'recordsTotal':recordsTotal, 'recordsFiltered': recordsFiltered}


def tracking_codes_json(request):
	r = request.GET
	start = int(r.get('start', 0))
	length = int(r.get('length', 10))
	search = (r.get(u'search[value]', '') or '').strip()
	db_alias = db_aliases.get_program_db_alias(programs.get_active_program_code(request))

	qs = (
		Sample.objects.using(db_alias)
		.filter(tracking_code_id__isnull=False)
		.values(
			'tracking_code_id',
			'tracking_code__code',
			'tracking_code__created_at',
			'tracking_code__facility__facility',
			'tracking_code__facility__district__district',
		)
		.annotate(sample_count=Count('id'))
	)
	if search:
		qs = qs.filter(
			Q(tracking_code__code__startswith=search) |
			Q(tracking_code__facility__facility__startswith=search) |
			Q(tracking_code__facility__district__district__startswith=search)
		)

	records_total = (
		Sample.objects.using(db_alias)
		.filter(tracking_code_id__isnull=False)
		.values('tracking_code_id')
		.distinct()
		.count()
	)
	records_filtered = qs.count()
	rows = qs.order_by('-tracking_code__created_at')[start:start + length]

	data = []
	for row in rows:
		tracking_code = row.get('tracking_code__code') or ''
		tracking_code_id = row.get('tracking_code_id') or ''
		samples_url = '/samples/list/?tracking_code_id={0}&tracking_code={1}'.format(tracking_code_id, tracking_code)
		data.append([
			"<a href='{0}'>{1}</a>".format(samples_url, tracking_code),
			row.get('tracking_code__facility__facility') or '',
			row.get('tracking_code__facility__district__district') or '',
			row.get('sample_count') or 0,
			utils.local_datetime(row.get('tracking_code__created_at')),
			"<a href='{0}'>view samples</a>".format(samples_url),
		])

	return HttpResponse(json.dumps({
		"draw": r.get('draw'),
		"recordsTotal": records_total,
		"recordsFiltered": records_filtered,
		"data": data,
	}))


def vl_list(request):
	return render(request, 'samples/vl_list.html')

def vl_list_data(request):
	r = request.GET
	samples = __get_samples(r, request)
	samples_data = samples.get('samples_data')
	data = []
	for s in samples_data:
		data.append(
			[
			s.facility_reference,
			s.barcode,
			'{0}{1}/{2}'.format(s.locator_category, s.envelope.envelope_number, s.locator_position),
			s.get_sample_type_display(),
			s.get_program_code_display() if s.program_code else '',
			utils.local_date(s.date_collected),
			utils.local_date(s.treatment_initiation_date),
			s.date_received,
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

def __get_samples(r, request):
	start = int(r.get('start'))
	length = int(r.get('length'))
	filter_query = __get_filter_query(r, request)
	db_alias = db_aliases.get_program_db_alias(programs.get_active_program_code(request))

	samples_data = Sample.objects.using(db_alias).filter(filter_query).order_by('-envelope__envelope_number')[start:start+length]

	recordsTotal =  Sample.objects.using(db_alias).count()
	recordsFiltered = recordsTotal if not filter_query else Sample.objects.using(db_alias).filter(filter_query).count()
	return {'samples_data':samples_data, 'recordsTotal':recordsTotal, 'recordsFiltered': recordsFiltered}

def __get_filter_query(r, request):
	qs_params = Q()
	search = r.get(u'search[value]', None)
	global_search = r.get('global_search', None)
	active_program_code = programs.get_active_program_code(request)

	if global_search:
		search = global_search.strip()
		
	if search:
		search = search.strip()
		fn_cond = Q(form_number__icontains=search)
		loc_cond = sample_utils.locator_cond(search)
		qs_params = fn_cond

	
	verified = r.get('verified')
	if verified=='0' or verified=='1':
		qs_params = Q(verified=int(verified))
	if active_program_code:
		qs_params = qs_params & Q(program_code=int(active_program_code))
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
