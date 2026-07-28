import builtins
import json, os, glob, calendar
import csv, pandas, io, json
import openpyxl
import re
from urllib.parse import urlencode
from datetime import *
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.http import JsonResponse
from django.db.models import Count, Q
from django import *

from backend.models import Appendix,Facility,MedicalLab
from .models import *
from django.forms import formset_factory
from django.forms import *
from .forms import *
from home import utils
from home import programs
from home import db_aliases
from . import utils as sample_utils
from django.db import connections
from django.db import transaction
from worksheets.models import Worksheet,WorksheetSample
from results.models import Result,ResultsQC
from results import utils as result_utils
from . import utils as worksheet_utils
import requests
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.management import call_command
from .services import SampleService
from vl import services as vl_services

ENVS_LIMIT = 1000
SAMPLES_LIMIT = 1000
TRACKING_CODE_RECEPTION_FILTER = Q(date_received__isnull=True)
DUPLICATE_FACILITY_REFERENCE_MESSAGE = "Olaba kisoboka? Taracking code cant be shared between facilities"
TRACKING_CODE_FACILITY_LOCK_MESSAGE = "Tekisoboka. Tracking code can't be shared between facilities."
TRACKING_CODE_FACILITY_MISMATCH_MESSAGE = "Warning: this tracking code belongs to a different facility. Please check the selected facility or use the correct tracking code."
TRACKING_CODE_SAMPLE_FACILITY_MISMATCH_MESSAGE = "Warning: this sample belongs to a different facility from the tracking code. Please check the facility reference or tracking code."
DUPLICATE_BARCODE_MESSAGE = "This position has already been received. Enter a different position."
DR_BOX_NUMBER_RE = re.compile(r'^DR(\d{4})(\d{4})$')
DR_BOX_POSITION_RE = re.compile(r'^(DR\d{8})/(\d{3})$')
PLACEHOLDER_TRACKING_CODE_VALUES = {'none', 'non'}
SOURCE_SYSTEM_PENDING_PACKAGING_UPDATES = {
	'locator_position': None,
	'envelope_id': None,
	'barcode': None,
	'date_received': None,
	'stage': 25,
}


def _envelope_capacity(sample_type):
	return 99 if sample_type == 'P' else 20


def _format_locator_position(position):
	return str(position).zfill(2)


def _format_sample_barcode(envelope_number, locator_position):
	return sample_utils.format_locator_barcode(envelope_number, _format_locator_position(locator_position))


def _can_manage_envelope(envelope):
	return not envelope.sample_set.exclude(stage=0).exists()


def _return_source_system_sample_to_pending_packaging(sample):
	for field_name, value in SOURCE_SYSTEM_PENDING_PACKAGING_UPDATES.items():
		setattr(sample, field_name, value)
	sample.save(update_fields=builtins.list(SOURCE_SYSTEM_PENDING_PACKAGING_UPDATES.keys()))


def _normalize_dr_box_number(value):
	box_number = (value or '').strip().upper().replace(' ', '')
	match = DR_BOX_NUMBER_RE.match(box_number)
	if not match:
		raise ValueError('Box number must be in the format DR26055001.')
	year_month, running_number = match.groups()
	expected_year_month = datetime.now().strftime('%y%m')
	if year_month != expected_year_month:
		raise ValueError('Box number must start with the current year/month ' + expected_year_month + '.')
	if int(running_number) < 1:
		raise ValueError('Box running number must be greater than 0000.')
	return box_number


def _normalize_dr_box_position(value, expected_box_number=None):
	box_position = (value or '').strip().upper().replace(' ', '')
	match = DR_BOX_POSITION_RE.match(box_position)
	if not match:
		raise ValueError('Box position must be in the format DR26055001/001.')
	box_number, position = match.groups()
	if expected_box_number and box_number != expected_box_number:
		raise ValueError('Box position must belong to the selected box.')
	if int(position) < 1 or int(position) > 100:
		raise ValueError('Box position must be between 001 and 100.')
	return box_number, "{0}/{1}".format(box_number, position)


def _current_dr_box_prefix():
	return "DR" + datetime.now().strftime('%y%m')


def _get_facility_reference_conflict(facility_reference, facility_id, exclude_sample_id=None, db_alias='default'):
	facility_reference = (facility_reference or '').strip()
	if facility_reference == '' or not facility_id:
		return None

	# Pending package samples can arrive before reception without a tracking code.
	# Only tracked samples can prove that a tracking code is being reused across facilities.
	conflict_qs = (
		Sample.objects.using(db_alias)
		.filter(facility_reference=facility_reference, tracking_code_id__isnull=False)
		.exclude(facility_id=facility_id)
	)
	for placeholder_code in PLACEHOLDER_TRACKING_CODE_VALUES:
		conflict_qs = conflict_qs.exclude(tracking_code__code__iexact=placeholder_code)
	if exclude_sample_id:
		conflict_qs = conflict_qs.exclude(pk=exclude_sample_id)
	return conflict_qs.first()


def _find_existing_sample_for_reception(facility_reference, facility_id=None, db_alias='default'):
	facility_reference = (facility_reference or '').strip()
	if facility_reference == '':
		return None

	qs = (
		Sample.objects.using(db_alias)
		.select_related('patient')
		.filter(Q(facility_reference=facility_reference) | Q(barcode2=facility_reference))
	)
	if facility_id:
		sample = qs.filter(facility_id=facility_id).first()
		if sample:
			return sample
	return qs.first()


def _get_or_create_tracking_code(code, user_id, facility_id=None, db_alias='default'):
	code = (code or '').strip()
	if code == '' or _is_placeholder_tracking_code_value(code):
		return None

	tracking_code = TrackingCode.objects.using(db_alias).filter(code=code).first()
	if tracking_code is None:
		tracking_code = TrackingCode(code=code, creation_by_id=user_id)
		if facility_id:
			tracking_code.facility_id = facility_id
		tracking_code.save(using=db_alias)
		data = {
			"barcode": code,
			"user_id": 1,
			"numberofsamples": 1,
			"is_tracked_from_facility": 0,
			"transfer_to": settings.REF_LAB_ID,
			"ref_lab_id": settings.REF_LAB_ID,
			"is_to_be_transfered": 0,
			"receipt_date": "",
			"name_of_receiver": "Kakembo John"
		}
		requests.request("POST", settings.SAMPLE_TRACKING_URL, data=data)
	elif facility_id and not tracking_code.facility_id:
		tracking_code.facility_id = facility_id
		tracking_code.save(using=db_alias, update_fields=['facility', 'updated_at'])
	return tracking_code


def _is_placeholder_tracking_code_value(value):
	return (value or '').strip().lower() in PLACEHOLDER_TRACKING_CODE_VALUES


def _is_valid_tracking_code(tracking_code):
	return bool(tracking_code and not _is_placeholder_tracking_code_value(getattr(tracking_code, 'code', '')))


def _get_tracking_code_facility_mismatch(tracking_code, facility_id):
	if not _is_valid_tracking_code(tracking_code) or not facility_id or not tracking_code.facility_id:
		return False
	return str(tracking_code.facility_id) != str(facility_id)


def _should_block_tracking_code_facility_mismatch(sample, tracking_code, facility_id):
	if sample is not None:
		return False
	return _get_tracking_code_facility_mismatch(tracking_code, facility_id)


def _resolve_tracking_code(tracking_code_id, code, user_id, facility_id=None, db_alias='default'):
	code = (code or '').strip()
	tracking_code = None
	if tracking_code_id:
		candidate = TrackingCode.objects.using(db_alias).filter(pk=tracking_code_id).first()
		if _is_valid_tracking_code(candidate) and (code == '' or (candidate.code or '').strip() == code):
			tracking_code = candidate
	if tracking_code is None and code and not _is_placeholder_tracking_code_value(code):
		tracking_code = _get_or_create_tracking_code(code, user_id, facility_id, db_alias=db_alias)
	elif tracking_code and facility_id and not tracking_code.facility_id:
		tracking_code.facility_id = facility_id
		tracking_code.save(using=db_alias, update_fields=['facility', 'updated_at'])
	return tracking_code


def _resolve_tracking_code_for_sample(sample, tracking_code_id, code, user_id, facility_id=None, db_alias='default'):
	sample_tracking_code_id = getattr(sample, 'tracking_code_id', None)
	if sample_tracking_code_id:
		tracking_code = _get_tracking_code_by_id(sample_tracking_code_id, db_alias=db_alias)
		if _is_valid_tracking_code(tracking_code):
			if facility_id and not tracking_code.facility_id:
				tracking_code.facility_id = facility_id
				tracking_code.save(using=db_alias, update_fields=['facility', 'updated_at'])
			return tracking_code
		if str(tracking_code_id or '') == str(sample_tracking_code_id):
			tracking_code_id = None
	return _resolve_tracking_code(tracking_code_id, code, user_id, facility_id, db_alias=db_alias)


def _get_tracking_code_by_id(tracking_code_id, db_alias='default'):
	if not tracking_code_id:
		return None
	try:
		return TrackingCode.objects.using(db_alias).filter(pk=tracking_code_id).first()
	except (TypeError, ValueError):
		return None


def _sample_tracking_code_payload(sample, db_alias='default'):
	tracking_code_id = getattr(sample, 'tracking_code_id', None)
	if not tracking_code_id:
		return {
			'tracking_code_id': '',
			'tracking_code': '',
		}
	tracking_code = _get_tracking_code_by_id(tracking_code_id, db_alias=db_alias)
	if not _is_valid_tracking_code(tracking_code):
		return {
			'tracking_code_id': '',
			'tracking_code': '',
		}
	return {
		'tracking_code_id': getattr(tracking_code, 'id', '') or '',
		'tracking_code': getattr(tracking_code, 'code', '') or '',
	}


def _sample_patient_facility_mismatch(sample, tracking_code, db_alias='default'):
	if sample is None or tracking_code is None or not tracking_code.facility_id:
		return False
	if not sample.tracking_code_id:
		return False
	existing_tracking_code = getattr(sample, 'tracking_code', None)
	if existing_tracking_code is None:
		existing_tracking_code = _get_tracking_code_by_id(sample.tracking_code_id, db_alias=db_alias)
	if not _is_valid_tracking_code(existing_tracking_code):
		return False
	existing_tracking_facility_id = getattr(existing_tracking_code, 'facility_id', None)
	if existing_tracking_facility_id:
		return existing_tracking_facility_id != tracking_code.facility_id
	patient_facility_id = getattr(getattr(sample, 'patient', None), 'facility_id', None)
	if not patient_facility_id:
		return False
	return patient_facility_id != tracking_code.facility_id


def _sample_matches_tracking_code(sample, tracking_code):
	return bool(sample and tracking_code and sample.tracking_code_id and sample.tracking_code_id == tracking_code.id)


def _tracking_code_package_samples(tracking_code, db_alias='default'):
	if tracking_code is None:
		return []
	samples = (
		Sample.objects.using(db_alias)
		.select_related('patient')
		.filter(tracking_code=tracking_code)
		.filter(TRACKING_CODE_RECEPTION_FILTER)
		.order_by('id')
	)
	ret = []
	for sample in samples:
		patient = getattr(sample, 'patient', None)
		ret.append({
			'facility_reference': sample.facility_reference or sample.form_number or '',
			'hep_number': getattr(patient, 'hep_number', '') or sample.reception_hep_number or '',
			'date_collected': sample.date_collected.strftime('%Y-%m-%d') if sample.date_collected else '',
		})
	return ret


def _lookup_existing_sample_for_reception(facility_reference, facility_id=None, tracking_code=None, db_alias='default'):
	facility_reference = (facility_reference or '').strip()
	ret = {
		'hep_number': '',
		'date_collected': '',
		'err_msg': '',
		'is_dr': 0,
		'tracking_code_id': '',
		'tracking_code': '',
	}
	if facility_reference == '':
		ret['err_msg'] = 'Not found'
		return ret

	sample = _find_existing_sample_for_reception(facility_reference, facility_id, db_alias=db_alias)
	exclude_sample_id = sample.pk if _sample_matches_tracking_code(sample, tracking_code) else None
	conflict_sample = _get_facility_reference_conflict(facility_reference, facility_id, exclude_sample_id, db_alias=db_alias)
	if conflict_sample:
		ret['err_msg'] = DUPLICATE_FACILITY_REFERENCE_MESSAGE
		ret['facility_reference_conflict'] = 1
		return ret
	if sample:
		ret['facility_id'] = sample.facility_id or getattr(getattr(sample, 'patient', None), 'facility_id', None) or ''
		ret.update(_sample_tracking_code_payload(sample, db_alias=db_alias))

	if _sample_patient_facility_mismatch(sample, tracking_code, db_alias=db_alias):
		ret['err_msg'] = TRACKING_CODE_SAMPLE_FACILITY_MISMATCH_MESSAGE
		ret['tracking_facility_conflict'] = 1
		return ret

	if sample and sample.barcode2 == facility_reference and sample.barcode2 != sample.facility_reference:
		ret.update({
			'hep_number': getattr(getattr(sample, 'patient', None), 'hep_number', '') or '',
			'date_collected': sample.date_collected.strftime('%Y-%m-%d') if sample.date_collected else '',
			'err_msg': 'This is a DR sample.',
			'is_dr': 1,
		})
	elif sample and not sample.envelope_id and not sample.barcode:
		ret.update({
			'hep_number': getattr(getattr(sample, 'patient', None), 'hep_number', '') or sample.reception_hep_number or '',
			'date_collected': sample.date_collected.strftime('%Y-%m-%d') if sample.date_collected else '',
		})
	elif sample and (sample.envelope_id or sample.barcode):
		ret['err_msg'] = 'Already received'
	else:
		ret['err_msg'] = 'Not found'
	return ret


ALIS_PROGRAM_CODES = {
	'hepb': '1', 'hep_b': '1', 'hepatitis_b': '1', 'hbv': '1',
	'hepc': '2', 'hep_c': '2', 'hepatitis_c': '2', 'hcv': '2',
	'viral_load': '3', 'hiv_viral_load': '3', 'hiv_vl': '3', 'vl': '3',
}
PROGRAM_NAMES = {'1': 'HepB', '2': 'HepC', '3': 'HIV Viral Load'}


def _search_alis_facility_identifier(facility_identifier):
	facility_identifier = (facility_identifier or '').strip()
	if not facility_identifier:
		return {}
	token = getattr(settings, 'IRRDS_ALIS_BARCODE_SEARCH_TOKEN', '') or os.environ.get('IRRDS_ALIS_BARCODE_SEARCH_TOKEN', '')
	if not token:
		return {}
	url = getattr(settings, 'IRRDS_ALIS_BARCODE_SEARCH_URL', '') or os.environ.get(
		'IRRDS_ALIS_BARCODE_SEARCH_URL',
		'https://irrds.cphl.go.ug/api/alis/barcode/search',
	)
	try:
		response = requests.post(
			url,
			json={'barcode': facility_identifier},
			headers={'Content-Type': 'application/json', 'Authorization': 'Bearer {0}'.format(token)},
			timeout=10,
		)
		if response.status_code >= 400:
			return {}
		return response.json()
	except (ValueError, requests.RequestException):
		return {}


def _alis_systems(payload):
	systems = []
	found_in = payload.get('found_in') or []
	if isinstance(found_in, builtins.list):
		systems.extend(found_in)
	results = payload.get('results') or []
	if isinstance(results, builtins.list):
		for result in results:
			if isinstance(result, builtins.dict) and result.get('system'):
				systems.append(result.get('system'))
	return builtins.list(dict.fromkeys(str(system or '').strip() for system in systems if system))


def _alis_program_code(system_name):
	normalized = re.sub(r'[^a-z0-9]+', '_', (system_name or '').strip().lower()).strip('_')
	if normalized in ALIS_PROGRAM_CODES:
		return ALIS_PROGRAM_CODES[normalized]
	if 'hepatitis_b' in normalized or normalized.startswith('hepb'):
		return '1'
	if 'hepatitis_c' in normalized or normalized.startswith('hepc'):
		return '2'
	if 'viral_load' in normalized or normalized.startswith('hiv_vl'):
		return '3'
	return ''


def check_facility_identifier(request):
	facility_identifier = (request.GET.get('barcode') or '').strip()
	active_program_code = programs.get_active_program_code(request) or '1'
	ret = {'blocked': 0, 'system': '', 'message': ''}
	if not facility_identifier:
		return JsonResponse(ret)

	systems = _alis_systems(_search_alis_facility_identifier(facility_identifier))
	if not systems:
		return JsonResponse(ret)
	program_codes = {_alis_program_code(system) for system in systems}
	program_codes.discard('')
	if active_program_code in program_codes:
		return JsonResponse(ret)

	other_program_code = next(iter(program_codes), '')
	other_system = PROGRAM_NAMES.get(other_program_code, systems[0].replace('_', ' ').title())
	active_program = PROGRAM_NAMES.get(active_program_code, 'the selected program')
	ret.update({
		'blocked': 1,
		'system': other_system,
		'message': 'The facility identifier {0} belongs to {1}, not {2}.'.format(
			facility_identifier,
			other_system,
			active_program,
		),
	})
	return JsonResponse(ret)


def update_envelope_program_code(envelope_id, program_code):
	if envelope_id and program_code:
		Envelope.objects.filter(pk=envelope_id).update(program_code=program_code)


def posted_date(post_data, field_name):
	value = (post_data.get(field_name) or '').strip()
	if value == '':
		return None
	for date_format in ('%d/%m/%Y', '%Y-%m-%d'):
		try:
			return datetime.strptime(value, date_format).date()
		except ValueError:
			continue
	raise ValidationError('{0} has an invalid date format.'.format(value))


def _posted_sample_type(request):
	if sample_utils.is_hep_program_code(programs.get_active_program_code(request)):
		return 'P'
	sample_type = request.POST.get('sample_type')
	if sample_type in (None, '', 'None'):
		return None
	return sample_type


def _set_missing_sample_type(sample, request):
	if sample_utils.is_hep_program_code(programs.get_active_program_code(request)):
		sample.sample_type = 'P'
		return
	if sample.sample_type not in (None, ''):
		return
	sample_type = _posted_sample_type(request)
	if sample_type:
		sample.sample_type = sample_type


def _set_sample_type_from_request_or_envelope(sample, request, envelope_id=None):
	_set_missing_sample_type(sample, request)
	if sample.sample_type not in (None, ''):
		return
	resolved_envelope_id = envelope_id or sample.envelope_id
	if not resolved_envelope_id:
		return
	envelope = sample.envelope if sample.envelope_id == resolved_envelope_id and getattr(sample, 'envelope', None) else None
	if envelope is None:
		envelope = Envelope.objects.filter(pk=resolved_envelope_id).only('sample_type').first()
	if envelope and envelope.sample_type:
		sample.sample_type = envelope.sample_type


def get_session_program_code(request):
	code = programs.get_active_program_code(request)
	return int(code) if code else None


def get_dropdown_db_alias(request):
	return db_aliases.get_program_db_alias(programs.get_active_program_code(request))


def _get_existing_tracking_code(request, tracking_code_id='', code=''):
	db_alias = get_dropdown_db_alias(request)
	tracking_code = _get_tracking_code_by_id(tracking_code_id, db_alias=db_alias)
	if tracking_code is None and code:
		tracking_code = (
			TrackingCode.objects.using(db_alias)
			.select_related('facility')
			.filter(code=(code or '').strip())
			.first()
		)
	return tracking_code


def _get_tracking_context_from_request(request):
	tracking_code_id = request.GET.get('tracking_code_id') or request.GET.get('tr_code_id') or ''
	current_tr_code = request.GET.get('current_tr_code') or request.GET.get('tracking_code') or request.GET.get('code') or ''
	tracking_code = _get_existing_tracking_code(request, tracking_code_id, current_tr_code)
	if tracking_code:
		tracking_code_id = tracking_code.id
		current_tr_code = tracking_code.code
	return tracking_code, tracking_code_id or '', current_tr_code or ''


def _sample_reception_initial(tracking_code=None):
	initial = {
		'locator_category': 'V',
		'date_collected': datetime.now().date(),
		'date_received': datetime.now().date(),
	}
	if tracking_code and tracking_code.facility_id:
		initial['facility'] = tracking_code.facility_id
	return initial


def _receive_batch_tracking_context(tracking_code=None):
	return {
		'tracking_facility_id': tracking_code.facility_id if tracking_code and tracking_code.facility_id else '',
		'tracking_facility_lock_message': TRACKING_CODE_FACILITY_LOCK_MESSAGE,
	}


def _locator_lookup_values(request, barcode):
	raw_barcode = (barcode or '').strip()
	values = []

	def add(value):
		value = (value or '').strip()
		if value and value not in values:
			values.append(value)

	add(raw_barcode)
	compact_barcode = sample_utils.compact_envelope_number(raw_barcode)
	add(compact_barcode)

	active_program_code = programs.get_active_program_code(request)
	for candidate in (raw_barcode, compact_barcode):
		try:
			parsed_candidate = sample_utils.parse_locator_id(candidate, active_program_code)
		except ValueError:
			parsed_candidate = None
		if parsed_candidate:
			add(parsed_candidate.get('barcode'))

	if sample_utils.is_hep_program_code(active_program_code) and compact_barcode:
		expected_prefix = sample_utils.envelope_prefix_for_program(active_program_code)
		has_hep_prefix = compact_barcode[0] in sample_utils.HEP_PREFIX_PROGRAMS
		if expected_prefix and not has_hep_prefix and compact_barcode.isdigit() and len(compact_barcode) >= 6:
			try:
				parsed_candidate = sample_utils.parse_locator_id(expected_prefix + compact_barcode, active_program_code)
			except ValueError:
				parsed_candidate = None
			if parsed_candidate:
				add(parsed_candidate.get('barcode'))

	return values


def _get_received_barcode_conflict(request, barcode):
	for lookup_barcode in _locator_lookup_values(request, barcode):
		sample = Sample.objects.using(get_dropdown_db_alias(request)).filter(barcode=lookup_barcode).first()
		if sample:
			return sample
	return None


def _apply_received_sample_to_post(request, post_data):
	sample = _get_received_barcode_conflict(request, post_data.get('barcode'))
	if sample is None:
		return None

	post_data['id'] = str(sample.pk)
	post_data['barcode'] = sample.barcode or post_data.get('barcode')
	post_data['date_received'] = sample.date_received.strftime('%Y-%m-%d') if sample.date_received else ''
	if sample.envelope_id:
		post_data['envelope_number'] = sample.envelope.envelope_number
	if sample.locator_position:
		post_data['locator_position'] = sample.locator_position
	if sample.sample_type:
		post_data['sample_type'] = sample.sample_type
	return sample


def get_facilities_qs(request):
	return Facility.objects.using(get_dropdown_db_alias(request)).values('id', 'facility')


def get_regimens_qs(request):
	return Appendix.objects.using(get_dropdown_db_alias(request)).filter(appendix_category=3)


def bind_past_regimens_formset(formset, db_alias):
	for form in formset.forms:
		if 'regimen' in form.fields:
			form.fields['regimen'].queryset = Appendix.objects.using(db_alias).filter(appendix_category_id=3)
	return formset


def get_program_label(program_code):
	theme = programs.PROGRAM_THEMES.get(str(program_code or ''), {})
	return theme.get('label', 'Unknown program')


def get_program_mismatch_message(request, actual_program_code, item_label='sample'):
	active_program_code = get_session_program_code(request)
	if not active_program_code or not actual_program_code:
		return ''
	if int(active_program_code) == int(actual_program_code):
		return ''
	return 'This %s belongs to %s, but your active program is %s. Switch program to continue.' % (
		item_label,
		get_program_label(actual_program_code),
		get_program_label(active_program_code),
	)


def get_sample_program_code(sample):
	if sample and getattr(sample, 'program_code', None):
		return int(sample.program_code)
	if sample and sample.envelope_id and sample.envelope and sample.envelope.program_code:
		return int(sample.envelope.program_code)
	return None


def lock_envelope_to_session_program(request, envelope_id):
	active_program_code = get_session_program_code(request)
	if not envelope_id or not active_program_code:
		return ''
	envelope = Envelope.objects.filter(pk=envelope_id).first()
	if envelope is None:
		return ''
	if envelope.program_code:
		return get_program_mismatch_message(request, envelope.program_code, 'envelope')
	update_envelope_program_code(envelope_id, active_program_code)
	return ''

@permission_required('samples.add_sample', login_url='/login/')
@transaction.atomic
def create(request):
	facilities = get_facilities_qs(request)
	saved_sample = request.GET.get('saved_sample')
	page_type = request.GET.get('page_type')
	PastRegimensFormSet = modelformset_factory(PastRegimens, PastRegimensForm, extra=5)
	treatment_indication_options = utils.TREATMENT_INFO_OPTIONS
	treatment_indication_selected_options = ''
	selected_treatment_ids = ''

	if request.method == 'POST':
		return handle_post_request(request, facilities, PastRegimensFormSet,treatment_indication_options,treatment_indication_selected_options,selected_treatment_ids)
	else:
		return handle_get_request(request, facilities, saved_sample, page_type, PastRegimensFormSet,treatment_indication_options,treatment_indication_selected_options,selected_treatment_ids)

def handle_post_request(request, facilities, PastRegimensFormSet,treatment_indication_options,treatment_indication_selected_options,selected_treatment_ids):
    pst = request.POST.copy()
    is_hiv_program = vl_services.is_hiv_program(request)
    received_sample = None if is_hiv_program else _apply_received_sample_to_post(request, pst)
    if sample_utils.is_hep_program_code(programs.get_active_program_code(request)):
        pst['sample_type'] = 'P'
    db_alias = get_dropdown_db_alias(request)
    patient_form = PatientForm(pst)
    envelope_form = EnvelopeForm(pst)
    preliminary_findings_form = PreliminaryFindingsForm(pst)
    sample_id = pst.get('id')
    sample_instance = None
    page_type = pst.get('page_type')
    if sample_id:
        sample_instance = Sample.objects.filter(pk=sample_id).first()
        sample_form = SampleForm(pst, instance=sample_instance, db_alias=db_alias)
    else:
        sample_form = SampleForm(pst, db_alias=db_alias)
    drug_resistance_form = DrugResistanceRequestForm(pst)
    past_regimens_formset = bind_past_regimens_formset(PastRegimensFormSet(pst), db_alias)

    if not is_hiv_program and received_sample is None and not sample_id:
        sample_form.is_valid()
        sample_form.add_error('barcode', 'Sorry dear! this sample has not yet been received')
        return render_create_page(request, facilities, envelope_form, patient_form, preliminary_findings_form,sample_form, drug_resistance_form, past_regimens_formset, page_type)

    if SampleService.validate_forms(patient_form, preliminary_findings_form,envelope_form, sample_form, drug_resistance_form, past_regimens_formset, pst):
        if is_hiv_program:
            try:
                save_result = vl_services.save_sample_form(pst, request.user)
                next_barcode = save_result.get('next_barcode')
                if request.POST.get('from_page') == 'verify':
                    return redirect("/samples/verify_list/?verified=0")
                elif request.POST.get('results_qc_id'):
                    return redirect("/results/dr_results/")
                elif request.POST.get('from_page') == 'approvals':
                    return redirect("/samples/search/?search_val=%s&search_env=1&approvals=1" % pst.get('envelope_number'))
                elif next_barcode:
                    return redirect('/samples/create?barcode=%s&page_type=%s' % (next_barcode, pst.get('page_type')))
                return redirect('/samples/create?page_type=%s' % pst.get('page_type'))
            except Exception as e:
                sample_form.add_error('barcode', str(e))
                return render_create_page(request, facilities, envelope_form, patient_form, preliminary_findings_form,sample_form, drug_resistance_form, past_regimens_formset, page_type)

        sample = Sample.objects.filter(pk=pst.get('id')).first()
        #response_data = save_form_using_external_api(pst,request.user.id,sample)
        #status = response_data.get("status")
        #if int(status) == 200:
        #	next_barcode = sample_utils.get_next_barcode(sample.barcode,sample.sample_type)
        #	return redirect('/samples/create?saved_sample=%s&barcode=%s&page_type=%s' % (sample.pk,next_barcode,pst.get('page_type')))
        #else:
        #	return HttpResponse('bikyagaanye')
        try:
            patient = SampleService.create_patient(patient_form, pst, request.user)
            preliminary_findings = SampleService.create_preliminary_finidings(preliminary_findings_form,patient, pst, request.user)
            sample = SampleService.update_sample(sample_form, pst, patient, request.user)
            SampleService.create_drug_resistance(drug_resistance_form, pst, past_regimens_formset, sample)
            next_barcode = sample_utils.get_next_barcode(sample.barcode,sample.sample_type)

            if request.POST.get('from_page') == 'verify':
                return redirect("/samples/verify_list/?verified=0")
            elif request.POST.get('results_qc_id'):
                return redirect("/results/dr_results/")
            elif request.POST.get('from_page') == 'approvals':
                return redirect("/samples/search/?search_val=%s&search_env=1&approvals=1" %sample.envelope.envelope_number)
            elif next_barcode:
                return redirect('/samples/create?saved_sample=%s&barcode=%s&page_type=%s' % (sample.pk,next_barcode,pst.get('page_type')))
            else:
                return redirect('/samples/create?saved_sample=%s&page_type=%s' % (sample.pk,pst.get('page_type')))
        except Exception as e:
            print(e)
            return HttpResponse(e)
            sample_form.add_error('barcode', 'An error occurred while saving the sample. Please try again. Check if reception entered art number')
            return render_create_page(request, facilities, envelope_form, patient_form, preliminary_findings_form,sample_form, drug_resistance_form, past_regimens_formset, page_type)
    else:
        sample_form.add_error('form_number', 'Saving failed due to validation errors')
        return render_create_page(request, facilities, envelope_form, patient_form, preliminary_findings_form,sample_form, drug_resistance_form, past_regimens_formset, page_type)

def save_form_using_external_api(pst,user_id,sample):
	form_data = pst.dict()
	form_data["created_by_id"]=user_id
	form_data["data_entered_by_id"]=user_id
	sanitized_art_no = utils.removeSpecialCharactersFromString(pst.get('hep_number'))
	unique_id = "%s-A-%s" %(pst.get('facility'), sanitized_art_no)
	form_data["sanitized_hep_number"]=sanitized_art_no
	form_data["unique_id"]=unique_id
	needs_verification = sample_utils.is_rec_and_entery_data_mataching(sample,pst.get('hep_number'),pst.get('facility'))
	sample.required_verification = needs_verification
	if needs_verification == 1:
		verified = 0
		required_verification = 1
	else:
		verified = 1
		required_verification = 0
	form_data["verified"] = verified
	form_data["required_verification"] = required_verification

	external_api_url = "http://localhost:8000/api/save_vl_form/"

	headers = {
		"User-Agent": "Django-App",
		"Content-Type": "application/json"
	}
	try:
		# Make the POST request
		response = requests.post(external_api_url, json=form_data, headers=headers,timeout=10,proxies={"http": None, "https": None})
		##response.raise_for_status()  # Raise an error for HTTP errors
		# Convert response to JSON
		response_data = response.json()
		# Extract the ID
		#sample_id = response_data.get("id")  # Assuming the API returns {"id": 123, "message": "Success"}
		return response_data
		#if sample_id:
		#	response_json = {"message": "User created successfully", "id": sample_id,"status":200}
		#else:
		#	response_json = {"error": "ID not found in response", "details": response_data,"status":400}
	except requests.Timeout:
		response_json = {"error": "Request timed out", "status":408}
		return response_json
	#except requests.RequestException as e:
	#	response_json = {"error": "API request failed", "details": str(e), "status":500}

	#print("Response Data:", response_json)
	#return JsonResponse(response_json, status=200 if "id" in response_json else 500)


def handle_get_request(request, facilities, saved_sample, page_type, PastRegimensFormSet,treatment_indication_options,treatment_indication_selected_options,selected_treatment_ids):
    barcode = ''
    db_alias = get_dropdown_db_alias(request)
    if request.GET.get('barcode'):
        barcode = request.GET.get('barcode')

    envelope_form = EnvelopeForm(initial={'envelope_number': sample_utils.initial_env_number()})
    patient_form = PatientForm
    preliminary_findings_form = PreliminaryFindingsForm
    sample_form = SampleForm(initial={'barcode': barcode,'locator_category': 'V', 'date_collected': datetime.now().strftime("%d/%m/%Y")}, db_alias=db_alias)
    drug_resistance_form = DrugResistanceRequestForm
    past_regimens_formset = bind_past_regimens_formset(PastRegimensFormSet(queryset=PastRegimens.objects.none()), db_alias)
    return render_create_page(request, facilities, envelope_form, patient_form,preliminary_findings_form, sample_form, drug_resistance_form, past_regimens_formset, page_type,treatment_indication_options,treatment_indication_selected_options,selected_treatment_ids)

def render_create_page(request, facilities, envelope_form, patient_form, preliminary_findings_form,sample_form, drug_resistance_form, past_regimens_formset, page_type='',treatment_indication_options=None,treatment_indication_selected_options=None,selected_treatment_ids=None):
    pending_entry = PendingEntryQueue.objects.all()
    sample = ''
    saved_sample = request.GET.get('saved_sample')
    if saved_sample:
        sample = Sample.objects.filter(pk=saved_sample).first()
    context = {
        'envelope_form': envelope_form,
        'patient_form': patient_form,
        'sample_form': sample_form,
        'drug_resistance_form': drug_resistance_form,
        'past_regimens_formset': past_regimens_formset,
        'regimens': get_regimens_qs(request),
        'facilities': facilities,
        'null_dob': None,
		'null_treatment_initiation_date':None,
		'facilities':facilities,
		'page_type':page_type,
		'sample':sample,
		'pending_entry':pending_entry,
		'pending_entry_count':len(pending_entry),
		'min_no_envelopes_pending':settings.MIN_NO_ENVELOPES_PENDING,
		'treatment_indication_options': utils.TREATMENT_INFO_OPTIONS,
		'preliminary_findings_form' : preliminary_findings_form,
    }
    return render(request, 'samples/create.html', context)

@permission_required('samples.add_sample', login_url='/login/')

def fix_verifications(request):
	env_no = request.GET.get('env_number')
	envelope = Envelope.objects.filter(envelope_number = env_no)
	samples = Sample.objects.filter(envelope = envelope)
	for sample in samples:
		existing_ver = Verification.objects.filter(sample= sample).first()
		if not existing_ver:
			ver = Verification()
			ver.accepted = 1
			ver.verified_by_id = 1
			ver.pat_edits = 0
			ver.sample_edits =0
			ver.created_at = sample.created_at
			ver.updated_at = sample.created_at
			ver.sample = sample
			ver.save()

			sample.verified = 1
			sample.save()
		else:
			#mark sample verified
			if sample.locator_category == 'V':
				existing_ver.accepted = 1
			else:
				existing_ver.accepted = 0
			existing_ver.save()
			sample.verified = 1
			sample.save()
	return HttpResponse('done')


def receive_api(request):

	return HttpResponse(request.POST.get('facilityid'))


@transaction.atomic
def receive(request):
	if vl_services.is_hiv_program(request):
		if request.method == 'POST':
			try:
				sample = vl_services.receive_sample(request.POST, request.user)
				return redirect('/samples/receive?saved_sample=%s&env_id=%s&current_tr_code=%s' % (
					sample.id,
					sample.envelope_id,
					request.POST.get('code', ''),
				))
			except Exception as e:
				form = SampleReceptionForm(request.POST)
				form.add_error('barcode', str(e))
				context = {
					'sample_reception_form': form,
					'tr_code_id': request.POST.get('tracking_code_id'),
					'tracking_code_id': request.POST.get('tracking_code_id'),
					'env_id': request.POST.get('envelope_id'),
					'current_tr_code': request.POST.get('current_tr_code'),
					'page_type': request.POST.get('page_type', ''),
					'reception_id': '',
					'locator_category': request.POST.get('locator_category', ''),
					'reception_hep_number': request.POST.get('reception_hep_number', ''),
					'facility_reference': request.POST.get('facility_reference', ''),
					'form_data': request.POST,
				}
				return render(request, 'samples/receive.html', context)
		tracking_code, tr_code_id, current_tr_code = _get_tracking_context_from_request(request)
		form = SampleReceptionForm(initial=_sample_reception_initial(tracking_code), db_alias=get_dropdown_db_alias(request))
		return render(request, 'samples/receive.html', {
			'sample_reception_form': form,
			'tr_code_id': tr_code_id,
			'tracking_code_id': tr_code_id,
			'env_id': request.GET.get('env_id'),
			'current_tr_code': current_tr_code,
			'page_type': request.GET.get('page_type'),
			'reception_id':'',
			'locator_category':'',
			'reception_hep_number': '',
			'facility_reference': '',
			'form_data':'',
		})

	saved_sample = request.GET.get('saved_sample')
	tracking_code, tr_code_id, current_tr_code = _get_tracking_context_from_request(request)
	page_type = request.GET.get('page_type')
	env_id = request.GET.get('env_id')

	if request.method == 'POST':
		form_data = request.POST.copy()
		pst = form_data
		current_tr_code = pst.get('current_tr_code') or current_tr_code or ''
		accepted = pst.get('locator_category')
		rejection_reason_id = pst.get('rejection_reason_id')
		page_type = pst.get('page_type')
		if(accepted=='R' and not rejection_reason_id):
			return HttpResponse("rejection reason required for rejected samples")
		locator_error = ''
		try:
			parsed_locator = sample_utils.parse_locator_id(pst.get('barcode'), programs.get_active_program_code(request))
		except ValueError as e:
			parsed_locator = None
			locator_error = str(e)
		if parsed_locator:
			pst['barcode'] = parsed_locator.get('barcode')
			pst['envelope_number'] = parsed_locator.get('envelope_number')
			pst['locator_position'] = parsed_locator.get('locator_position')
			pst['sample_type'] = parsed_locator.get('sample_type')
		if sample_utils.is_hep_program_code(programs.get_active_program_code(request)):
			pst['sample_type'] = 'P'

		sample_reception_form = SampleReceptionForm(pst)
		if locator_error:
			sample_reception_form.add_error('barcode', locator_error)
		#valid_sample = sample_reception_form.is_valid()
		#return HttpResponse(valid_sample)
		#if valid_sample:
		tr_code_id = pst.get('tracking_code_id')
		envelope = Envelope.objects.filter(envelope_number=pst.get('envelope_number')).first()
		env_id = envelope.id if envelope else pst.get('envelope_id')
		if env_id:
			pst['envelope_id'] = env_id
		session_program_code = get_session_program_code(request)
		if env_id is None:
			sample_reception_form.add_error('barcode', 'Envelope was not found, did you accession it?')
		else:
			mismatch_message = lock_envelope_to_session_program(request, env_id)
			if mismatch_message:
				sample_reception_form.add_error('barcode', mismatch_message)
		conflict_sample = _get_received_barcode_conflict(request, pst.get('barcode'))
		if conflict_sample:
			sample_reception_form.add_error('barcode', DUPLICATE_BARCODE_MESSAGE)
		if not (pst.get('reception_hep_number') or '').strip():
			sample_reception_form.add_error('barcode', 'Hep number is required.')
		if sample_reception_form.is_valid():
			date_collected = sample_reception_form.cleaned_data.get('date_collected')
			db_alias = get_dropdown_db_alias(request)
			facility_ref = pst.get('facility_reference')
			facility_reference = None if facility_ref == '' else facility_ref
			s = None
			if facility_reference is not None:
				s = _find_existing_sample_for_reception(
					facility_reference,
					pst.get('facility'),
					db_alias=db_alias,
				)
			tracking_code = _resolve_tracking_code_for_sample(
				s,
				tr_code_id,
				pst.get('code'),
				request.user.id,
				pst.get('facility'),
				db_alias=db_alias,
			)
			if tracking_code is None:
				sample_reception_form.add_error('barcode', 'Tracking code is required.')
			elif _should_block_tracking_code_facility_mismatch(s, tracking_code, pst.get('facility')):
				sample_reception_form.add_error('facility', TRACKING_CODE_FACILITY_MISMATCH_MESSAGE)
			if sample_reception_form.errors:
				context = {
					'sample_reception_form': sample_reception_form,
					'tr_code_id': getattr(tracking_code, 'id', None) or tr_code_id,
					'tracking_code_id': getattr(tracking_code, 'id', None) or tr_code_id,
					'env_id': env_id,
					'current_tr_code': pst.get('code') or current_tr_code,
					'page_type': page_type,
					'reception_id': '',
					'locator_category': pst.get('locator_category'),
					'reception_hep_number': pst.get('reception_hep_number', ''),
					'facility_reference': pst.get('facility_reference', ''),
					'form_data': pst,
				}
				return render(request, 'samples/receive.html', context)
			tr_code_id = tracking_code.id
			current_tr_code = tracking_code.code
			#get the facility_patient
			#save the sample and its first identifier

			sanitized_art_no = utils.removeSpecialCharactersFromString(pst.get('reception_hep_number'))
			unique_id = "%s-A-%s" %(pst.get('facility'), sanitized_art_no)
			#return HttpResponse(unique_id)
			facility_pat = FacilityPatient.objects.filter(unique_id=unique_id).first()
			fac_pat = facility_pat if facility_pat else None
			conflict_sample = _get_facility_reference_conflict(
				facility_reference,
				pst.get('facility'),
				db_alias=db_alias,
			)
			if conflict_sample:
				sample_reception_form.add_error('facility_reference', DUPLICATE_FACILITY_REFERENCE_MESSAGE)
				form_data = pst
				context = {
					'sample_reception_form': sample_reception_form,
					'tr_code_id': tr_code_id,
					'tracking_code_id': tr_code_id,
					'env_id':env_id,
					'current_tr_code':current_tr_code,
					'page_type': page_type,
					'reception_id':'',
					'locator_category': pst.get('locator_category'),
					'reception_hep_number': pst.get('reception_hep_number', ''),
					'facility_reference': pst.get('facility_reference', ''),
					'form_data':form_data
				}
				return render(request, 'samples/receive.html', context)
			form_number = pst.get('barcode') if facility_ref == '' else facility_ref

			if pst.get('locator_category') == 'R':
				stage = 7
			else:
				stage = 0
			if s:
				if _sample_patient_facility_mismatch(s, tracking_code, db_alias=db_alias):
					sample_reception_form.add_error('facility_reference', TRACKING_CODE_SAMPLE_FACILITY_MISMATCH_MESSAGE)
					context = {
						'sample_reception_form': sample_reception_form,
						'tr_code_id': tr_code_id,
						'tracking_code_id': tr_code_id,
						'env_id': env_id,
						'current_tr_code': current_tr_code,
						'page_type': page_type,
						'reception_id': '',
						'locator_category': pst.get('locator_category'),
						'reception_hep_number': pst.get('reception_hep_number', ''),
						'facility_reference': pst.get('facility_reference', ''),
						'form_data': pst
					}
					return render(request, 'samples/receive.html', context)
				if not s.tracking_code_id:
					s.facility_id = pst.get('facility')
					s.facility_reference = facility_reference
					s.form_number = form_number
					s.reception_hep_number = pst.get('reception_hep_number')
					s.facility_patient = fac_pat
				s.tracking_code_id = tr_code_id
				s.locator_category = pst.get('locator_category')
				s.envelope_id = env_id
				s.verified = 1
				s.stage = 0
				s.locator_position=pst.get('locator_position')
				s.barcode=pst.get('barcode')
				s.date_collected = date_collected
				_set_sample_type_from_request_or_envelope(s, request, env_id)
				#s.date_received = request.POST.get('date_received')
				s.date_received = datetime.now()
				s.received_by = request.user
				if session_program_code:
					s.program_code = session_program_code
				s.save()
			else:
				s = Sample(tracking_code_id = tr_code_id,locator_category = pst.get('locator_category'),locator_position=pst.get('locator_position'),
					barcode=pst.get('barcode'),created_by =request.user,stage=stage,
					form_number=form_number,facility_id = pst.get('facility'),
					sample_type=pst.get('sample_type') or _posted_sample_type(request),date_collected=date_collected,date_received=datetime.now(), envelope_id = env_id,received_by = request.user,reception_hep_number=pst.get('reception_hep_number'),facility_reference=facility_reference,facility_patient = fac_pat,verified=0)
				if session_program_code:
					s.program_code = session_program_code
				s.save()

			update_envelope_program_code(env_id, get_session_program_code(request))
			sample_utils.update_envelope_status(s,'received')
			#save the corresponding verification object
			v = Verification()
			v.pat_edits = 0
			v.sample_edits = 0
			v.sample = s
			accepted = pst.get('locator_category')
			v.accepted = True if accepted == 'V' else False
			if(accepted=='R'):
				#save the patient object
				patient = Patient()
				patient.facility_id = pst.get('facility')
				patient.hep_number=pst.get('reception_hep_number')
				patient.created_by_id= request.user.id
				patient.save()
				v.rejection_reason_id = pst.get('rejection_reason_id')
				if not v.rejection_reason_id:
					return HttpResponse("rejection reason required for rejected samples")
				#release the rejection by default
				sample_utils.release_rejected_sample(s, request.user.id)
				s.verified = 1
				s.is_data_entered = 1
				s.patient = patient
				s.save()
			else:
				v.rejection_reason_id = None

			v.verified_by = request.user
			v.save()

			# if the sample has been tested, update it
			ws = WorksheetSample.objects.filter(instrument_id=s.barcode).first()
			if ws and ws.sample_id is None:
				ws.sample = s
				ws.save()
			d_reception = s.envelope.created_at.strftime('%Y-%m-%d')
			return redirect('/samples/receive?saved_sample=%s&tr_code_id=%s&env_id=%s&current_tr_code=%s&date_received=%s&page_type=%s' %(s.pk, tr_code_id,env_id,pst.get('code'),d_reception,page_type))
	else:
		form_data = ''
		d = datetime.now()
		sample_reception_form = SampleReceptionForm(initial=_sample_reception_initial(tracking_code), db_alias=get_dropdown_db_alias(request))

	context = {
		'sample_reception_form': sample_reception_form,
		'tr_code_id': tr_code_id,
		'tracking_code_id': tr_code_id,
		'env_id':env_id,
		'current_tr_code':current_tr_code,
		'page_type': page_type,
		'reception_id':'',
		'locator_category':'',
		'reception_hep_number': '',
		'facility_reference': '',
		'form_data':form_data
	}

	if saved_sample:
		sample = Sample.objects.filter(pk=saved_sample).first()
		context.update({'sample':sample,'tr_code_id':tr_code_id,'tracking_code_id':tr_code_id,'env_id':env_id,})

	return render(request, 'samples/receive.html', context)

@transaction.atomic
def reject_sample(request):
	rejection_reason_id = request.POST.get('rejection_reason_id')

	sample_identifier_id = request.POST.get('sample_identifier_id')
	worksheet_id = request.POST.get('worksheet_id')
	if sample_identifier_id:
		worksheet_id = request.POST.get('worksheet_id')
		ws = WorksheetSample.objects.get(pk=request.POST.get('ws_id'))
		ws.stage = 7
		ws.save()

		s = Sample.objects.get(pk=sample_identifier_id)
		s.rejected_by_id = request.user.id
		s.stage = 7
		s.rejected_at = datetime.now().date()
		s.save()


	if rejection_reason_id and s.id:
		v = Verification.objects.filter(sample_id=s.id).first()
		if not v:
			v = Verification()
			v.sample_id = s.id
		v.accepted = False
		v.rejection_reason_id = request.POST.get('rejection_reason_id')
		if not v.rejection_reason_id:
			return HttpResponse("rejection reason required for rejected samples")
		v.verified_by = request.user
		v.save()
		v.sample.locator_category = 'R'
		v.sample.save()
	return redirect("/worksheets/show/%d" %int(worksheet_id))

def get_envelope_details(request):
	envelope_number = request.GET.get('envelope_number')
	if vl_services.is_hiv_program(request):
		return HttpResponse(json.dumps(vl_services.get_envelope_details(envelope_number)))
	ret = []
	envelope = Envelope.objects.filter(id__gte=settings.ENVELOPE_SAMPLES_CUT_OFF,envelope_number=envelope_number).first()
	if envelope is None:
		envelope = Envelope.objects.filter(envelope_number=envelope_number).first()
	env_status_update = request.GET.get('env_status_update')
	env_id = ''
	date_received = ''
	err_msg = ''
	program_mismatch = False
	if envelope:
		err_msg = get_program_mismatch_message(request, envelope.program_code, 'envelope')
		if err_msg:
			program_mismatch = True
		else:
			env_id = envelope.id
			update_env_status(envelope,env_status_update)
			date_received = envelope.created_at.strftime('%Y-%m-%d')
	else:
		err_msg = ''

	ret = {
		'envelope_id': env_id,
		'date_received':date_received,
		'program_mismatch': program_mismatch,
		'err_msg': err_msg,
		'program_code': envelope.program_code if envelope else ''
		}
	return HttpResponse(json.dumps(ret))
def get_envelope_status_for_lab(request):
	envelope_number = request.GET.get('envelope_number')

	envelope = Envelope.objects.filter(id__gte=settings.ENVELOPE_SAMPLES_CUT_OFF,envelope_number=envelope_number).first()
	if envelope is None:
		#envelope was not received
		return HttpResponse(1)
	else:
		s_identifier = SampleIdentifier.objects.filter(env=envelope).first()
		if s_identifier is None:
			return HttpResponse(2)
		else:
			return HttpResponse(3)


def update_env_status(envelope,update_env_status):
	if update_env_status == 'has_result':
		envelope.has_result = 1
	if update_env_status == 'received':
		env_queue = PendingReceptionQueue.objects.filter(envelope = envelope).first()
		if env_queue:
			env_queue.delete()
		#update the data entry que - if has result
		if envelope.has_result and envelope.is_received == 0:
			does_exist = PendingEntryQueue.objects.filter(envelope = envelope).first()
			if does_exist is None:
				ent_queue = PendingEntryQueue()
				ent_queue.envelope = envelope
				ent_queue.envelope_number = envelope.envelope_number
				ent_queue.status = 1
				ent_queue.save()

	envelope.save()
	return True

def get_tracking_code_details(request):
	code = request.GET.get('code')
	facility_id = request.GET.get('facility_id')
	lookup_only = request.GET.get('lookup_only') == '1'
	if vl_services.is_hiv_program(request):
		if lookup_only:
			tr = vl_services.VLTrackingCode.objects.using('vl_lims').filter(code=(code or '').strip()).first()
		else:
			tr = vl_services.get_or_create_tracking_code(code, request.user, facility_id)
		if tr is None or _is_placeholder_tracking_code_value(getattr(tr, 'code', '')):
			return HttpResponse(json.dumps({
				'exists': 0,
				'tracking_code_id': '',
				'facility_id': '',
				'facility_name': '',
				'district': '',
				'hub': '',
				'number_of_samples': '',
				'package_samples': [],
				'facility_mismatch': 0,
				'err_msg': '',
			}))
		facility = Facility.objects.select_related('district', 'hub').filter(pk=tr.facility_id).first() if tr.facility_id else None
		district = getattr(facility, 'district', None)
		hub = getattr(facility, 'hub', None)
		facility_mismatch = _get_tracking_code_facility_mismatch(tr, facility_id)
		return HttpResponse(json.dumps({
			'exists': 1,
			'tracking_code_id': tr.id,
			'facility_id': tr.facility_id or '',
			'facility_name': getattr(facility, 'facility', '') or '',
			'district': getattr(district, 'district', '') or '',
			'hub': getattr(hub, 'hub', '') or '',
			'number_of_samples': tr.no_samples or '',
			'package_samples': [],
			'facility_mismatch': 1 if facility_mismatch else 0,
			'err_msg': TRACKING_CODE_FACILITY_MISMATCH_MESSAGE if facility_mismatch else '',
		}))
	db_alias = get_dropdown_db_alias(request)
	if lookup_only:
		tr = TrackingCode.objects.using(db_alias).select_related('facility__district', 'facility__hub').filter(code=(code or '').strip()).first()
	else:
		tr = _get_or_create_tracking_code(code, request.user.id, facility_id, db_alias=db_alias)
	if tr is None or _is_placeholder_tracking_code_value(getattr(tr, 'code', '')):
		return HttpResponse(json.dumps({
			'exists': 0,
			'tracking_code_id': '',
			'facility_id': '',
			'facility_name': '',
			'district': '',
			'hub': '',
			'number_of_samples': '',
			'package_samples': [],
			'facility_mismatch': 0,
			'err_msg': '',
		}))
	facility_mismatch = _get_tracking_code_facility_mismatch(tr, facility_id)
	facility = getattr(tr, 'facility', None)
	district = getattr(facility, 'district', None)
	hub = getattr(facility, 'hub', None)
	package_samples = _tracking_code_package_samples(tr, db_alias=db_alias)
	ret = {
		'exists': 1,
		'tracking_code_id': tr.id,
		'facility_id': getattr(facility, 'id', '') or '',
		'facility_name': getattr(facility, 'facility', '') or '',
		'district': getattr(district, 'district', '') or '',
		'hub': getattr(hub, 'hub', '') or '',
		'number_of_samples': len(package_samples) if package_samples else '',
		'package_samples': package_samples,
		'facility_mismatch': 1 if facility_mismatch else 0,
		'err_msg': TRACKING_CODE_FACILITY_MISMATCH_MESSAGE if facility_mismatch else '',
	}
	return HttpResponse(json.dumps(ret))


def _render_receive_batch_error(request, sample_reception_form, error, tr_code_id='', env_id='', current_tr_code=''):
	pending_reception = PendingReceptionQueue.objects.all()
	envelope_samples = []
	if env_id:
		envelope = Envelope.objects.filter(pk=env_id).first()
		envelope_samples = envelope.sample_set.all().order_by('locator_position') if envelope else []
	tracking_code = _get_existing_tracking_code(request, tr_code_id, current_tr_code)
	context = {
		'sample_reception_form': sample_reception_form,
		'tr_code_id': getattr(tracking_code, 'id', None) or tr_code_id,
		'env_id': env_id,
		'current_tr_code': current_tr_code or getattr(tracking_code, 'code', ''),
		'reception_id': '',
		'pending_reception': pending_reception,
		'pending_reception_count': pending_reception.count(),
		'min_no_envelopes_pending': settings.MIN_NO_ENVELOPES_PENDING,
		'envelope_samples': envelope_samples,
		'last_received_barcode': request.POST.get('last_barcode', ''),
		'batch_error': error,
	}
	context.update(_receive_batch_tracking_context(tracking_code))
	return render(request, 'samples/receive_bactch.html', context)


def _batch_receive_error(request, sample_reception_form, error, tr_code_id='', env_id='', current_tr_code=''):
	return _render_receive_batch_error(request, sample_reception_form, error, tr_code_id, env_id, current_tr_code)


def _batch_receive_rows(request):
	locator_ids = [(locator_id or '').strip() for locator_id in request.POST.getlist('locator_id')]
	hep_numbers = [(hep_number or '').strip() for hep_number in request.POST.getlist('hep_number')]
	rows = []
	for index, locator_id in enumerate(locator_ids):
		if locator_id == '':
			continue
		hep_number = hep_numbers[index] if index < len(hep_numbers) else ''
		rows.append({
			'locator_id': locator_id,
			'hep_number': hep_number,
		})
	return rows


def _normalise_batch_row(request, row, envelope):
	try:
		parsed_locator = sample_utils.parse_locator_id(row.get('locator_id'), programs.get_active_program_code(request))
	except ValueError as e:
		raise ValidationError(str(e))
	if not parsed_locator:
		raise ValidationError('Invalid locator ID: {0}'.format(row.get('locator_id')))
	if envelope and parsed_locator.get('envelope_number') != envelope.envelope_number:
		raise ValidationError('Locator ID {0} is not in envelope {1}.'.format(row.get('locator_id'), envelope.envelope_number))
	row['barcode'] = parsed_locator.get('barcode')
	row['locator_position'] = parsed_locator.get('locator_position')
	row['sample_type'] = parsed_locator.get('sample_type') or (envelope.sample_type if envelope else None)
	return row


def _save_receive_batch_row(request, row, tracking_code_id, env_id, facility_id, date_collected, session_program_code):
	hep_number = row.get('hep_number')
	sanitized_art_no = utils.removeSpecialCharactersFromString(hep_number)
	unique_id = "%s-A-%s" % (facility_id, sanitized_art_no)
	facility_pat = FacilityPatient.objects.filter(unique_id=unique_id).first()
	sample = Sample(
		tracking_code_id=tracking_code_id,
		locator_category='V',
		locator_position=row.get('locator_position'),
		barcode=row.get('barcode'),
		created_by=request.user,
		date_received=datetime.now(),
		form_number=row.get('barcode'),
		reception_hep_number=hep_number,
		facility_id=facility_id,
		sample_type=row.get('sample_type') or _posted_sample_type(request),
		date_collected=date_collected,
		stage=0,
		is_data_entered=0,
		patient_id=None,
		received_by=request.user,
		envelope_id=env_id,
		facility_patient=facility_pat,
		verified=0,
		facility_reference=None,
	)
	_set_sample_type_from_request_or_envelope(sample, request, env_id)
	if session_program_code:
		sample.program_code = session_program_code
	sample.save()
	sample_utils.update_envelope_status(sample, 'received')
	sample_utils.save_verification_details(sample, request)
	sample_utils.update_worksheet_sample(sample)
	sample_utils.update_result_models(sample)
	return sample


def _handle_receive_batch_submit(request):
	pst = request.POST
	sample_reception_form = SampleReceptionForm(pst, db_alias=get_dropdown_db_alias(request))
	tr_code_id = pst.get('tracking_code_id')
	current_tr_code = pst.get('current_tr_code') or pst.get('code') or ''
	facility_id = pst.get('facility')
	env_id = sample_utils.resolve_posted_envelope_id(request)
	rows = _batch_receive_rows(request)

	try:
		date_collected = posted_date(pst, 'date_collected')
	except ValidationError as e:
		return _batch_receive_error(request, sample_reception_form, str(e), tr_code_id, env_id, current_tr_code)

	if not pst.get('code') and not tr_code_id:
		return _batch_receive_error(request, sample_reception_form, 'Tracking code is required.', tr_code_id, env_id, current_tr_code)
	if not env_id:
		return _batch_receive_error(request, sample_reception_form, 'Envelope was not found, did you accession it?', tr_code_id, env_id, current_tr_code)
	if not facility_id:
		return _batch_receive_error(request, sample_reception_form, 'Facility is required.', tr_code_id, env_id, current_tr_code)
	if not rows:
		return _batch_receive_error(request, sample_reception_form, 'No generated samples were submitted.', tr_code_id, env_id, current_tr_code)

	session_program_code = get_session_program_code(request)
	mismatch_message = lock_envelope_to_session_program(request, env_id)
	if mismatch_message:
		return _batch_receive_error(request, sample_reception_form, mismatch_message, tr_code_id, env_id, current_tr_code)

	envelope = Envelope.objects.filter(pk=env_id).first()
	if envelope is None:
		return _batch_receive_error(request, sample_reception_form, 'Envelope was not found, did you accession it?', tr_code_id, env_id, current_tr_code)

	try:
		rows = [_normalise_batch_row(request, row, envelope) for row in rows]
	except ValidationError as e:
		return _batch_receive_error(request, sample_reception_form, str(e), tr_code_id, env_id, current_tr_code)

	seen_barcodes = set()
	for row in rows:
		barcode = row.get('barcode')
		hep_number = row.get('hep_number')
		if not hep_number:
			return _batch_receive_error(request, sample_reception_form, 'Hep number is required for {0}.'.format(barcode), tr_code_id, env_id, current_tr_code)
		if barcode in seen_barcodes:
			return _batch_receive_error(request, sample_reception_form, 'Duplicate locator ID in this batch: {0}.'.format(barcode), tr_code_id, env_id, current_tr_code)
		seen_barcodes.add(barcode)
		if _get_received_barcode_conflict(request, barcode):
			return _batch_receive_error(request, sample_reception_form, '{0}: {1}'.format(barcode, DUPLICATE_BARCODE_MESSAGE), tr_code_id, env_id, current_tr_code)

	tracking_code = _resolve_tracking_code(tr_code_id, pst.get('code'), request.user.id, facility_id, db_alias=get_dropdown_db_alias(request))
	if tracking_code is None:
		return _batch_receive_error(request, sample_reception_form, 'Tracking code is required.', tr_code_id, env_id, current_tr_code)
	if _get_tracking_code_facility_mismatch(tracking_code, facility_id):
		return _batch_receive_error(request, sample_reception_form, TRACKING_CODE_FACILITY_MISMATCH_MESSAGE, tracking_code.id, env_id, current_tr_code)

	saved_samples = [
		_save_receive_batch_row(request, row, tracking_code.id, env_id, facility_id, date_collected, session_program_code)
		for row in rows
	]
	update_envelope_program_code(env_id, get_session_program_code(request))
	last_sample = saved_samples[-1]
	params = urlencode({
		'saved_sample': last_sample.pk,
		'env_id': env_id,
		'tr_code_id': tracking_code.id,
		'current_tr_code': pst.get('code') or current_tr_code,
		'last_barcode': last_sample.barcode,
	})
	return redirect('/samples/receive_batch/?{0}'.format(params))


@transaction.atomic
def receive_batch(request,ret_to_fun = 0):
	if (request.method == 'POST' or ret_to_fun) and not vl_services.is_hiv_program(request):
		conflict_sample = _get_received_barcode_conflict(request, request.POST.get('the_barcode'))
		if conflict_sample:
			ret = {
				'saved_sample': '',
				'env_id': request.POST.get('envelope_id'),
				'tracking_code_id': request.POST.get('tracking_code_id'),
				's_barcode': request.POST.get('the_barcode', ''),
				'err_msg': DUPLICATE_BARCODE_MESSAGE,
			}
			return ret if ret_to_fun else HttpResponse(json.dumps(ret))
	if vl_services.is_hiv_program(request):
		if request.method == 'POST' or ret_to_fun:
			try:
				sample = vl_services.receive_sample(request.POST, request.user)
				ret = {
					'saved_sample': sample.id,
					'env_id': sample.envelope_id,
					'tracking_code_id': sample.tracking_code_id,
					's_barcode': sample.barcode,
					'err_msg': '',
				}
				if ret_to_fun:
					return sample
				return HttpResponse(json.dumps(ret))
			except Exception as e:
				ret = {
					'saved_sample': '',
					'env_id': request.POST.get('envelope_id'),
					'tracking_code_id': request.POST.get('tracking_code_id'),
					's_barcode': request.POST.get('the_barcode', ''),
					'err_msg': str(e),
				}
				return HttpResponse(json.dumps(ret))
		saved_sample = request.GET.get('saved_sample')
		tracking_code, tr_code_id, current_tr_code = _get_tracking_context_from_request(request)
		env_id = request.GET.get('env_id')
		sample_reception_form = SampleReceptionForm(initial=_sample_reception_initial(tracking_code), db_alias=get_dropdown_db_alias(request))
		context = {
			'sample_reception_form': sample_reception_form,
			'tr_code_id': tr_code_id,
			'env_id':env_id,
			'current_tr_code':current_tr_code,
			'reception_id':'',
			'pending_reception':[],
			'pending_reception_count':0,
			'min_no_envelopes_pending':settings.MIN_NO_ENVELOPES_PENDING,
			'envelope_samples': vl_services.get_envelope_samples(env_id),
			'last_received_barcode': request.GET.get('last_barcode', ''),
		}
		if saved_sample:
			sample = vl_services.get_adapted_sample(saved_sample)
			if sample and not env_id and sample.envelope_id:
				env_id = sample.envelope_id
			if sample and not tr_code_id and getattr(sample, 'tracking_code_id', None):
				tr_code_id = sample.tracking_code_id
			context.update({
				'sample': sample,
				'tr_code_id': tr_code_id,
				'env_id': env_id,
				'envelope_samples': vl_services.get_envelope_samples(sample.envelope_id if sample else env_id),
				'last_received_barcode': sample.barcode if sample and sample.barcode else request.GET.get('last_barcode', ''),
			})
		return render(request, 'samples/receive_bactch.html', context)

	saved_sample = request.GET.get('saved_sample')
	tracking_code, tr_code_id, current_tr_code = _get_tracking_context_from_request(request)
	env_id = request.GET.get('env_id')
	patient_id = None
	if current_tr_code is None:
		current_tr_code = ''
	if request.method == 'POST' and not ret_to_fun and _batch_receive_rows(request):
		return _handle_receive_batch_submit(request)
	if request.method == 'POST' or ret_to_fun:
		pst = request.POST
		date_collected = posted_date(request.POST, 'date_collected')
		sample_reception_form = SampleReceptionForm(pst, db_alias=get_dropdown_db_alias(request))
		tr_code_id = request.POST.get('tracking_code_id')
		env_id = sample_utils.resolve_posted_envelope_id(request)
		session_program_code = get_session_program_code(request)
		mismatch_message = lock_envelope_to_session_program(request, env_id)
		if mismatch_message:
			ret = {
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': request.POST.get('the_barcode', ''),
				'err_msg': mismatch_message,
			}
			if ret_to_fun:
				return ret
			return HttpResponse(json.dumps(ret))
		saved_id = request.POST.get('saved_id')
		sample_only = request.POST.get('sample_only')
		facility_ref = request.POST.get('facility_reference')
		facility_id = request.POST.get('facility')
		barcode = request.POST.get('the_barcode')
		hep_number = request.POST.get('reception_hep_number')
		required_message = ''
		if not env_id:
			required_message = 'Envelope was not found, did you accession it?'
		elif not barcode:
			required_message = 'Locator ID is required.'
		elif not facility_id:
			required_message = 'Facility is required.'
		elif not hep_number:
			required_message = 'Hep number is required.'
		if required_message:
			ret = {
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': barcode or '',
				'err_msg': required_message,
				'message_type': 'err',
			}
			if ret_to_fun:
				return ret
			return HttpResponse(json.dumps(ret))
		conflict_sample = _get_facility_reference_conflict(
			facility_ref,
			facility_id,
			saved_id,
			db_alias=get_dropdown_db_alias(request),
		)
		if conflict_sample:
			ret = {
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': request.POST.get('the_barcode', ''),
				'err_msg': DUPLICATE_FACILITY_REFERENCE_MESSAGE,
				'message_type': 'err',
			}
			if ret_to_fun:
				return ret
			return HttpResponse(json.dumps(ret))
		tracking_code = _resolve_tracking_code(
			tr_code_id,
			request.POST.get('code'),
			request.user.id,
			facility_id,
			db_alias=get_dropdown_db_alias(request),
		)
		if tracking_code is None:
			ret = {
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': request.POST.get('the_barcode', ''),
				'err_msg': 'Tracking code is required.',
				'message_type': 'err',
			}
			if ret_to_fun:
				return ret
			return HttpResponse(json.dumps(ret))
		if _get_tracking_code_facility_mismatch(tracking_code, facility_id):
			ret = {
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tracking_code.id,
				's_barcode': request.POST.get('the_barcode', ''),
				'err_msg': TRACKING_CODE_FACILITY_MISMATCH_MESSAGE,
				'message_type': 'err',
			}
			if ret_to_fun:
				return ret
			return HttpResponse(json.dumps(ret))
		tr_code_id = tracking_code.id
		form_number = request.POST.get('barcode') if facility_ref == '' else facility_ref
		if request.POST.get('facility') is None:
			sample_reception_form.add_error('facility','The facility is required')
			ret = {
				'saved_sample': '',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				'err_msg':'Please select the facility'
			}

		sanitized_art_no = utils.removeSpecialCharactersFromString(request.POST.get('reception_hep_number'))
		unique_id = "%s-A-%s" %(request.POST.get('facility'), sanitized_art_no)
		facility_pat = FacilityPatient.objects.filter(unique_id=unique_id).first()
		fac_pat = facility_pat if facility_pat else None
		#save the sample and its first identifier


		if saved_id:
			mg = saved_id
			s = Sample.objects.get(pk=saved_id)
			if not env_id and s.envelope_id:
				env_id = s.envelope_id
			s.tracking_code_id = tr_code_id
			s.locator_category = 'V'
			s.locator_position = request.POST.get('the_position')
			s.barcode = request.POST.get('the_barcode')
			s.reception_hep_number = request.POST.get('reception_hep_number')
			s.facility_id = request.POST.get('facility')
			_set_sample_type_from_request_or_envelope(s, request, env_id)
			s.facility_patient = fac_pat
			if session_program_code:
				s.program_code = session_program_code
			if env_id:
				s.envelope_id = env_id
			s.stage = 0
			s.date_collected = date_collected
			s.date_received = datetime.now()
			s.form_number = form_number
			s.facility_reference = facility_ref
			if sample_only:
				s.is_data_entered = 1
				s.verified = 1
			else:
				s.is_data_entered = 0
				s.verified = 0
			s.received_by = request.user
			s.save()
			update_envelope_program_code(env_id, get_session_program_code(request))
		else:
			if sample_only == '1':
				data_entered_val = 1
				verified = 1
				patient = Patient()
				patient.hep_number = request.POST.get('reception_hep_number')
				patient.facility_id = request.POST.get('facility')
				patient.created_by = request.user
				patient.save()
				patient_id = patient.id
			else:
				data_entered_val = 0
				verified = 0

			#if lab ran samples before reception, update the sample instead
			lab_sample = Sample.objects.filter(barcode=request.POST.get('the_barcode')).first()
			s = Sample(tracking_code_id = tr_code_id,locator_category = 'V',locator_position=request.POST.get('the_position'),
			barcode=request.POST.get('the_barcode'),created_by =request.user,date_received = datetime.now(),
			form_number=form_number,reception_hep_number = request.POST.get('reception_hep_number'),facility_id = request.POST.get('facility'),
			sample_type=_posted_sample_type(request),date_collected=date_collected,stage=0,is_data_entered=data_entered_val,patient_id=patient_id, received_by = request.user,envelope_id = env_id,facility_patient = fac_pat,verified=verified,facility_reference = facility_ref)
			_set_sample_type_from_request_or_envelope(s, request, env_id)
			if session_program_code:
				s.program_code = session_program_code
			#if lab_sample:
				#s.id = lab_sample.id
			s.save()

		update_envelope_program_code(env_id, get_session_program_code(request))
		sample_utils.update_envelope_status(s,'received')

		#save the corresponding verification object
		sample_utils.save_verification_details(s,request)
		sample_utils.update_worksheet_sample(s)

		# if the sample has been tested, updated it
		sample_utils.update_result_models(s)
		if ret_to_fun:
			return s
		ret = {
				'saved_sample': s.id,
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':s.barcode,
				'err_msg':''
			}

		return HttpResponse(json.dumps(ret))

	else:
		d = datetime.now()
		sample_reception_form = SampleReceptionForm(initial=_sample_reception_initial(tracking_code), db_alias=get_dropdown_db_alias(request))

	pending_reception = PendingReceptionQueue.objects.all()
	context = {
		'sample_reception_form': sample_reception_form,
		'tr_code_id': tr_code_id,
		'env_id':env_id,
		'current_tr_code':current_tr_code,
		'reception_id':'',
		'pending_reception':pending_reception,
		'pending_reception_count':pending_reception.count(),
		'min_no_envelopes_pending':settings.MIN_NO_ENVELOPES_PENDING,
		'envelope_samples': [],
		'last_received_barcode': request.GET.get('last_barcode', ''),
	}

	if saved_sample:
		sample = Sample.objects.filter(pk=saved_sample).first()
		if sample and not env_id and sample.envelope_id:
			env_id = sample.envelope_id
		if sample and not tr_code_id and sample.tracking_code_id:
			tr_code_id = sample.tracking_code_id
		if sample and not tracking_code and sample.tracking_code_id:
			tracking_code = _get_existing_tracking_code(request, sample.tracking_code_id, '')
			if tracking_code:
				tr_code_id = tracking_code.id
				current_tr_code = current_tr_code or tracking_code.code
				sample_reception_form = SampleReceptionForm(initial=_sample_reception_initial(tracking_code), db_alias=get_dropdown_db_alias(request))
		envelope_samples = sample.envelope.sample_set.all().order_by('locator_position') if sample and sample.envelope_id else []
		context.update({'sample':sample,'tr_code_id':tr_code_id,'env_id':env_id,'envelope_samples': envelope_samples,'last_received_barcode': sample.barcode if sample and sample.barcode else request.GET.get('last_barcode', '')})
	elif env_id:
		envelope = Envelope.objects.filter(pk=env_id).first()
		context.update({'envelope_samples': envelope.sample_set.all().order_by('locator_position') if envelope else []})
	context.update({'tr_code_id': tr_code_id, 'current_tr_code': current_tr_code})
	context.update(_receive_batch_tracking_context(tracking_code))

	return render(request, 'samples/receive_bactch.html', context)

@transaction.atomic
def receive_hie(request):

	saved_sample = request.GET.get('saved_sample')
	tracking_code, tr_code_id, current_tr_code = _get_tracking_context_from_request(request)
	env_id = request.GET.get('env_id')
	facility_reference = request.GET.get('facility_reference')
	barcode_lookup = (request.GET.get('barcode') or '').strip()
	if barcode_lookup != '':
		sample = Sample.objects.filter(barcode2=barcode_lookup).first()
		ret = {
			'hep_number': '',
			'date_collected': '',
			'err_msg': '',
			'is_dr': 0,
		}
		if sample:
			ret.update({
				'err_msg': barcode_lookup + ' is for DR',
				'is_dr': 1,
			})
		return HttpResponse(json.dumps(ret))
	if facility_reference is not None:
		if vl_services.is_hiv_program(request):
			facility_id = request.GET.get('facility_id')
			return HttpResponse(json.dumps(vl_services.get_receive_hie_details(facility_reference, facility_id)))
		facility_id = request.GET.get('facility_id')
		tracking_code_id = request.GET.get('tracking_code_id')
		tracking_code = _get_tracking_code_by_id(tracking_code_id, db_alias=get_dropdown_db_alias(request))
		ret = _lookup_existing_sample_for_reception(
			facility_reference,
			facility_id=facility_id,
			tracking_code=tracking_code,
			db_alias=get_dropdown_db_alias(request),
		)
		s = _find_existing_sample_for_reception(
			facility_reference,
			facility_id,
			db_alias=get_dropdown_db_alias(request),
		)
		mismatch_message = get_program_mismatch_message(request, get_sample_program_code(s), 'sample')
		if mismatch_message:
			ret.update({
				'hep_number': '',
				'date_collected': '',
				'err_msg': mismatch_message,
				'is_dr': 0,
			})
		return HttpResponse(json.dumps(ret))

	if current_tr_code is None:
		current_tr_code = ''
	if request.method == 'POST':
		pst = request.POST
		conflict_sample = _get_received_barcode_conflict(request, pst.get('the_barcode'))
		if conflict_sample:
			return HttpResponse(json.dumps({
				'saved_sample': '',
				'env_id': pst.get('envelope_id'),
				'tracking_code_id': pst.get('tracking_code_id'),
				's_barcode': pst.get('the_barcode', ''),
				'receipt_type': 'not_allowed',
				'message_type': 'err',
				'err_msg': DUPLICATE_BARCODE_MESSAGE,
			}))
		sample_reception_form = SampleReceptionForm(pst)
		tr_code_id = request.POST.get('tracking_code_id')
		facility_reference = request.POST.get('facility_reference')
		facility_id = request.POST.get('facility')
		barcode = request.POST.get('the_barcode')
		hep_number = request.POST.get('reception_hep_number')
		env_id_raw = request.POST.get('envelope_id')
		try:
			env_id = int(env_id_raw)
		except (TypeError, ValueError):
			return HttpResponse(json.dumps({
				'saved_sample': '',
				'env_id': env_id_raw or '',
				'tracking_code_id': tr_code_id,
				's_barcode': barcode or '',
				'receipt_type': 'not_allowed',
				'message_type': 'err',
				'err_msg': 'Envelope was not found, did you accession it?'
			}))
		try:
			date_collected = posted_date(request.POST, 'date_collected')
		except ValidationError as e:
			return HttpResponse(json.dumps({
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': barcode or '',
				'receipt_type': 'not_allowed',
				'message_type': 'err',
				'err_msg': str(e)
			}))
		required_message = ''
		if not barcode:
			required_message = 'Locator ID is required.'
		elif not facility_id:
			required_message = 'Facility is required.'
		elif not facility_reference:
			required_message = 'Facility identifier is required.'
		elif not hep_number:
			required_message = 'Hep number is required when the facility identifier is not found.'
		if required_message:
			return HttpResponse(json.dumps({
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': barcode or '',
				'receipt_type': 'not_allowed',
				'message_type': 'err',
				'err_msg': required_message
			}))
		mismatch_message = lock_envelope_to_session_program(request, env_id)
		if mismatch_message:
			ret = {
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': request.POST.get('the_barcode'),
				'receipt_type': 'not_allowed',
				'err_msg': mismatch_message
			}
			return HttpResponse(json.dumps(ret))
		db_alias = get_dropdown_db_alias(request)
		s = _find_existing_sample_for_reception(
			facility_reference,
			facility_id,
			db_alias=db_alias,
		)
		tracking_code = _resolve_tracking_code_for_sample(
			s,
			tr_code_id,
			request.POST.get('code'),
			request.user.id,
			facility_id,
			db_alias=db_alias,
		)
		if tracking_code is None:
			return HttpResponse(json.dumps({
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': request.POST.get('the_barcode'),
				'receipt_type': 'not_allowed',
				'message_type': 'err',
				'err_msg': 'Tracking code is required.'
			}))
		if _should_block_tracking_code_facility_mismatch(s, tracking_code, facility_id):
			return HttpResponse(json.dumps({
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tracking_code.id,
				's_barcode': request.POST.get('the_barcode'),
				'receipt_type': 'not_allowed',
				'message_type': 'err',
				'err_msg': TRACKING_CODE_FACILITY_MISMATCH_MESSAGE
			}))
		tr_code_id = tracking_code.id
		saved_id = request.POST.get('saved_id')
		if not saved_id and _sample_matches_tracking_code(s, tracking_code):
			saved_id = s.pk
		conflict_sample = _get_facility_reference_conflict(
			facility_reference,
			facility_id,
			saved_id,
			db_alias=db_alias,
		)
		if conflict_sample:
			ret = {
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': request.POST.get('the_barcode'),
				'receipt_type': 'not_allowed',
				'message_type': 'err',
				'err_msg': DUPLICATE_FACILITY_REFERENCE_MESSAGE
			}
			return HttpResponse(json.dumps(ret))

		sample_program_mismatch = get_program_mismatch_message(request, get_sample_program_code(s), 'sample')
		if sample_program_mismatch:
			ret = {
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': request.POST.get('the_barcode'),
				'receipt_type': 'not_allowed',
				'err_msg': sample_program_mismatch
			}
			return HttpResponse(json.dumps(ret))

		if s and s.date_received is None:
			s.tracking_code_id = tr_code_id
			s.locator_category = 'V'
			s.envelope_id = env_id
			s.verified = 1
			s.is_data_entered = 1
			s.stage = 0
			s.locator_position=request.POST.get('the_position')
			s.barcode=request.POST.get('the_barcode')
			s.sample_type=_posted_sample_type(request)
			s.date_collected = date_collected
			#s.date_received = request.POST.get('date_received')
			s.date_received = datetime.now()
			s.received_by_id = request.user.id
			s.save()
			update_envelope_program_code(env_id, get_session_program_code(request))
			sample_utils.save_verification_details(s,request)

			ws = WorksheetSample.objects.filter(other_instrument_id=s.barcode).first()
			if ws:
				#if ws.sample is None:
				ws.sample = s
				ws.sample_type=_posted_sample_type(request)
				ws.save()
			ret = {
				'saved_sample': s.id,
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':s.barcode,
				'receipt_type':'hie',
				'err_msg':'saved'
			}
		elif s and s.date_received is not None:
			#save as normal sample
			ret = {
				'saved_sample': '',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':s.barcode,
				'receipt_type':'not_allowed',
				'err_msg':'on'+s.barcode
			}
		elif hep_number is not None and hep_number != '':
			#save as normal sample
			s = receive_batch(request,1)
			if isinstance(s, dict):
				s.update({
					's_barcode': request.POST.get('the_barcode'),
					'receipt_type': 'not_allowed',
				})
				return HttpResponse(json.dumps(s))
			ret = {
				'saved_sample': s.id,
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':s.barcode,
				'receipt_type':'non_hie',
				'err_msg':'saved, non HIE'
			}

		else:
			ret = {
				'saved_sample': '',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':request.POST.get('the_barcode'),
				'receipt_type':'not_at_all',
				'err_msg':'not found'
			}

		return HttpResponse(json.dumps(ret))

	else:
		d = datetime.now()
		sample_reception_form = SampleReceptionForm(initial=_sample_reception_initial(tracking_code), db_alias=get_dropdown_db_alias(request))

	context = {
		'sample_reception_form': sample_reception_form,
		'tr_code_id': tr_code_id,
		'tracking_code_id': tr_code_id,
		'env_id':env_id,
		'current_tr_code':current_tr_code,
		'reception_id':'',
	}

	if saved_sample:
		sample = Sample.objects.filter(pk=saved_sample).first()
		#return HttpResponse(sample)
		context.update({'sample':sample,'tr_code_id':tr_code_id,'env_id':env_id,})

	return render(request, 'samples/receive_hie.html', context)

@transaction.atomic
def create_range(request):
	users = User.objects.all()
	now = datetime.now()
	active_program_code = programs.get_active_program_code(request)
	active_program_int = get_session_program_code(request)
	current_period = (int(now.strftime('%y')), now.month)
	previous_month_date = now.replace(day=1) - timedelta(days=1)
	previous_period = (int(previous_month_date.strftime('%y')), previous_month_date.month)
	allowed_periods = [current_period]
	if previous_period != current_period:
		allowed_periods.append(previous_period)

	def render_create_range(error_message=''):
		years = []
		for year, month in allowed_periods:
			if year not in years:
				years.append(year)
		return render(request, 'samples/create_range.html', {
			'users': users,
			'years': years,
			'logged_in_user_id': request.user.id,
			'current_year': current_period[0],
			'current_month': current_period[1],
			'previous_year': previous_period[0],
			'previous_month': previous_period[1],
			'error_message': error_message,
			'active_program_code': active_program_code,
			'active_program_int': active_program_int,
		})

	if vl_services.is_hiv_program(request):
		if request.method == 'POST':
			try:
				vl_services.create_range(request.POST, request.user)
				return redirect('/samples/create_range/')
			except Exception as e:
				return render_create_range(str(e))
		return render_create_range()
	if request.method == 'POST':
		year = request.POST.get('year', '')
		month = request.POST.get('month', '')
		lower_limit_raw = request.POST.get('lower_limit', '')
		upper_limit_raw = request.POST.get('upper_limit', '')
		program_code = active_program_int or request.POST.get('program_code')
		sample_type = 'P' if sample_utils.is_hep_program_code(program_code) else request.POST.get('sample_type')
		envelope_type = request.POST.get('envelope_type') or '1'
		try:
			year_int = int(year)
			month_int = int(month)
		except (TypeError, ValueError):
			return render_create_range('Invalid accession range input.')
		if (year_int, month_int) not in allowed_periods:
			return render_create_range('Accessioning is restricted to the current month and previous month only.')
		year_month = year + month
		try:
			lower_boundary = sample_utils.parse_envelope_range_boundary(lower_limit_raw, program_code, year_month)
			upper_boundary = sample_utils.parse_envelope_range_boundary(upper_limit_raw, program_code, year_month)
		except (TypeError, ValueError) as e:
			return render_create_range(str(e) or 'Invalid accession range input.')
		if lower_boundary.get('year_month') != year_month or upper_boundary.get('year_month') != year_month:
			return render_create_range('Envelope range must match the selected year and month.')
		l_limit = lower_boundary.get('increment')
		u_limit = upper_boundary.get('increment')
		number_of_envs = (u_limit - l_limit) + 1
		if number_of_envs <= 0:
			return render_create_range('Upper limit must be greater than or equal to lower limit.')
		lower_sample_type = lower_boundary.get('sample_type')
		upper_sample_type = upper_boundary.get('sample_type')
		if lower_sample_type != upper_sample_type:
			return render_create_range('Mixed ranges are not allowed. Split Plasma and DBS envelopes into separate accession batches.')
		if sample_type != lower_sample_type:
			return render_create_range('Sample type does not match the selected envelope range.')
		env_range = EnvelopeRange()
		env_range.year_month = year_month
		env_range.lower_limit = lower_boundary.get('stored_limit')
		env_range.upper_limit = upper_boundary.get('stored_limit')
		env_range.sample_type = sample_type
		env_range.accessioned_by_id = request.POST.get('accessioned_by')
		#env_range.accessioned_at = request.POST.get('accessioned_at')
		env_range.accessioned_at = now.date()
		env_range.entered_by = request.user
		env_range.created_at = now
		env_range.save()

		for lim in range(l_limit, u_limit + 1):
			if sample_utils.is_hep_program_code(program_code):
				env_number = sample_utils.format_hep_envelope_number(program_code, year_month, lim)
			else:
				env_number = year_month+'-'+str(lim).zfill(4)
			envelope = Envelope.objects.select_for_update().filter(envelope_number=env_number).first()
			if envelope is None:
				envelope = Envelope(envelope_number=env_number)

			envelope.sample_type = sample_type
			envelope.type = int(envelope_type)
			envelope.program_code = program_code
			envelope.accessioned_at = now
			envelope.envelope_range = env_range
			envelope.accessioner = request.user
			envelope.assignment_by = request.user
			envelope.save()

			EnvelopeAssignment.objects.get_or_create(
				the_envelope=envelope,
				assigned_to_id=request.user.id,
				assigned_by=request.user,
				type=1,
			)
		return redirect('/samples/create_range/')

	return render_create_range()

@permission_required('samples.change_sample', login_url='/login/')
def edit_received(request, reception_id):
	if request.method == 'POST':
		accepted = request.POST.get('locator_category')
		rejection_reason_id = request.POST.get('rejection_reason_id')
		facility_id = request.POST.get('facility')
		hep_number = request.POST.get('reception_hep_number')
		if(accepted=='R' and not rejection_reason_id):
			return HttpResponse("rejection reason required for rejected samples")
		tr = _resolve_tracking_code(
			request.POST.get('tracking_code_id'),
			request.POST.get('code'),
			request.user.id,
			facility_id,
		)
		sample_reception = Sample.objects.get(pk=reception_id)
		if sample_reception:
			sample_reception.facility_id = facility_id
			sample_reception.reception_hep_number = hep_number
			sample_reception.date_collected = posted_date(request.POST, 'date_collected')
			sample_reception.sample_type = _posted_sample_type(request) or sample_reception.sample_type
			if tr:
				sample_reception.tracking_code_id = tr.id
			if(accepted=='R'):
				sample_reception.verification.rejection_reason_id = rejection_reason_id
				sample_reception.verification.accepted = False
				sample_reception.locator_category = 'R'
			else:
				sample_reception.verification.rejection_reason_id = None
				sample_reception.verification.accepted = True
			sample_reception.verification.verified_by = request.user
			sample_reception.save()
			update_envelope_program_code(sample_reception.envelope_id, get_session_program_code(request))
			sample_reception.verification.save()
		if sample_reception.patient_id:
			sample_reception.patient.hep_number = hep_number
			sample_reception.patient.facility_id = facility_id
			unique_id = "%s-A-%s" %(facility_id, utils.removeSpecialCharactersFromString(hep_number))
			sample_reception.patient.unique_id = unique_id
			sample_reception.patient.save()
		return redirect("/samples/show/%d" %sample_reception.pk)
	else:
		sample_reception = Sample.objects.get(pk=reception_id)
		verification = Verification.objects.filter(sample=sample_reception).first()
		context = {
			'sample_reception_form':SampleReceptionForm(instance=sample_reception),
			'current_tr_code': sample_reception.tracking_code.code if sample_reception.tracking_code_id else '',
			'tracking_code_id': sample_reception.tracking_code_id or '',
			'env_id': sample_reception.envelope_id or '',
			'page_type': '',
			'reception_id':reception_id,
			'locator_category':sample_reception.locator_category,
			'reception_hep_number':sample_reception.reception_hep_number,
			'facility_reference':sample_reception.facility_reference,
			'rejection_reason_id': verification.rejection_reason_id if verification else '',
		}
		return render(request, 'samples/receive.html', context)

@permission_required('samples.change_sample', login_url='/login/')
def edit(request, sample_id):
	sample = Sample.objects.get(pk=sample_id)
	patient = sample.patient if sample.patient_id else Patient(
		facility_id=sample.facility_id,
		hep_number=sample.reception_hep_number,
	)
	count_dr = 0
	drug_resistance = None
	date_received = sample.date_received
	preliminary_findings_instance = None
	try:
		drug_resistance = sample.drugresistancerequest
		count_dr = PastRegimens.objects.filter(drug_resistance_request=drug_resistance).count()
	except :
		pass
	try:
		preliminary_findings_instance = PreliminaryFindings.objects.filter(patient_id=sample.patient_id).order_by('-id').first()
	except:
		pass

	PastRegimensFormSet = modelformset_factory(PastRegimens, form=PastRegimensForm,
							extra=(5-count_dr))


	intervene = request.GET.get('intervene')
	envelope_form = EnvelopeForm(instance=sample.envelope)
	patient_form = PatientForm(instance=patient)
	preliminary_findings = PreliminaryFindingsForm(instance=preliminary_findings_instance)
	if patient:
		sample.facility = patient.facility
	db_alias = get_dropdown_db_alias(request)
	sample_form = SampleForm(instance=sample, db_alias=db_alias)
	drug_resistance_form = DrugResistanceRequestForm(instance=drug_resistance)
	past_regimens_formset = bind_past_regimens_formset(
		PastRegimensFormSet(queryset=PastRegimens.objects.filter(drug_resistance_request=drug_resistance)),
		db_alias,
	)
	facilities = get_facilities_qs(request)

	context = {
		'sample_id': sample_id,
		'patient_form': patient_form,
		'preliminary_findings': preliminary_findings,
		'preliminary_findings_form': preliminary_findings,
		'sample_form': sample_form,
		'vsi': sample.vl_sample_id,
		'drug_resistance_form': drug_resistance_form,
		'past_regimens_formset': past_regimens_formset,
		'facilities': facilities,
		'regimens': get_regimens_qs(request),
		'intervene': intervene,
		'date_received': date_received,
		'from_page': request.GET.get('from_page'),
		'page_type': 2,
		'facilities': facilities,
		'treatment_indication_options': utils.TREATMENT_INFO_OPTIONS,
		'selected_treatment_ids': '',
	}

	return render(request, 'samples/create.html', context)


def does_form_number_exist(request, form_number):
	if Sample.objects.filter(form_number = form_number).exists():
		#check if this is an HIE form
		#Sample.objects.get(form_number = form_number)
		#Sample.objects.filter(barcode = request.GET.get('barcode')).first()
		#return HttpResponse('truth is true')
		return HttpResponse(form_number)
	else:
		return HttpResponse('')

def get_district_hub(request, facility_id):
	district_hub = sample_utils.get_district_hub_by_facility(
		facility_id,
		get_dropdown_db_alias(request),
	)
	return HttpResponse(district_hub)

def get_patient(request):

	#district_hub = sample_utils.get_district_hub_by_facility(facility_id)
	facility_id = request.GET.get('facility_id')
	hep_number = request.GET.get('hep_number')
	#facility = Facility.objects.get(pk=facility_id)
	ret = {}
	#for now turn off this feature
	#return HttpResponse(json.dumps(ret))
	unique_id = "%s-A-%s" %(facility_id, hep_number.replace(' ','').replace('-','').replace('/',''))
	#patient = FacilityPatient.objects.filter( Q(facility_id=facility_id,unique_id=unique_id)).first()
	patient = Patient.objects.filter(unique_id=unique_id).order_by('-created_at').first()

	if patient:
		treatment_initiation = ''
		if patient.treatment_initiation_date:
			treatment_initiation = patient.treatment_initiation_date.strftime("%m/%d/%Y").__str__()
		dob = ''
		if patient.dob:
			dob = patient.dob.strftime("%m/%d/%Y").__str__()
		ret = {
			'patient_id':patient.id,
			'treatment_initiation_date':treatment_initiation,
			'dob': dob,
			'gender':patient.gender,
			'other_id':patient.other_id,
			'is_facility_clean': '',
			}
	else:
		ret = {
				'is_facility_clean': ''
			}

	return HttpResponse(json.dumps(ret))

def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()

def get_barcode_details(request):
	barcode = request.GET.get('barcode')
	if vl_services.is_hiv_program(request):
		try:
			parsed_barcode = sample_utils.parse_locator_id(barcode, programs.get_active_program_code(request))
			if parsed_barcode:
				barcode = parsed_barcode.get('barcode')
		except ValueError:
			pass
		return HttpResponse(json.dumps(vl_services.get_barcode_details(barcode)))
	ret = {'barcode_exists': False, 'err_msg': ''}
	sample = _get_received_barcode_conflict(request, barcode)
	if sample:
		rec_date = sample.date_received
		date_received = rec_date.strftime('%Y-%m-%d') if rec_date else ''
		err_msg = get_program_mismatch_message(request, get_sample_program_code(sample), 'sample')
		ret = {
			'barcode_exists': True,
			'reception_facility': sample.facility_id,
			's_id': sample.id,
			'is_data_entered': sample.is_data_entered,
			'reception_hep_number': sample.reception_hep_number,
			'date_received': date_received,
			'barcode': sample.barcode or '',
			'envelope_number': sample.envelope.envelope_number if sample.envelope_id else '',
			'locator_position': sample.locator_position or '',
			'locator_category': sample.locator_category or '',
			'sample_type': sample.sample_type or '',
			'program_mismatch': bool(err_msg),
			'err_msg': err_msg or DUPLICATE_BARCODE_MESSAGE,
			}

	return HttpResponse(json.dumps(ret))

def show(request, sample_id):
	sample = Sample.objects.get(pk=sample_id)
	patient = sample.patient if sample.patient_id else Patient(
		facility_id=sample.facility_id,
		hep_number=sample.reception_hep_number,
	)
	drug_resistance = None
	try:
		drug_resistance = sample.drugresistancerequest
	except :
		pass

	PastRegimensFormSet = modelformset_factory(PastRegimens, form=PastRegimensForm)

	context = {
		'sample_id': sample_id,

		'patient_form': PatientForm(instance=patient),
		'sample_form': SampleForm(instance=sample),
		'drug_resistance_form': DrugResistanceRequestForm(instance=drug_resistance),
		'past_regimens_formset': PastRegimensFormSet(queryset=PastRegimens.objects.filter(drug_resistance_request=drug_resistance)),
		'vl_sample_id': sample.vl_sample_id,
	}

	return render(request, 'samples/show.html', context)

def list(request):
	search_val = request.GET.get('search_val')
	is_data_entered = request.GET.get('is_data_entered')
	sample_without_results = request.GET.get('sample_without_results')
	hie_samples_pending_reception = request.GET.get('hie_samples_pending_reception')
	tracking_code_id = request.GET.get('tracking_code_id')
	tracking_code = request.GET.get('tracking_code')

	return render(request, 'samples/list.html', {
		'global_search':search_val,
		'is_data_entered':is_data_entered,
		'sample_without_results':sample_without_results,
		'hie_samples_pending_reception':hie_samples_pending_reception,
		'tracking_code_id': tracking_code_id,
		'tracking_code': tracking_code,
	})


def tracking_codes(request):
	return render(request, 'samples/tracking_codes.html')

def update_patient_parent(request):
	parent_patients = Patient.objects.filter(is_the_clean_patient=1, facility_id=1526)[:100]
	cursor = connections['default'].cursor()
	for parent_patient in parent_patients:

		#assign update each patient with this facility_id and unique_id to all that don't have a parent

		patients_for_parent = Patient.objects.filter(unique_id=parent_patient.unique_id,facility_id=parent_patient.facility_id)
		if patients_for_parent.count > 0:
			for patient in patients_for_parent:
				connections['default'].cursor().execute("UPDATE vl_patients SET parent_id=%s WHERE id=%s",[parent_patient.id,patient.id])

	return HttpResponse('done')

def pending_verification_list(request):
	search_val = request.GET.get('search_val')
	if request.method == 'POST':
		patient_id = request.POST.get('patient_id')
		p_type = request.POST.get('type')
		patient = Patient.objects.get(pk=patient_id)
		if patient:
			if(p_type == 'new'):
				patient.is_verified = 1
				patient.parent_id = patient_id
				#add other conditions here
				patient.save()
				return HttpResponse(1)
			else:
				#get the patient for consideration
				hep_number = request.POST.get('hep_number')
				facility_id = request.POST.get('facility_id')
				unique_id = "%s-A-%s" %(facility_id, hep_number.replace(' ','').replace('-','').replace('/',''))
				merge_old_patient = Patient.objects.filter(unique_id=unique_id,facility_id=facility_id).first()

				if merge_old_patient:
					#if transfered, create the historical record
					if p_type == 'transfer':
						patient_transfer_history = patientTransferHistory()
						patient_transfer_history.old_hep_number = merge_old_patient.hep_number
						patient_transfer_history.current_hep_number = patient.hep_number
						patient_transfer_history.old_facility_id  = merge_old_patient.facility_id
						patient_transfer_history.current_facility_id = patient.facility_id
						patient_transfer_history.created_at = datetime.now()
						patient_transfer_history.save()
						#assign the old patient the new art number
						merge_old_patient.hep_number = patient.hep_number
						merge_old_patient.save()


					#assign the sample to the right patient_id
					sample = Sample.objects.get(patient_id=patient.id)
					sample.patient_id = merge_old_patient.id
					sample.patient_id = merge_old_patient.id
					sample.facility_id = merge_old_patient.facility_id
					sample.save()

					patient.parent_id = merge_old_patient.id
					patient.is_verified = 2
					patient.save()
					return HttpResponse('done')
						#set the patient to be this merge_patient

	patients = Patient.objects.filter(is_verified=0)[:500]
	facilities = Facility.objects.values('id', 'facility').order_by('facility')
	facility_dropdown = utils.select( "facility_id",
									  {'k_col':'id', 'v_col':'facility', 'items':facilities })
	return render(request, 'samples/pending_verification_list.html', {'global_search':search_val,'patients':patients,'facilities':facilities})

def appendix_select(name="", cat_id=0, clss='form-control input-xs w-md'):
	apendices = Appendix.objects.values('id','appendix')
	more = {'class': clss}
	return utils.select(name,{'k_col':'id', 'v_col':'appendix', 'items':apendices.filter(appendix_category_id=cat_id)},"",more)

@permission_required('samples.add_verification', login_url='/login/')
@transaction.atomic
def verify(request, sample_id):
	if request.method == 'POST':
		sample = Sample.objects.get(pk=sample_id)
		sample.verified = 1
		sample.verified_at = datetime.now().date()
		sample.verifier = request.user
		sample.save()
		#if there is a result, release it
		result = Result.objects.filter(sample_id=sample.id).first()
		if result is not None and result.resultsqc.released == 0:
			result.resultsqc.released = 1
			result.resultsqc.released_at = datetime.now()
			result.resultsqc.save()
		return HttpResponse('verified')
	else:
		return HttpResponse('not allowed')

@transaction.atomic
def remove(request, sample_id):
	if request.method != 'POST':
		return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
	sample = get_object_or_404(Sample.objects.select_for_update(), pk=sample_id)
	if sample.stage != 0:
		return JsonResponse({'success': False, 'message': 'Only stage 0 samples can be removed.'}, status=400)
	#remove sample id from identifiers and worksheet samples
	#connections['default'].cursor().execute("UPDATE vl_sample_identifiers SET sample_id=null WHERE sample_id=%s",[sample.id])
	connections['default'].cursor().execute("DELETE from vl_worksheet_samples WHERE sample_id=%s",[sample.id])
	#now remove sample
	#return envelope to lab
	envelope = sample.envelope
	if envelope:
		envelope.is_lab_completed = 0
		envelope.processed_by_id = None
		envelope.save()
	#source-system samples are returned to pending packaging, others are deleted
	if sample.source_system_id:
		_return_source_system_sample_to_pending_packaging(sample)
		return JsonResponse({'success': True, 'message': 'Source-system sample moved to pending packaging.'})
	else:
		sample.delete()
		return JsonResponse({'success': True, 'message': 'Sample removed.'})

@permission_required('samples.delete_sampleapprovalstats', login_url='/login/')
@transaction.atomic
def switch_samples(request):
	r = request.POST
	env_id = r.get('env_id')
	if env_id is not None:
		#nullify barcode n locator_positions for samples on this envelope to avoid errors of duplication
		Sample.objects.filter(envelope_id=env_id).update(barcode=None,locator_position=None)
	new_barcode = r.get('new_barcode')
	sample_id = r.get('sample_id')
	if new_barcode:
		sample = Sample.objects.get(pk = sample_id)
		sample.barcode = new_barcode
		sample.locator_position = r.get('locator_posn')
		#if data is not yet entered, nulify form_number to avoid cases of repeat form_number
		if sample.is_data_entered == 0:
			sample.form_number = None
		sample.save()

		if sample.facility_reference is None:
			print('fac ref is empty')
			ws = WorksheetSample.objects.filter(sample_id = sample_id).first()
			if ws:
				ws.instrument_id = new_barcode
				ws.save()
	return HttpResponse('saved')

@permission_required('samples.add_verification', login_url='/login/')
def detach_sample(request):
	s_id = request.POST.get('sample_id')
	sample = Sample.objects.get(pk=s_id)
	sample.locator_category =None
	sample.locator_position =None
	sample.date_received =None
	sample.barcode =None
	sample.save()
	ws = WorksheetSample.objects.filter(sample_id = sample_id).first()
	if ws:
		ws.other_instrument_id = None
		ws.save()
	return HttpResponse('detached')

@permission_required('samples.add_verification', login_url='/login/')
def get_rejection_reasons(request):
	ret = RejectionReasons(request.GET.get('sample_type')).rejection_reasons
	return HttpResponse(json.dumps(ret))

@permission_required('samples.add_verification', login_url='/login/')
def save_verify(request):
	r = request.POST
	bcode = r.get('barcode')
	if not bcode == "":
		if len(r.get('barcode')) > 14:
			return HttpResponse('the the barcode length should not be more than 14 characters long')
	pat_edits = int(r.get('pat_edits'))
	sample_edits = int(r.get('sample_edits'))
	if(pat_edits>0):
		p = Patient.objects.get(pk=r.get('patient_id'))
		p.hep_number = r.get('hep_number', '')
		p.other_id = r.get('other_id', '')
		p.dob = utils.get_date(r, 'dob')
		p.gender = r.get('gender', '')
		p.save()

	s = Sample.objects.get(pk=r.get('sample_id'))
	if sample_edits>0:

		facility_id = r.get('facility_id')
		if facility_id:
			s.facility_id = facility_id
		s.form_number = r.get('form_number')
		s.date_collected = utils.get_date(r, 'date_collected')
		s.treatment_initiation_date = utils.get_date(r, 'treatment_initiation_date')
		s.locator_category = r.get('locator_category', '')
		s.locator_position = r.get('locator_position', '')
		tx = r.get('treatment_duration')
		s.treatment_duration = tx if tx else None

	s.verified = 1
	s.barcode = r.get('barcode')
	s.save()

	if s.in_worksheet:
		return HttpResponse("sample in worksheet already")

	v = Verification.objects.filter(sample=s).first()
	v = v if v else Verification()
	v.pat_edits = pat_edits
	v.sample_edits = sample_edits
	v.sample = s
	accepted = int(r.get('accepted',0))
	v.accepted = True if accepted == 1 else False
	if(v.accepted==False):
		v.rejection_reason_id = r.get('rejection_reason_id')
		if not v.rejection_reason_id:
			return HttpResponse("rejection reason required for rejected samples")
	else:
		v.rejection_reason_id = None

	v.verified_by = request.user
	v.save()
	#mark barcode used

	if(not Sample.objects.filter(envelope=s.envelope, verified=False).count()):
		envelope = Envelope.objects.get(pk=s.envelope.pk)
		envelope.stage = 2
		envelope.save()

	return HttpResponse("saved")


@permission_required('samples.add_verification', login_url='/login/')
def verify_list(request):
	r_tab = request.GET.get('tab')
	facility_id = request.GET.get('facility_id')
	verified = int(request.GET.get('verified'))
	envelope_id = request.GET.get('envelope_id')
	db_alias = get_dropdown_db_alias(request)
	facilities = Facility.objects.using(db_alias).all()
	if verified:
		filters = Q(verified = 1,is_data_entered = 1,required_verification = 1)
	else:
		filters = Q(verified = 0,is_data_entered = 1,envelope_id__isnull=False)
	if envelope_id:
		filters = filters & Q(envelope_id = envelope_id)

	if facility_id:
		filters = filters & Q(facility_id=int(facility_id))
	#return HttpResponse(filters)
	samples = programs.filter_queryset_by_program(request, Sample.objects.using(db_alias).filter(filters), 'program_code').order_by('barcode')

	page = request.GET.get('page', 1)
	paginator = Paginator(samples, 100)
	try:
		samples = paginator.page(page)
	except PageNotAnInteger:
		samples = paginator.page(1)
	except EmptyPage:
		samples = paginator.page(paginator.num_pages)
	context = {'samples':samples,'facilities':facilities}
	return render(request, 'samples/verify_list.html', context)

@permission_required('samples.add_verification', login_url='/login/')
def receive_package(request):
	r_tab = request.GET.get('tab')
	facility_id = request.GET.get('facility_id')
	verified = int(request.GET.get('verified'))
	envelope_id = request.GET.get('envelope_id')
	facilities = Facility.objects.all()

	filters = Q(status=0)|Q(status=1)|Q(status=2)
	if facility_id:
		filters = filters & Q(facility_id=int(facility_id))
	#return HttpResponse(filters)
	packages = TrackingCode.objects.filter(filters).order_by('code')

	page = request.GET.get('page', 1)
	paginator = Paginator(packages, 100)
	try:
		packages = paginator.page(page)
	except PageNotAnInteger:
		packages = paginator.page(1)
	except EmptyPage:
		packages = paginator.page(paginator.num_pages)
	context = {'packages':packages,'facilities':facilities}
	return render(request, 'samples/receive_package.html', context)


def _search_samples_queryset(request):
	db_alias = get_dropdown_db_alias(request)
	return (
		Sample.objects.using(db_alias)
		.select_related(
			'patient__facility__district',
			'facility__district',
			'sample_reception__facility__district',
			'tracking_code',
			'clinician',
			'lab_tech',
		)
	)

def verify_list_old(request):
	search_val = request.GET.get('search_val')
	verified = request.GET.get('verified')
	context = {
		'verified':verified,
		'global_search':search_val,
	}
	if(verified=='0'):
		pending_qs = programs.filter_queryset_by_program(request, Sample.objects.filter(created_at__gte=date(settings.LIST_CUT_OFF_YEAR, settings.LIST_CUT_OFF_MONTH,settings.LIST_CUT_OFF_DATE),verified=False,envelope__sample_medical_lab=request.user.userprofile.medical_lab_id), 'program_code')
		context.update({
			'pending': pending_qs.count(),
			'pending_dbs': pending_qs.filter(sample_type='D').count(),
			'pending_plasma': pending_qs.filter(sample_type='P').count(),
			})


	return render(request, "samples/verify_list.html", context)

@permission_required('samples.add_verification', login_url='/login/')
def verify_envelope(request, envelope_id):
	samples = Sample.objects.filter(envelope_id=envelope_id).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"}).order_by('lposition_int')

	ret=[]
	for s in samples:
		facility = s.facility if hasattr(s, 'facility') else ''
		hub = facility.hub if hasattr(facility, 'hub') else ''
		hub_name = hub.hub if hasattr(hub, 'hub') else ''
		district = facility.district if hasattr(facility, 'district') else ''
		district_name = district.district if hasattr(district, 'district') else ''
		ret.append({
				'patient_id': s.patient.id,
				'sample_id': s.id,
				'accepted': "%s"%int(s.verification.accepted) if hasattr(s, 'verification') else '',
				'vl_sample_id': s.vl_sample_id,
				'locator_category': s.locator_category,
				'locator_position': s.locator_position,
				'envelope_number': s.envelope.envelope_number,
				'loc':"%s%s/%s"  %(s.locator_category, s.envelope.envelope_number, s.locator_position),
				'form_number': s.form_number,
				'sample_type':s.sample_type,
				'facility_id': str(s.facility_id),
				'facility_name': facility.facility if hasattr(facility, 'facility') else '',
				'district': district_name,
				'hub': hub_name,
				'date_collected': utils.local_date(s.date_collected),
				'hep_number': s.patient.hep_number,
				'other_id': s.patient.other_id,
				'gender': s.patient.gender,
				'barcode': s.barcode,
				'dob': utils.local_date(s.patient.dob),
				'treatment_initiation_date': utils.local_date(s.treatment_initiation_date),
				'treatment_duration':"%s"%(s.treatment_duration) if s.treatment_duration else "",
				'sample_creator': s.created_by.username,
				'created_at': utils.local_date(s.created_at),
			})
	return HttpResponse(json.dumps(ret))



def appendices_json(cat_id):
	appendices = Appendix.objects.values('id', 'appendix').filter(appendix_category_id=cat_id)
	ret={}
	for a in appendices:
		ret[a['id']] = a['appendix']
	return json.dumps(ret)

def pat_hist(request, facility_id):
	ret = []
	hep_number = request.GET.get('hep_number')
	if hep_number == '':
		return HttpResponse(json.dumps(ret))
	unique_id = "%s-A-%s" %(facility_id, hep_number.replace(' ','').replace('-','').replace('/',''))
	#samples = Sample.objects.filter( Q(patient__unique_id=unique_id)|Q(facility_id=facility_id,patient__hep_number=hep_number)).order_by('-date_collected')[:3]
	#samples = Sample.objects.filter( Q(patient__unique_id=unique_id)).order_by('-date_collected')[:3]
	#samples = Sample.objects.filter(Q(patient__unique_id=unique_id)).select_related('patient').only('form_number', 'date_collected', 'patient__hep_number', 'patient__other_id').order_by('-date_collected')[:3]

	samples = (
    Sample.objects
    .filter(patient__unique_id=unique_id)
    .select_related('patient')  # Joins patient data in single query
    .prefetch_related('result')  # Efficiently gets related results
    .only(  # Only fetch fields we actually use
        'form_number',
        'date_collected',
        'patient__hep_number',
        'patient__other_id',
        'patient__id',
        'patient__gender',
        'patient__dob'
	).order_by('-date_collected')[:3]
	)

	# Prepare response data
	ret = []
	for s in samples:
		# Get result if it exists (already prefetched)
		result = getattr(s, 'result', None)
		ret.append({
	        'form_number': s.form_number,
	        'date_collected': utils.local_date(s.date_collected),
	        'hep_number': s.patient.hep_number,  # No additional query needed
	        'other_id': s.patient.other_id,
	        'patient_id': s.patient.id,
	        'gender': s.patient.gender,
	        'dob': utils.local_date(s.patient.dob),
	        'result': result_utils.format_result_for_display(result),
	        'test_date': utils.local_date(result.test_date) if result else '',
	    })
	return HttpResponse(json.dumps(ret))

def release_rejects(request):
	if request.method == 'POST':
		sample = Sample.objects.get(pk=request.POST.get('sample_pk'))
		choice = request.POST.get('choice')
		released = 1 if choice == 'release' else 3

		comments = request.POST.get('comments')

		other_params = {
			'released': released,
			'comments': request.POST.get('comments'),
			'reject_released_by': request.user,
			'released_at': datetime.now().date(),
		}
		rsr, rsr_created = RejectedSamplesRelease.objects.update_or_create(sample=sample, defaults=other_params)
		return HttpResponse("saved")
	else:
		date_rejected_fro = request.GET.get('date_rejected_fro',date.today().strftime("%Y-%m-1"))
		date_rejected_to = request.GET.get('date_rejected_to',date.today().strftime("%Y-%m-%d"))

		released = request.GET.get('released', '0')
		if released == '3':
			rlsd = 3
		else:
			rlsd = True if released=='1' else None

		rejects = programs.filter_queryset_by_program(request, Verification.objects.filter(accepted=False, sample__rejectedsamplesrelease__released=rlsd,  sample__date_received__gte=date_rejected_fro, sample__date_received__lte=date_rejected_to), 'sample__program_code')
		context = {	'rejects':rejects,
					'date_rejected_fro':date_rejected_fro,
					'date_rejected_to':date_rejected_to,
					'released':released,}

		return render(request, "samples/release_rejects.html", context)

@permission_required('results.add_result', login_url='/login/')
def received(request):
	samples = programs.filter_queryset_by_program(request, Sample.objects.filter(created_at__gte=date(settings.LIST_CUT_OFF_YEAR, settings.LIST_CUT_OFF_MONTH,settings.LIST_CUT_OFF_DATE),is_data_entered=0), 'program_code').order_by('-created_at')[:1000]
	context = {'samples': samples}
	return render(request, 'samples/received_samples.html', context)


def intervene_list(request):
	intervene_rejects = programs.filter_queryset_by_program(request, RejectedSamplesRelease.objects.filter(released=False,sample__envelope__sample_medical_lab=utils.user_lab(request)), 'sample__program_code')[:500]
	return render(request, 'samples/intervene_list.html', {'intervene_rejects':intervene_rejects})

def search(request):
	allowed_program_edit_user_ids = (31, 69)
	can_edit_program = request.user.id in allowed_program_edit_user_ids
	if request.method == 'POST':
		if request.POST.get('action') == 'update_program':
			if not can_edit_program:
				return JsonResponse({'error': 'Not allowed'}, status=403)
			sample = Sample.objects.filter(pk=request.POST.get('sample_id')).first()
			program_code = request.POST.get('program_code')
			if sample is None:
				return JsonResponse({'error': 'Sample not found'}, status=404)
			if str(program_code) not in ('1', '2', '3'):
				return JsonResponse({'error': 'Invalid program'}, status=400)
			sample.program_code = int(program_code)
			sample.save()
			return JsonResponse({'saved': True, 'label': sample.get_program_code_display(), 'program_code': str(sample.program_code)})
		return JsonResponse({'error': 'Invalid action'}, status=400)
	if vl_services.is_hiv_program(request):
		search = request.GET.get('search_val')
		approvals = request.GET.get('approvals')
		remove_sample = request.GET.get('remove_sample')
		switch_sample = request.GET.get('switch_sample')
		with_results = request.GET.get('with_results')
		search_env = request.GET.get('search_env')
		search_sample = request.GET.get('search_sample')
		dr_sample_matches = []
		samples = vl_services.search_samples(search, search_env=bool(search_env), search_sample=bool(search_sample))
		if search and search_sample:
			dr_sample_matches = builtins.list(vl_services.VLSample.objects.using('vl_lims').filter(barcode2=(search or '').strip())[:20])
		if switch_sample:
			return render(request, 'samples/switch_samples.html', {'samples':samples, 'approvals':approvals,'switch_sample':switch_sample,'envelope_id':''})
		elif with_results:
			return render(request, 'samples/with_results.html', {'samples':samples, 'approvals':approvals,'with_results':with_results,'envelope_id':''})
		return render(request, 'samples/search.html', {
			'samples':samples,
			'approvals':approvals,
			'remove_sample':remove_sample,
			'switch_sample':switch_sample,
			'program_choices': Sample.PROGRAM_CODES,
			'can_edit_program': can_edit_program,
			'dr_sample_matches': dr_sample_matches,
		})
	cond = Q()
	search = request.GET.get('search_val')
	approvals = request.GET.get('approvals')
	remove_sample = request.GET.get('remove_sample')
	switch_sample = request.GET.get('switch_sample')
	with_results = request.GET.get('with_results')
	search_env = request.GET.get('search_env')
	search_sample = request.GET.get('search_sample')
	env_id = ''
	samples = None
	dr_sample_matches = []
	if search:
		search = search.strip()
		if search_env:
			db_alias = get_dropdown_db_alias(request)
			env = Envelope.objects.using(db_alias).filter(sample_utils.env_cond(search)).first()

			if env:
				env_id = env.id
				search = search.replace("-","")
				samples = _search_samples_queryset(request).filter(envelope=env).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"})

		else:
			if search_sample:
				direct_lookup = (
					sample_utils.exact_or_legacy_duplicate_cond('facility_reference', search) |
					sample_utils.exact_or_legacy_duplicate_cond('barcode', search) |
					sample_utils.exact_or_legacy_duplicate_cond('barcode2', search) |
					sample_utils.exact_or_legacy_duplicate_cond('form_number', search)
				)
				samples = _search_samples_queryset(request).filter(direct_lookup).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"})
				dr_sample_matches = builtins.list(_search_samples_queryset(request).filter(sample_utils.exact_or_legacy_duplicate_cond('barcode2', search))[:20])

			else:
				fn_cond = Q(form_number__startswith=search)
				facility_reference_cond = Q(facility_reference__startswith=search)
				barcode_cond = Q(barcode__startswith=search)
				barcode2_cond = Q(barcode2__startswith=search)
				loc_cond = sample_utils.locator_cond(search)
				cond = fn_cond | facility_reference_cond | barcode_cond | barcode2_cond
				cond = cond | loc_cond if loc_cond else cond
				samples = _search_samples_queryset(request).filter(cond).extra({'lposition_int': "CAST(locator_position as UNSIGNED)"})

	if samples is not None:
		filtered_samples = programs.filter_queryset_by_program(request, samples, 'program_code')
		if not (search_sample or search_env) or filtered_samples.exists():
			samples = filtered_samples
		samples = samples[:300]

	if switch_sample:
		return render(request, 'samples/switch_samples.html', {'samples':samples, 'approvals':approvals,'switch_sample':switch_sample,'envelope_id':env_id})
	elif with_results:
		return render(request, 'samples/with_results.html', {'samples':samples, 'approvals':approvals,'with_results':with_results,'envelope_id':env_id})
	else:
		return render(request, 'samples/search.html', {
			'samples':samples,
			'approvals':approvals,
			'remove_sample':remove_sample,
			'switch_sample':switch_sample,
			'program_choices': Sample.PROGRAM_CODES,
			'can_edit_program': can_edit_program,
			'dr_sample_matches': dr_sample_matches,
		})

def envelope_list(request):
	return render(request, 'samples/envelope_list.html')


def manage_envelopes(request):
	return render(request, 'samples/manage_envelopes.html')


def manage_envelopes_json(request):
	r = request.GET
	start = int(r.get('start', 0))
	length = int(r.get('length', 10))
	search = (r.get('search[value]', '') or '').strip()
	lab = utils.user_lab(request)

	envelopes = Envelope.objects.filter(sample_medical_lab=lab).annotate(sample_count=Count('sample'))
	if search:
		envelopes = envelopes.filter(Q(envelope_number__icontains=search) | Q(sample_type__icontains=search))

	records_total = Envelope.objects.filter(sample_medical_lab=lab).count()
	records_filtered = envelopes.count()
	envelopes = envelopes.order_by('-created_at')[start:start + length]

	data = []
	for envelope in envelopes:
		can_manage = _can_manage_envelope(envelope)
		actions = """
			<button type='button' class='btn btn-xs btn-primary edit-envelope' data-envelope='{0}'>Edit</button>
			<button type='button' class='btn btn-xs btn-danger delete-envelope' data-envelope='{0}' {1}>Delete</button>
		""".format(envelope.id, '' if can_manage else 'disabled="disabled"')
		data.append([
			envelope.envelope_number,
			envelope.get_type_display() or dict(Envelope.TYPES)[1],
			envelope.get_sample_type_display(),
			envelope.sample_count,
			'Yes' if can_manage else 'No',
			actions,
		])

	return JsonResponse({
		'draw': r.get('draw'),
		'recordsTotal': records_total,
		'recordsFiltered': records_filtered,
		'data': data,
	})


def manage_envelope_details(request, envelope_id):
	envelope = get_object_or_404(Envelope, pk=envelope_id, sample_medical_lab=utils.user_lab(request))
	return JsonResponse({
		'id': envelope.id,
		'envelope_number': envelope.envelope_number,
		'type': envelope.type or 1,
		'sample_count': envelope.sample_set.count(),
		'can_manage': _can_manage_envelope(envelope),
	})


@transaction.atomic
def manage_envelope_update(request, envelope_id):
	envelope = get_object_or_404(Envelope, pk=envelope_id, sample_medical_lab=utils.user_lab(request))
	if request.method != 'POST':
		return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
	if not _can_manage_envelope(envelope):
		return JsonResponse({'success': False, 'message': 'Only envelopes with stage 0 samples can be changed.'}, status=400)

	new_number = (request.POST.get('envelope_number') or '').strip()
	try:
		new_type = int(request.POST.get('type', envelope.type))
	except (TypeError, ValueError):
		new_type = envelope.type
	if not new_number:
		return JsonResponse({'success': False, 'message': 'Envelope number is required.'}, status=400)
	if new_type not in [1, 2]:
		new_type = 1
	if Envelope.objects.exclude(pk=envelope.id).filter(envelope_number=new_number).exists():
		return JsonResponse({'success': False, 'message': 'Envelope number already exists.'}, status=400)

	number_changed = envelope.envelope_number != new_number
	envelope.envelope_number = new_number
	envelope.type = new_type
	envelope.save()

	PendingReceptionQueue.objects.filter(envelope=envelope).update(envelope_number=new_number)
	PendingEntryQueue.objects.filter(envelope=envelope).update(envelope_number=new_number)

	if number_changed:
		for sample in envelope.sample_set.all():
			new_barcode = _format_sample_barcode(new_number, sample.locator_position)
			sample.barcode = new_barcode
			sample.save(update_fields=['barcode'])
			if sample.sample_reception_id:
				SampleReception.objects.filter(pk=sample.sample_reception_id).update(barcode=new_barcode)

	return JsonResponse({'success': True, 'message': 'Envelope updated.'})


@transaction.atomic
def manage_envelope_delete(request, envelope_id):
	if request.method != 'POST':
		return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
	envelope = get_object_or_404(
		Envelope.objects.select_for_update(),
		pk=envelope_id,
		sample_medical_lab=utils.user_lab(request),
	)
	samples = envelope.sample_set.select_for_update()
	if samples.exclude(stage=0).exists():
		return JsonResponse({'success': False, 'message': 'Only envelopes with stage 0 samples can be deleted.'}, status=400)

	detached_count = samples.filter(source_system_id__isnull=False).update(**SOURCE_SYSTEM_PENDING_PACKAGING_UPDATES)
	deleted_count = samples.count()
	envelope.delete()
	return JsonResponse({
		'success': True,
		'message': 'Envelope deleted. {0} sample(s) deleted and {1} source-system sample(s) moved to pending packaging.'.format(
			deleted_count,
			detached_count,
		),
	})


def facility_hep_numbers(request, facility_id):
	facility_samples = Sample.objects.filter(facility=facility_id).order_by('-pk')
	ret = []
	for s in facility_samples:
		if s.patient.hep_number not in ret:
			ret.append(s.patient.hep_number)
	return HttpResponse(json.dumps(ret))

def reverse_approval(request, verification_id):
	verification = Verification.objects.filter(pk=verification_id).first()
	sample = verification.sample
	ra = "Reverse approval failed"
	if sample.in_worksheet:
		ra = "Reverse approval not possible because the sample is already in a worksheet"
	else:
		if verification:
			sample.verified = False
			sample.save()
			verification.delete()
			ra = "Reverse approval successful"

	return redirect("/samples/search/?search_val=%s&approvals=1&reverse_approval=%s"%(request.GET.get("search_val"), ra))

@permission_required('samples.view_reports', login_url='/login/')
def download(request, path):
	report_type = (request.GET.get('type') or '').strip().lower()
	if request.GET.get('cohort'):
		folder = settings.MEDIA_ROOT
	elif report_type == 'hepb':
		folder = "hepb_reports"
	elif report_type == 'hepc':
		folder = "hepc_reports"
	elif report_type == 'vl':
		folder = "vl_reports"
	elif request.GET.get('dr'):
		folder = "reports/drug_resistance"
	elif request.GET.get('detectables'):
		folder = "reports/detectables"
	else:
		folder = "vl_reports"

	file_path = os.path.join(settings.MEDIA_ROOT, "%s/%s"%(folder,path))
	if os.path.exists(file_path):
		with open(file_path, 'rb') as fh:
			response = HttpResponse(fh.read(), content_type="application//x-zip-compressed")
			response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
			return response
	else:
		return HttpResponse("report missing")

@permission_required('samples.view_reports', login_url='/login/')
def reports(request):
	report_type = (request.GET.get('type') or '').strip().lower()
	if report_type == 'hepb':
		path = os.path.join(settings.MEDIA_ROOT, "hepb_reports/")
		report_title = 'HepB Reports'
		report_command = 'generate_hepb_report'
	elif report_type == 'hepc':
		path = os.path.join(settings.MEDIA_ROOT, "hepc_reports/")
		report_title = 'HepC Reports'
		report_command = 'generate_hepc_report'
	elif report_type == 'vl':
		path = os.path.join(settings.MEDIA_ROOT, "vl_reports/")
		report_title = 'VL Reports'
		report_command = 'generate_vl_report'
	elif request.GET.get('dr'):
		path = os.path.join(settings.MEDIA_ROOT, "reports/drug_resistance/")
		report_title = 'Drug Resistance Samples'
		report_command = ''
	elif request.GET.get('detectables'):
		path = os.path.join(settings.MEDIA_ROOT, "reports/detectables/")
		report_title = 'Detectable Samples'
		report_command = ''
	else:
		path = os.path.join(settings.MEDIA_ROOT, "vl_reports/")
		report_title = 'VL Reports'
		report_command = 'generate_vl_report'

	if request.method == 'POST' and report_command:
		call_command(report_command)
		return redirect('%s?type=%s&updated=1' % (request.path, report_type or 'vl'))

	reports = []
	for r in glob.glob("%s*.zip"%path):
		stats = os.stat(r)
		last_modified = datetime.fromtimestamp(stats.st_mtime)
		size = round(stats.st_size/1000000.0,1)
		report = os.path.basename(r)
		period = "%s, %s" %(calendar.month_abbr[int(report[4:6])], report[0:4])
		reports.append({'report':report, 'period':period, 'last_modified':last_modified, 'size':size})
	return render(request,'samples/reports.html', {'reports': reports, 'report_title': report_title, 'report_type': report_type, 'report_command': report_command})

class RejectionReasons(Appendix):
	"""docstring for RejectionReason"""
	data_quality = {}
	sample_quality = {}
	eligibility = {}
	rejection_reasons = {}

	def __init__(self, sample_type):
		for r in Appendix.objects.filter(appendix_category=4, tag__startswith=sample_type):
			if 'data_quality' in r.tag:
				self.data_quality.update({r.pk:r.appendix})
			elif 'sample_quality' in r.tag:
				self.sample_quality.update({r.pk:r.appendix})
			elif 'eligibility' in r.tag:
				self.eligibility.update({r.pk:r.appendix})

		self.rejection_reasons = json.dumps({
			'data_quality':self.data_quality,
			'sample_quality':self.sample_quality,
			'eligibility':self.eligibility})

def range_list(request):
	search_val = request.GET.get('search_val')
	return render(request, 'samples/range_list.html', {'global_search':search_val })

class RangeJson(BaseDatatableView):
	model = EnvelopeRange
	columns = ['year_month','lower_limit','upper_limit','sample_type','accessioned_by','accessioned_at','entered_by','links']
	order_columns = ['year_month','lower_limit','upper_limit']
	max_display_length = 500

	def render_column(self, row, column):
		if column == 'accessioned_by':
			return row.accessioned_by.first_name+' '+row.accessioned_by.last_name
		elif column == 'entered_by':
			return row.entered_by.first_name+' '+row.entered_by.last_name
		elif column == 'accessioned_at':
			return utils.set_page_date_only_format(row.accessioned_at)
		elif column =='links':
			links = utils.dropdown_links([
					{"label":"View envelopes","url":"/samples/range_envelopes/?type=1&range_id={0}".format(row.pk)},
					])
			return links

		else:
			return super(RangeJson, self).render_column(row, column)


	def filter_queryset(self, qs):
		search = self.request.GET.get(u'search[value]', None)
		global_search = self.request.GET.get('global_search', None)

		qs_params = Q()
		if search:
			qs_params = Q(year_month=search) | Q(lower_limit=search) | Q(upper_limit=search)
		return qs.filter(qs_params).order_by('year_month')

@transaction.atomic
def range_envelopes(request):

	if request.method == 'POST':
		envelope_ids = request.POST.getlist('envelope_ids')
		p_type = request.POST.getlist('type')
		processor = int(request.POST.get('accessioner_id'))
		assignment_type = int(request.POST.get('type'))
		for env_id in envelope_ids:
			envelope = Envelope.objects.get(pk=env_id)
			if p_type == '1':
				envelope.accessioned_at = datetime.now().date()
				envelope.accessioner_id = processor
				envelope.assignment_by = request.user
			else:
				envelope.processed_by_id = processor
				envelope.accessioned_at = datetime.now().date()
				envelope.lab_assignment_by = request.user
			envelope.save()

			env_assignment = EnvelopeAssignment()
			env_assignment.the_envelope = envelope
			env_assignment.assigned_to_id= processor
			env_assignment.type = assignment_type
			env_assignment.assigned_by = request.user
			env_assignment.save()
			if p_type == '1':
				return redirect('/samples/range_envelopes/?type=%s&range_id=%d' %(assignment_type,int(request.POST.get('range_id'))))
			else:
				return redirect('/samples/range_envelopes/?type=%s&wksht_id=%d' %(assignment_type,int(request.POST.get('wksht_id'))))

	else:
		users = utils.get_users()
		range_id = request.GET.get('range_id')
		wksht_id = request.GET.get('wksht_id')
		p_type = request.GET.get('type')
		if p_type == '1':
			envs = Envelope.objects.filter(envelope_range_id = int(range_id)).order_by('envelope_number')
		else:
			wksht_id = int(wksht_id)
			#envs = Envelope.objects.raw('SELECT envelope_number, e.id, processed_at FROM vl_worksheet_samples ws INNER JOIN vl_sample_identifiers si ON si.id = ws.sample_identifier_id INNER JOIN vl_envelopes e ON e.id = si.env_id INNER JOIN auth_user u ON u.id = e.processed_by_id WHERE ws.worksheet_id = %d GROUP BY e.id' %(wksht_id))
			envs = Envelope.objects.raw('select envelope_number, e.id from vl_worksheet_samples ws INNER JOIN vl_sample_identifiers s ON s.id = ws.sample_identifier_id and ws.worksheet_id = %d INNER JOIN vl_envelopes e ON e.id = s.env_id where ws.worksheet_id = %d GROUP BY e.id' %(wksht_id,wksht_id))

		page = request.GET.get('page', 1)
		paginator = Paginator(envs, 10)
		try:
			envelopes = paginator.page(page)
		except PageNotAnInteger:
			envelopes = paginator.page(1)
		except EmptyPage:
			envelopes = paginator.page(paginator.num_pages)
		context = {'envelopes':envelopes,'users':users}
		return render(request, 'samples/range_envelopes.html', context)

@transaction.atomic
def merge_envelopes(request):
	if request.method == 'POST':
		s_env = Envelope.objects.filter(envelope_number=request.POST.get('source_envelope')).first()
		d_env = Envelope.objects.filter(envelope_number=request.POST.get('destination_envelope')).first()
		if s_env.sample_type == d_env.sample_type:
			no_sourse_samples = Sample.objects.filter(envelope=s_env).count()
			no_destination_samples = Sample.objects.filter(envelope=s_env).count()
			#return HttpResponse(no_sourse_samples)
	#else:
	return render(request, 'samples/merge_envelopes.html')

@transaction.atomic
def receive_sample_only(request):

	saved_sample = request.GET.get('saved_sample')
	tracking_code, tr_code_id, current_tr_code = _get_tracking_context_from_request(request)
	env_id = request.GET.get('env_id')
	if current_tr_code is None:
		current_tr_code = ''
	if request.method == 'POST':
		if vl_services.is_hiv_program(request):
			try:
				sample = vl_services.receive_sample_only(request.POST, request.user)
				ret = {
					'saved_sample': sample.id,
					'env_id': sample.envelope_id,
					'tracking_code_id': sample.tracking_code_id,
					's_barcode': sample.barcode,
					'receipt_type': 'hie',
					'message_type': 'success',
					'err_msg': 'saved'
				}
				return HttpResponse(json.dumps(ret))
			except Exception as e:
				ret = {
					'saved_sample':'',
					'env_id':request.POST.get('envelope_id'),
					'tracking_code_id':request.POST.get('tracking_code_id'),
					's_barcode':request.POST.get('the_barcode', ''),
					'receipt_type':'hie',
					'message_type':'err',
					'err_msg':str(e)
				}
				return HttpResponse(json.dumps(ret))
		pst = request.POST
		sample_reception_form = SampleReceptionForm(pst)
		tr_code_id = request.POST.get('tracking_code_id')
		facility_reference = request.POST.get('facility_reference')
		facility_id = request.POST.get('facility')
		hep_number = request.POST.get('reception_hep_number')
		barcode = request.POST.get('the_barcode')
		env_id_raw = request.POST.get('envelope_id')
		try:
			env_id = int(env_id_raw)
		except (TypeError, ValueError):
			return HttpResponse(json.dumps({
				'saved_sample':'',
				'env_id':env_id_raw or '',
				'tracking_code_id':tr_code_id,
				's_barcode':barcode or '',
				'receipt_type':'hie',
				'message_type':'err',
				'err_msg':'Envelope was not found, did you accession it?'
			}))
		try:
			date_collected = posted_date(request.POST, 'date_collected')
		except ValidationError as e:
			return HttpResponse(json.dumps({
				'saved_sample':'',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':barcode or '',
				'receipt_type':'hie',
				'message_type':'err',
				'err_msg':str(e)
			}))
		required_message = ''
		if not barcode:
			required_message = 'Locator ID is required.'
		elif not facility_id:
			required_message = 'Facility is required.'
		elif not facility_reference:
			required_message = 'Facility identifier is required.'
		elif not hep_number:
			required_message = 'Hep number is required when the facility identifier is not found.'
		if required_message:
			return HttpResponse(json.dumps({
				'saved_sample':'',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':barcode or '',
				'receipt_type':'hie',
				'message_type':'err',
				'err_msg':required_message
			}))
		db_alias = get_dropdown_db_alias(request)
		session_program_code = get_session_program_code(request)
		mismatch_message = lock_envelope_to_session_program(request, env_id)
		if mismatch_message:
			ret = {
				'saved_sample':'',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':request.POST.get('the_barcode'),
				'receipt_type':'hie',
				'message_type':'err',
				'err_msg':mismatch_message
			}
			return HttpResponse(json.dumps(ret))
		sample = _find_existing_sample_for_reception(facility_reference, facility_id, db_alias=db_alias)
		tracking_code = _resolve_tracking_code_for_sample(
			sample,
			tr_code_id,
			request.POST.get('code'),
			request.user.id,
			facility_id,
			db_alias=db_alias,
		)
		if tracking_code is None:
			return HttpResponse(json.dumps({
				'saved_sample':'',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':request.POST.get('the_barcode'),
				'receipt_type':'hie',
				'message_type':'err',
				'err_msg':'Tracking code is required.'
			}))
		tr_code_id = tracking_code.id
		if _should_block_tracking_code_facility_mismatch(sample, tracking_code, facility_id):
			ret = {
				'saved_sample':'',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':request.POST.get('the_barcode'),
				'receipt_type':'hie',
				'message_type':'err',
				'err_msg':TRACKING_CODE_FACILITY_MISMATCH_MESSAGE
			}
			return HttpResponse(json.dumps(ret))
		saved_id = request.POST.get('saved_id')
		barcode_conflict = _get_received_barcode_conflict(request, barcode)
		if barcode_conflict and (sample is None or barcode_conflict.pk != sample.pk):
			return HttpResponse(json.dumps({
				'saved_sample': '',
				'env_id': env_id,
				'tracking_code_id': tr_code_id,
				's_barcode': barcode or '',
				'receipt_type': 'hie',
				'message_type': 'err',
				'err_msg': DUPLICATE_BARCODE_MESSAGE,
			}))
		if not saved_id and _sample_matches_tracking_code(sample, tracking_code):
			saved_id = sample.pk
		conflict_sample = _get_facility_reference_conflict(
			facility_reference,
			facility_id,
			saved_id,
			db_alias=db_alias,
		)
		if conflict_sample:
			ret = {
				'saved_sample':'',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':request.POST.get('the_barcode'),
				'receipt_type':'hie',
				'message_type':'err',
				'err_msg':DUPLICATE_FACILITY_REFERENCE_MESSAGE
			}
			return HttpResponse(json.dumps(ret))
		patient = sample.patient if sample else None
		sample_program_mismatch = get_program_mismatch_message(request, get_sample_program_code(sample), 'sample')
		if sample_program_mismatch:
			ret = {
				'saved_sample':'',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':request.POST.get('the_barcode'),
				'receipt_type':'hie',
				'message_type':'err',
				'err_msg':sample_program_mismatch
			}
			return HttpResponse(json.dumps(ret))
		if _sample_patient_facility_mismatch(sample, tracking_code, db_alias=db_alias):
			ret = {
				'saved_sample':'',
				'env_id':env_id,
				'tracking_code_id':tr_code_id,
				's_barcode':request.POST.get('the_barcode'),
				'receipt_type':'hie',
				'message_type':'err',
				'err_msg':TRACKING_CODE_SAMPLE_FACILITY_MISMATCH_MESSAGE
			}
			return HttpResponse(json.dumps(ret))
		if sample is None:
			if not request.POST.get('reception_hep_number'):
				ret = {
					'saved_sample':'',
					'env_id':env_id,
					'tracking_code_id':tr_code_id,
					's_barcode':request.POST.get('the_barcode'),
					'receipt_type':'hie',
					'message_type':'err',
					'err_msg':'Hep number is required when the facility identifier is not found.'
				}
				return HttpResponse(json.dumps(ret))
			sample = Sample()
			patient = Patient()

			patient.hep_number = request.POST.get('reception_hep_number')
			patient.facility_id = request.POST.get('facility')
			patient.created_by_id = request.user.id
			patient.save(using=db_alias)

			sample.reception_hep_number = request.POST.get('reception_hep_number')
			sample.facility_reference = facility_reference
			sample.form_number = facility_reference
			sample.facility_id = request.POST.get('facility')
			sample.created_by_id = request.user.id
			sample.received_by_id = request.user.id
			sample.date_received = datetime.now()
			sample.stage = 0
			sample.patient_id = patient.id
		if sample:
			#check if sample already received
			if sample.envelope_id:
				ret = {
						'saved_sample': sample.id,
						'env_id':env_id,
						'tracking_code_id':tr_code_id,
						's_barcode':request.POST.get('the_barcode'),
						'receipt_type':'hie',
						'message_type':'err',
						'err_msg':'already on '+sample.barcode
					}

				return HttpResponse(json.dumps(ret))

			#check if hep_numbers match
			if patient.hep_number is None:
				patient.hep_number = hep_number
				patient.save(using=db_alias)
			else:
				sanitized_input_art_no = utils.removeSpecialCharactersFromString(hep_number)
				sanitized_sample_art_no = utils.removeSpecialCharactersFromString(patient.hep_number)
				if sanitized_input_art_no != sanitized_sample_art_no:
					ret = {
						'saved_sample': sample.id,
						'env_id':env_id,
						'tracking_code_id':tr_code_id,
						's_barcode':request.POST.get('the_barcode'),
						'receipt_type':'hie',
						'message_type':'err',
						'err_msg':'miss match with '+patient.hep_number
					}
					return HttpResponse(json.dumps(ret))
		if not sample.tracking_code_id:
			sample.facility_id = facility_id
		sample.tracking_code_id = tr_code_id
		sample.locator_category = 'V'
		sample.envelope_id = env_id
		sample.verified = 1
		sample.is_data_entered = 1
		sample.only_sample_received = 1
		sample.required_verification = 0
		sample.stage = 0
		sample.received_by_id = request.user.id
		sample.locator_position=request.POST.get('the_position')
		sample.barcode=request.POST.get('the_barcode')
		_set_sample_type_from_request_or_envelope(sample, request, env_id)
		sample.date_collected = date_collected
		sample.date_received = datetime.now()
		if session_program_code:
			sample.program_code = session_program_code
		sample.save(using=db_alias)
		update_envelope_program_code(env_id, get_session_program_code(request))

		sample_utils.save_verification_details(sample,request)

		ret = {
			'saved_sample': sample.id,
			'env_id':env_id,
			'tracking_code_id':tr_code_id,
			's_barcode':sample.barcode,
			'receipt_type':'hie',
			'message_type':'success',
			'err_msg':'saved'
		}

		return HttpResponse(json.dumps(ret))

	else:
		d = datetime.now()
		sample_reception_form = SampleReceptionForm(initial=_sample_reception_initial(tracking_code), db_alias=get_dropdown_db_alias(request))
		envelope_samples = []
		if vl_services.is_hiv_program(request):
			envelope_samples = vl_services.get_envelope_samples(env_id)
		elif env_id:
			envelope = Envelope.objects.filter(pk=env_id).first()
			envelope_samples = envelope.sample_set.all().order_by('barcode') if envelope else []

		context = {
			'sample_reception_form': sample_reception_form,
			'tr_code_id': tr_code_id,
			'tracking_code_id': tr_code_id,
			'env_id':env_id,
			'current_tr_code':current_tr_code,
			'reception_id':'',
			'message_type':'',
			'envelope_samples': envelope_samples,
			'last_received_barcode': request.GET.get('last_barcode', ''),
		}

	if saved_sample:
		if vl_services.is_hiv_program(request):
			sample = vl_services.get_adapted_sample(saved_sample)
			envelope_samples = vl_services.get_envelope_samples(sample.envelope_id if sample else env_id)
			last_received_barcode = sample.barcode if sample and sample.barcode else request.GET.get('last_barcode', '')
			if sample and not tr_code_id and getattr(sample, 'tracking_code_id', None):
				tr_code_id = sample.tracking_code_id
			context.update({'sample':sample,'tr_code_id':tr_code_id,'tracking_code_id':tr_code_id,'env_id':env_id,'envelope_samples': envelope_samples,'last_received_barcode': last_received_barcode})
		else:
			db_alias = get_dropdown_db_alias(request)
			sample = Sample.objects.using(db_alias).filter(pk=saved_sample).first()
			if sample and not env_id and sample.envelope_id:
				env_id = sample.envelope_id
			if sample and not tr_code_id and sample.tracking_code_id:
				tracking_code = _get_existing_tracking_code(request, sample.tracking_code_id, '')
				if tracking_code:
					tr_code_id = tracking_code.id
					current_tr_code = current_tr_code or tracking_code.code
			initial = _sample_reception_initial(tracking_code)
			if sample and sample.facility_id and not initial.get('facility'):
				initial['facility'] = sample.facility_id
			sample_reception_form = SampleReceptionForm(initial=initial, db_alias=db_alias)
			envelope_samples = sample.envelope.sample_set.all().order_by('barcode') if sample and sample.envelope_id else []
			last_received_barcode = sample.barcode if sample and sample.barcode else request.GET.get('last_barcode', '')
			context.update({'sample_reception_form': sample_reception_form,'sample':sample,'tr_code_id':tr_code_id,'tracking_code_id':tr_code_id,'env_id':env_id,'current_tr_code': current_tr_code,'envelope_samples': envelope_samples,'last_received_barcode': last_received_barcode})
	context.update(_receive_batch_tracking_context(tracking_code))

	return render(request, 'samples/receive_sample_only.html', context)

@permission_required('results.add_resultsqc', login_url='/login/')
def release_sample_only_results(request):
	if request.method == 'POST':

		search_string = request.POST.get('search_string', '')  # e.g., '2504-5015,2504-5016' or '2504-5015'

		# Split into list and remove whitespace (if any)
		envelope_numbers = [num.strip() for num in search_string.split(',') if num.strip()]

		samples = Sample.objects.select_related('envelope').filter(envelope__envelope_number__in=envelope_numbers)
		with transaction.atomic():
			for sample in samples:
				print(sample)
				if not sample.patient_id:
					# Create a new patient
					patient = Patient.objects.create(facility_id=sample.facility_id,hep_number=sample.reception_hep_number,created_by_id = sample.created_by_id)
					# Assign the new patient to the sample
					sample.patient = patient
					sample.only_sample_received = 1
					sample.is_data_entered = 1
					sample.verified = 1
					sample.save()
					sample_utils.save_verification_details(sample,request)
				if hasattr(sample, 'result') and sample.result:
					rqc = sample.result.resultsqc
					if not rqc.released:
						other_params = {
							'released': True,
							'comments': 'manual',
							'released_by_id': request.user.id,
							'released_at': datetime.now(),
						}
						rqc, rqc_created = ResultsQC.objects.update_or_create(result=sample.result, defaults=other_params)
		return redirect('/samples/release_sample_only_results/')

	else:

		return render(request, 'samples/release_sample_only_resuts.html')

def download_envelope_results(request):
	samples_without_results = Sample.objects.filter(envelope_id=request.GET.get('env_id'))

		# Create CSV response
	response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="samples_with_results.csv"'},
        )
	writer = csv.writer(response)
	# Write header
	writer.writerow([
        'Facility Ref',
		'Lab Ref',
		'Facility',
		'District',
		'Patient ART #',
		'Date of Birth',
		'Sex',
		'current Regimen',
		'Result',
		'Test Date'
        # Add other sample fields you want to export
    ])

	# Write data
	for sample in samples_without_results:
		if sample.patient_id:
			fac = sample.patient.facility
			dist = sample.patient.facility.district
			art_no = sample.patient.hep_number
			dob = sample.patient.dob
			sex = sample.patient.gender

		else:
			fac = sample.facility
			dist = ''
			art_no = s.reception_hep_number
			dob = ''
			sex = ''

		writer.writerow([
            sample.facility_reference,
            sample.barcode,
            fac,
            dist,
            art_no,
            dob,
            sex,
            sample.current_regimen,
            result_utils.format_result_for_display(sample.result),
            sample.result.test_date
            # Add other sample fields
        ])
	return response


def dr_list(request):
	return render(request, 'samples/dr_list.html', {
		'dr_box_prefix': _current_dr_box_prefix(),
	})


@transaction.atomic
def archival_samples(request):
	saved_box = request.GET.get('saved_box')
	context = {
		'dr_box_prefix': _current_dr_box_prefix(),
	}
	if request.method == 'POST':
		box_number = (request.POST.get('box_number') or '').strip()
		sample_type = (request.POST.get('sample_type') or '').strip()
		try:
			starting_position = int(request.POST.get('starting_position', '0'))
		except (TypeError, ValueError):
			starting_position = 0
		try:
			number_of_samples = int(request.POST.get('number_of_samples', '0'))
		except (TypeError, ValueError):
			number_of_samples = 0

		box_positions = request.POST.getlist('box_position[]')
		barcodes = request.POST.getlist('barcode[]')
		hep_numbers = request.POST.getlist('hep_number[]')

		try:
			box_number = _normalize_dr_box_number(box_number)
		except ValueError as exc:
			context['error_message'] = str(exc)
			return render(request, 'samples/archival_samples.html', context)

		if sample_type not in ['P', 'D'] or number_of_samples < 1 or number_of_samples > 100 or starting_position < 1:
			context['error_message'] = 'Enter a valid box number, sample type, starting position, and number of samples.'
		elif len(box_positions) != number_of_samples or len(barcodes) != number_of_samples:
			context['error_message'] = 'Generated rows do not match the number of samples.'
		elif starting_position + number_of_samples - 1 > 100:
			context['error_message'] = 'A box can contain a maximum of 100 samples.'
		else:
			archival_envelope, created = ArchivalEnvelope.objects.get_or_create(
				box_number=box_number,
				defaults={
					'sample_type': sample_type,
					'date_archived': datetime.now().date(),
				}
			)
			if not created and archival_envelope.sample_type != sample_type:
				context['error_message'] = 'This box already exists with a different sample type.'
				return render(request, 'samples/archival_samples.html', context)
			normalized_positions = []
			try:
				for raw_position in box_positions:
					_, normalized_position = _normalize_dr_box_position(raw_position, archival_envelope.box_number)
					normalized_positions.append(normalized_position)
			except ValueError as exc:
				context['error_message'] = str(exc)
				return render(request, 'samples/archival_samples.html', context)
			occupied_positions = set(
				DrugResistanceRequest.objects.filter(archival_envelope=archival_envelope).values_list('box_position', flat=True)
			)
			if any(position in occupied_positions for position in normalized_positions):
				context['error_message'] = 'One or more positions are already saved on this box.'
				return render(request, 'samples/archival_samples.html', context)
			if len(set(normalized_positions)) != len(normalized_positions):
				context['error_message'] = 'Box positions must be unique.'
				return render(request, 'samples/archival_samples.html', context)
			for index in range(number_of_samples):
				barcode = (barcodes[index] or '').strip()
				hep_number = (hep_numbers[index] or '').strip() if index < len(hep_numbers) else ''
				box_position = normalized_positions[index]
				sample = None
				if barcode:
					sample = Sample.objects.filter(
						Q(barcode2=barcode) | Q(facility_reference=barcode)
					).first()

				if sample:
					dr_request = DrugResistanceRequest.objects.filter(sample=sample).first()
					if dr_request is None:
						dr_request = DrugResistanceRequest(sample=sample)
					dr_request.barcode = sample.barcode2 or barcode
				else:
					dr_request = DrugResistanceRequest.objects.filter(sample__isnull=True, barcode=barcode).first()
					if dr_request is None:
						dr_request = DrugResistanceRequest(barcode=barcode)
				dr_request.archival_envelope = archival_envelope
				dr_request.hep_number = hep_number or getattr(getattr(sample, 'patient', None), 'hep_number', '')
				dr_request.box_position = box_position
				dr_request.level_identified_at = 1
				dr_request.save()
			return redirect('/samples/archival_samples/?saved_box={0}'.format(archival_envelope.pk))

	if saved_box:
		context['saved_box'] = ArchivalEnvelope.objects.filter(pk=saved_box).first()
		if context['saved_box']:
			context['saved_box_requests'] = DrugResistanceRequest.objects.filter(
				archival_envelope=context['saved_box']
			).order_by('box_position', 'id')
	return render(request, 'samples/archival_samples.html', context)


def archival_box_positions(request):
	box_number = (request.GET.get('box_number') or '').strip()
	ret = {'exists': False, 'positions': [], 'entries': []}
	if box_number:
		archival_envelope = ArchivalEnvelope.objects.filter(box_number=box_number).first()
		if archival_envelope:
			requests = DrugResistanceRequest.objects.filter(
				archival_envelope=archival_envelope
			).order_by('box_position', 'id')
			ret['exists'] = True
			ret['positions'] = builtins.list(
				requests.filter(
					box_position__isnull=False,
				).exclude(box_position='').values_list('box_position', flat=True)
			)
			ret['entries'] = [
				{
					'box_position': dr_request.box_position or '',
					'barcode': dr_request.barcode or '',
					'hep_number': dr_request.hep_number or '',
				}
				for dr_request in requests
			]
	return JsonResponse(ret)


def _apply_dr_level_filter(qs, request):
	level_identified_at = (request.GET.get('level_identified_at') or '').strip()
	if level_identified_at in ['1', '2']:
		qs = qs.filter(level_identified_at=int(level_identified_at))
	return qs


def _dr_samples_queryset(request):
	return _apply_dr_level_filter(
		DrugResistanceRequest.objects.select_related(
			'sample',
			'sample__patient',
			'sample__facility',
			'sample__envelope',
		).filter(
			Q(sample__envelope__sample_medical_lab=utils.user_lab(request)) | Q(sample__isnull=True)
		).filter(
			archival_envelope__isnull=False
		).distinct(),
		request,
	)


def _dr_pending_decision_queryset(request):
	return _apply_dr_level_filter(
		DrugResistanceRequest.objects.select_related(
			'sample',
			'sample__patient',
			'sample__facility',
			'sample__envelope',
			'sample__result',
		).filter(
			archival_envelope__isnull=False,
			sample__isnull=False,
			decision__isnull=True,
			sample__envelope__sample_medical_lab=utils.user_lab(request),
		),
		request,
	)


def _dr_requests_without_sample_queryset(request):
	return _apply_dr_level_filter(
		DrugResistanceRequest.objects.filter(
			archival_envelope__isnull=False,
			sample__isnull=True,
		),
		request,
	)


def _lab_archival_queryset(request):
	qs = Sample.objects.select_related(
		'patient',
		'facility',
		'envelope',
		'result',
		'result__resultsqc',
	).filter(
		verified=True,
		result__resultsqc__released=True,
		result__result_numeric__gt=1000,
		envelope__sample_medical_lab=utils.user_lab(request),
		drugresistancerequest__isnull=True,
	)
	envelope_number = (request.GET.get('envelope_number') or '').strip()
	barcode = (request.GET.get('barcode') or '').strip()
	facility_reference = (request.GET.get('facility_reference') or '').strip()
	if envelope_number:
		qs = qs.filter(envelope__envelope_number__icontains=envelope_number)
	if barcode:
		qs = qs.filter(barcode__icontains=barcode)
	if facility_reference:
		qs = qs.filter(facility_reference__icontains=facility_reference)
	return qs


def dr_samples_json(request):
	r = request.GET
	start = int(r.get('start', 0))
	length = int(r.get('length', 10))
	search = (r.get(u'search[value]', '') or '').strip()

	qs = _dr_samples_queryset(request)
	records_total = qs.count()

	if search:
		qs = qs.filter(
			Q(barcode__icontains=search) |
			Q(sample__barcode__icontains=search) |
			Q(sample__form_number__icontains=search) |
			Q(sample__facility_reference__icontains=search) |
			Q(sample__patient__hep_number__icontains=search)
		)

	records_filtered = qs.count()
	qs = qs.order_by('-created_at')[start:start+length]

	data = []
	for dr_request in qs:
		sample = dr_request.sample
		patient = sample.patient if sample else None
		decision = dr_request.get_decision_display() if dr_request.decision else ''
		data.append([
			dr_request.barcode or (sample.barcode2 if sample else '') or '',
			sample.barcode if sample else '',
			sample.form_number if sample else '',
			sample.facility_reference if sample else '',
			sample.get_sample_type_display() if sample and sample.sample_type else '',
			sample.facility.facility if sample and sample.facility else '',
			patient.hep_number if patient else '',
			decision,
			"<a href='/samples/edit/{0}'>view</a>".format(sample.pk) if sample else '',
		])

	return HttpResponse(json.dumps({
		"draw": r.get('draw'),
		"recordsTotal": records_total,
		"recordsFiltered": records_filtered,
		"data": data,
	}))


def dr_pending_decision_json(request):
	r = request.GET
	start = int(r.get('start', 0))
	length = int(r.get('length', 10))
	search = (r.get(u'search[value]', '') or '').strip()

	qs = _dr_pending_decision_queryset(request)
	records_total = qs.count()

	if search:
		qs = qs.filter(
			Q(barcode__icontains=search) |
			Q(sample__barcode__icontains=search) |
			Q(sample__form_number__icontains=search) |
			Q(sample__facility_reference__icontains=search) |
			Q(sample__patient__hep_number__icontains=search)
		)

	records_filtered = qs.count()
	qs = qs.order_by('-created_at')[start:start+length]

	data = []
	for dr_request in qs:
		sample = dr_request.sample
		patient = sample.patient if sample else None
		result_value = result_utils.format_result_for_display(sample.result) if sample and hasattr(sample, 'result') and sample.result else ''
		data.append([
			dr_request.barcode or (sample.barcode2 if sample else '') or '',
			sample.barcode if sample else '',
			sample.form_number if sample else '',
			sample.facility_reference if sample else '',
			sample.get_sample_type_display() if sample and sample.sample_type else '',
			sample.facility.facility if sample and sample.facility else '',
			patient.hep_number if patient else '',
			result_value,
			'Pending',
			"<a href='#' class='decide-dr-request' data-dr-request='{0}'>Decide</a> | <a href='/samples/edit/{1}'>view</a>".format(dr_request.pk, sample.pk) if sample else '',
		])

	return HttpResponse(json.dumps({
		"draw": r.get('draw'),
		"recordsTotal": records_total,
		"recordsFiltered": records_filtered,
		"data": data,
	}))


def dr_requests_without_sample_json(request):
	r = request.GET
	start = int(r.get('start', 0))
	length = int(r.get('length', 10))
	search = (r.get(u'search[value]', '') or '').strip()

	qs = _dr_requests_without_sample_queryset(request)
	records_total = qs.count()
	if search:
		qs = qs.filter(Q(barcode__icontains=search))
	records_filtered = qs.count()
	qs = qs.order_by('-created_at')[start:start+length]

	data = []
	for dr_request in qs:
		data.append([
			dr_request.barcode or '',
			dr_request.get_decision_display() if dr_request.decision else '',
			utils.local_datetime(dr_request.created_at),
			"<a href='#' class='attach-dr-sample' data-dr-request='{0}'>Attach sample</a>".format(dr_request.pk),
		])
	return HttpResponse(json.dumps({
		"draw": r.get('draw'),
		"recordsTotal": records_total,
		"recordsFiltered": records_filtered,
		"data": data,
	}))


def lab_archival_json(request):
	r = request.GET
	start = int(r.get('start', 0))
	length = int(r.get('length', 10))
	qs = _lab_archival_queryset(request)
	records_total = qs.count()
	records_filtered = records_total
	qs = qs.order_by('barcode')[start:start+length]

	data = []
	for sample in qs:
		patient = sample.patient
		data.append([
			sample.envelope.envelope_number if sample.envelope else '',
			sample.barcode or '',
			sample.form_number or '',
			sample.facility_reference or '',
			sample.get_sample_type_display() if sample.sample_type else '',
			sample.facility.facility if sample.facility else '',
			patient.hep_number if patient else '',
			result_utils.format_result_for_display(sample.result) if sample.result else '',
			"<input type='text' class='form-control input-sm lab-archival-box-position' data-sample='{0}' placeholder='300001'>".format(sample.pk),
			"<a href='#' class='save-lab-archival' data-sample='{0}'>Save</a>".format(sample.pk),
		])
	return HttpResponse(json.dumps({
		"draw": r.get('draw'),
		"recordsTotal": records_total,
		"recordsFiltered": records_filtered,
		"data": data,
	}))


@transaction.atomic
def create_dr_request(request):
	if request.method != 'POST':
		return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
	barcode = (request.POST.get('barcode') or '').strip()
	if not barcode:
		return JsonResponse({'success': False, 'message': 'DR barcode is required.'}, status=400)
	try:
		barcode = _normalize_dr_box_number(barcode)
	except ValueError as exc:
		return JsonResponse({'success': False, 'message': str(exc)}, status=400)
	if DrugResistanceRequest.objects.filter(barcode=barcode).exists():
		return JsonResponse({'success': False, 'message': 'DR barcode already exists.'}, status=400)
	dr_request = DrugResistanceRequest.objects.create(barcode=barcode)
	return JsonResponse({'success': True, 'id': dr_request.pk})


@transaction.atomic
def attach_dr_sample(request, dr_request_id):
	if request.method != 'POST':
		return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
	dr_request = get_object_or_404(DrugResistanceRequest, pk=dr_request_id)
	search_value = (request.POST.get('barcode') or '').strip()
	if not search_value:
		return JsonResponse({'success': False, 'message': 'Barcode is required.'}, status=400)
	sample = Sample.objects.filter(
		Q(barcode=search_value) |
		Q(form_number=search_value) |
		Q(facility_reference=search_value)
	).first()
	if sample is None:
		return JsonResponse({'success': False, 'message': 'Sample not found.'}, status=404)
	existing_dr_request = DrugResistanceRequest.objects.filter(sample=sample).exclude(pk=dr_request.pk).first()
	if existing_dr_request:
		return JsonResponse({'success': False, 'message': 'Sample is already attached to another DR request.'}, status=400)
	dr_request.sample = sample
	if not dr_request.barcode:
		dr_request.barcode = sample.barcode2 or sample.barcode
	dr_request.hep_number = getattr(sample.patient, 'hep_number', '') or dr_request.hep_number
	dr_request.save()
	return JsonResponse({'success': True, 'sample_id': sample.pk})


@transaction.atomic
def decide_dr_request(request, dr_request_id):
	if request.method != 'POST':
		return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
	dr_request = get_object_or_404(DrugResistanceRequest, pk=dr_request_id)
	try:
		decision = int(request.POST.get('decision'))
	except (TypeError, ValueError):
		return JsonResponse({'success': False, 'message': 'Decision is required.'}, status=400)
	if decision not in [1, 2]:
		return JsonResponse({'success': False, 'message': 'Invalid decision.'}, status=400)
	dr_request.decision = decision
	dr_request.save(update_fields=['decision'])
	return JsonResponse({'success': True})


@transaction.atomic
def save_lab_archival(request, sample_id):
	if request.method != 'POST':
		return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
	sample = get_object_or_404(Sample.objects.select_related('patient', 'result', 'result__resultsqc'), pk=sample_id)
	try:
		box_number, box_position = _normalize_dr_box_position(request.POST.get('box_position'))
	except ValueError as exc:
		return JsonResponse({'success': False, 'message': str(exc)}, status=400)
	if sample.result is None or sample.result.result_numeric is None or sample.result.result_numeric <= 1000:
		return JsonResponse({'success': False, 'message': 'Sample does not qualify for lab archival.'}, status=400)
	if not hasattr(sample.result, 'resultsqc') or not sample.result.resultsqc.released:
		return JsonResponse({'success': False, 'message': 'Sample result has not been released.'}, status=400)
	archival_envelope, created = ArchivalEnvelope.objects.get_or_create(
		box_number=box_number,
		defaults={'sample_type': sample.sample_type, 'date_archived': datetime.now().date()}
	)
	if not created and archival_envelope.sample_type != sample.sample_type:
		return JsonResponse({'success': False, 'message': 'This box already exists with a different sample type.'}, status=400)
	if DrugResistanceRequest.objects.exclude(sample=sample).filter(archival_envelope=archival_envelope, box_position=box_position).exists():
		return JsonResponse({'success': False, 'message': 'This box position is already used.'}, status=400)
	dr_request, _ = DrugResistanceRequest.objects.update_or_create(
		sample=sample,
		defaults={
			'archival_envelope': archival_envelope,
			'barcode': sample.barcode2 or sample.barcode,
			'hep_number': getattr(sample.patient, 'hep_number', '') or '',
			'box_position': box_position,
			'level_identified_at': 2,
		}
	)
	return JsonResponse({'success': True, 'id': dr_request.pk})


def dr_list_export(request):
	tab = (request.GET.get('tab') or 'pending').strip()
	workbook = openpyxl.Workbook()
	sheet = workbook.active
	sheet.title = 'DR Samples'
	if tab == 'without_sample':
		sheet.append(['DR Barcode', 'Decision', 'Level Identified At', 'Created At'])
		qs = _dr_requests_without_sample_queryset(request).order_by('-created_at')
		search = (request.GET.get('search') or '').strip()
		if search:
			qs = qs.filter(barcode__icontains=search)
		for dr_request in qs:
			sheet.append([dr_request.barcode or '', dr_request.get_decision_display() if dr_request.decision else '', dr_request.get_level_identified_at_display() if dr_request.level_identified_at else '', utils.local_datetime(dr_request.created_at)])
	elif tab == 'lab_archival':
		sheet.append(['Envelope', 'Lab Barcode', 'Form Number', 'Facility Ref', 'Sample Type', 'Facility', 'Hep Number', 'Result'])
		for sample in _lab_archival_queryset(request).order_by('barcode'):
			sheet.append([
				sample.envelope.envelope_number if sample.envelope else '',
				sample.barcode or '',
				sample.form_number or '',
				sample.facility_reference or '',
				sample.get_sample_type_display() if sample.sample_type else '',
				sample.facility.facility if sample.facility else '',
				sample.patient.hep_number if sample.patient else '',
				result_utils.format_result_for_display(sample.result) if sample.result else '',
			])
	elif tab == 'all':
		sheet.append(['DR Barcode', 'Lab Barcode', 'Form Number', 'Facility Ref', 'Sample Type', 'Facility', 'Hep Number', 'Decision', 'Level Identified At'])
		qs = _dr_samples_queryset(request).order_by('-created_at')
		search = (request.GET.get('search') or '').strip()
		if search:
			qs = qs.filter(Q(barcode__icontains=search) | Q(sample__barcode__icontains=search) | Q(sample__form_number__icontains=search) | Q(sample__facility_reference__icontains=search) | Q(sample__patient__hep_number__icontains=search))
		for dr_request in qs:
			sample = dr_request.sample
			patient = sample.patient if sample else None
			sheet.append([dr_request.barcode or (sample.barcode2 if sample else '') or '', sample.barcode if sample else '', sample.form_number if sample else '', sample.facility_reference if sample else '', sample.get_sample_type_display() if sample and sample.sample_type else '', sample.facility.facility if sample and sample.facility else '', patient.hep_number if patient else '', dr_request.get_decision_display() if dr_request.decision else '', dr_request.get_level_identified_at_display() if dr_request.level_identified_at else ''])
	else:
		sheet.append(['DR Barcode', 'Lab Barcode', 'Form Number', 'Facility Ref', 'Sample Type', 'Facility', 'Hep Number', 'Result', 'Decision', 'Level Identified At'])
		qs = _dr_pending_decision_queryset(request).order_by('-created_at')
		search = (request.GET.get('search') or '').strip()
		if search:
			qs = qs.filter(Q(barcode__icontains=search) | Q(sample__barcode__icontains=search) | Q(sample__form_number__icontains=search) | Q(sample__facility_reference__icontains=search) | Q(sample__patient__hep_number__icontains=search))
		for dr_request in qs:
			sample = dr_request.sample
			patient = sample.patient if sample else None
			sheet.append([dr_request.barcode or (sample.barcode2 if sample else '') or '', sample.barcode if sample else '', sample.form_number if sample else '', sample.facility_reference if sample else '', sample.get_sample_type_display() if sample and sample.sample_type else '', sample.facility.facility if sample and sample.facility else '', patient.hep_number if patient else '', result_utils.format_result_for_display(sample.result) if sample and hasattr(sample, 'result') and sample.result else '', dr_request.get_decision_display() if dr_request.decision else 'Pending', dr_request.get_level_identified_at_display() if dr_request.level_identified_at else ''])
	output = io.BytesIO()
	workbook.save(output)
	output.seek(0)
	response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
	response['Content-Disposition'] = 'attachment; filename="dr_list_export.xlsx"'
	return response
