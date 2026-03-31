from datetime import datetime
from types import SimpleNamespace

import pandas
from django.contrib.auth.models import User
from django.db import connections
from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from home import programs, utils
from samples import utils as sample_utils
from backend.models import Facility
from results import utils as result_utils

from .models import VLEnvelope, VLEnvelopeAssignment, VLEnvelopeRange, VLPatient, VLResult, VLResultRun, VLResultRunDetail, VLResultsQC, VLSample, VLTrackingCode, VLVerification, VLWorksheet, VLWorksheetSample


def is_hiv_program(request):
	return programs.get_active_program_code(request) == '3'


def get_vl_user_id(user):
	if not isinstance(user, User):
		return None
	with connections['default'].cursor() as cursor:
		cursor.execute("SELECT vl_id FROM auth_user WHERE id = %s", [user.id])
		row = cursor.fetchone()
	return row[0] if row and row[0] else None


def _parse_date(value):
	if not value:
		return None
	return utils.get_mysql_from_uk_date(value)


def _parse_int(value):
	if value in (None, ''):
		return None
	try:
		return int(value)
	except (TypeError, ValueError):
		return None


def _envelope_number_from_barcode(barcode):
	if barcode and len(barcode) >= 8 and barcode[:8].isdigit():
		return "%s-%s" % (barcode[:4], barcode[4:8])
	return None


def _sync_legacy_envelope(legacy_envelope, sample_type=None):
	if legacy_envelope is None:
		return None

	envelope = VLEnvelope.objects.using('vl_lims').filter(envelope_number=legacy_envelope.envelope_number).first()
	if envelope is None:
		envelope = VLEnvelope(envelope_number=legacy_envelope.envelope_number)

	envelope.sample_type = sample_type or legacy_envelope.sample_type or envelope.sample_type or ''
	envelope.stage = legacy_envelope.stage or envelope.stage or 2
	envelope.is_received = bool(legacy_envelope.is_received) if legacy_envelope.is_received is not None else envelope.is_received
	envelope.is_data_entered = bool(legacy_envelope.is_data_entered) if legacy_envelope.is_data_entered is not None else envelope.is_data_entered
	envelope.is_lab_completed = legacy_envelope.is_lab_completed if legacy_envelope.is_lab_completed is not None else envelope.is_lab_completed
	envelope.has_result = bool(legacy_envelope.has_result) if legacy_envelope.has_result is not None else envelope.has_result
	envelope.sample_medical_lab_id = legacy_envelope.sample_medical_lab_id or envelope.sample_medical_lab_id
	envelope.accessioner_id = legacy_envelope.accessioner_id or envelope.accessioner_id
	envelope.accessioned_at = legacy_envelope.accessioned_at or envelope.accessioned_at
	envelope.processed_by_id = legacy_envelope.processed_by_id or envelope.processed_by_id
	envelope.processed_at = legacy_envelope.processed_at or envelope.processed_at
	envelope.envelope_range_id = legacy_envelope.envelope_range_id or envelope.envelope_range_id
	envelope.assignment_by_id = legacy_envelope.assignment_by_id or envelope.assignment_by_id
	envelope.lab_assignment_by_id = legacy_envelope.lab_assignment_by_id or envelope.lab_assignment_by_id
	envelope.save(using='vl_lims')
	return envelope


def _get_envelope_from_legacy(envelope_id=None, envelope_number=None, sample_type=None):
	from samples.models import Envelope as LegacyEnvelope

	legacy_envelope = None
	if envelope_id:
		legacy_envelope = LegacyEnvelope.objects.filter(pk=envelope_id).first()
	if legacy_envelope is None and envelope_number:
		legacy_envelope = LegacyEnvelope.objects.filter(envelope_number=envelope_number).first()
	return _sync_legacy_envelope(legacy_envelope, sample_type=sample_type)


def _resolve_envelope(post_data):
	envelope_id = _parse_int(post_data.get('envelope_id'))
	if envelope_id:
		envelope = VLEnvelope.objects.using('vl_lims').filter(pk=envelope_id).first()
		if envelope:
			return envelope
		envelope = _get_envelope_from_legacy(envelope_id=envelope_id, sample_type=post_data.get('sample_type'))
		if envelope:
			return envelope

	envelope_number = (post_data.get('envelope_number') or '').strip()
	if not envelope_number:
		envelope_number = _envelope_number_from_barcode(post_data.get('the_barcode') or post_data.get('barcode'))
	if envelope_number:
		envelope = VLEnvelope.objects.using('vl_lims').filter(envelope_number=envelope_number).first()
		if envelope:
			return envelope
		return _get_envelope_from_legacy(envelope_number=envelope_number, sample_type=post_data.get('sample_type'))
	return None


def _resolve_medical_lab_id(user):
	try:
		return user.userprofile.medical_lab_id
	except Exception:
		return None


def _facility_obj(facility_id):
	if not facility_id:
		return None
	return Facility.objects.filter(pk=facility_id).select_related('district').first()


def _sample_display(sample_type):
	return 'Plasma' if sample_type == 'P' else 'DBS' if sample_type == 'D' else sample_type


def save_sample_form(post_data, user):
	vl_user_id = get_vl_user_id(user)
	if not vl_user_id:
		raise ValueError("Current user has no vl_id mapping in hepb.auth_user")

	now = datetime.now()
	barcode = post_data.get('barcode')
	sample_type = post_data.get('sample_type')
	facility_id = _parse_int(post_data.get('facility'))
	medical_lab_id = _resolve_medical_lab_id(user)
	envelope_number = (post_data.get('envelope_number') or '').strip()
	art_number = (post_data.get('hep_number') or '').strip()
	sanitized_art_number = utils.removeSpecialCharactersFromString(art_number) if art_number else None
	unique_id = f"{facility_id}-A-{sanitized_art_number}" if facility_id and sanitized_art_number else None

	envelope = VLEnvelope.objects.using('vl_lims').filter(envelope_number=envelope_number).first()
	if envelope is None:
		envelope = VLEnvelope(
			envelope_number=envelope_number,
			sample_type=sample_type,
			sample_medical_lab_id=medical_lab_id,
			is_data_entered=True,
			is_received=True,
			stage=2,
		)
		envelope.save(using='vl_lims')

	patient = VLPatient.objects.using('vl_lims').filter(unique_id=unique_id).first()
	if patient is None:
		patient = VLPatient(
			unique_id=unique_id,
			art_number=art_number or None,
			sanitized_art_number=sanitized_art_number,
			other_id=post_data.get('other_id') or None,
			gender=post_data.get('gender') or None,
			dob=_parse_date(post_data.get('dob')),
			facility_id=facility_id,
			treatment_initiation_date=_parse_date(post_data.get('treatment_initiation_date')),
			current_regimen_initiation_date=_parse_date(post_data.get('current_regimen_initiation_date')),
			treatment_duration=_parse_int(post_data.get('treatment_duration')),
			created_by_id=vl_user_id,
			is_verified=True,
		)
		patient.save(using='vl_lims')
		if not patient.parent_id:
			patient.parent_id = patient.id
			patient.save(using='vl_lims')
	else:
		patient.art_number = art_number or patient.art_number
		patient.sanitized_art_number = sanitized_art_number or patient.sanitized_art_number
		patient.other_id = post_data.get('other_id') or patient.other_id
		patient.gender = post_data.get('gender') or patient.gender
		patient.dob = _parse_date(post_data.get('dob')) or patient.dob
		patient.facility_id = facility_id or patient.facility_id
		patient.treatment_initiation_date = _parse_date(post_data.get('treatment_initiation_date')) or patient.treatment_initiation_date
		patient.current_regimen_initiation_date = _parse_date(post_data.get('current_regimen_initiation_date')) or patient.current_regimen_initiation_date
		patient.treatment_duration = _parse_int(post_data.get('treatment_duration')) or patient.treatment_duration
		patient.save(using='vl_lims')

	sample = VLSample.objects.using('vl_lims').filter(barcode=barcode).first()
	if sample is None and post_data.get('form_number'):
		sample = VLSample.objects.using('vl_lims').filter(form_number=post_data.get('form_number')).first()

	if sample is None:
		sample = VLSample(
			created_by_id=vl_user_id,
			date_received=now,
		)

	sample.patient_id = patient.id
	sample.patient_unique_id = patient.unique_id
	sample.locator_category = post_data.get('locator_category') or 'V'
	sample.locator_position = post_data.get('locator_position') or sample.locator_position or ''
	sample.barcode = barcode
	sample.form_number = post_data.get('form_number') or barcode
	sample.facility_id = facility_id
	sample.data_facility_id = facility_id
	sample.envelope_id = envelope.id
	sample.sample_type = sample_type
	sample.date_collected = _parse_date(post_data.get('date_collected'))
	sample.treatment_initiation_date = _parse_date(post_data.get('treatment_initiation_date'))
	sample.current_regimen_initiation_date = _parse_date(post_data.get('current_regimen_initiation_date'))
	sample.treatment_duration = _parse_int(post_data.get('treatment_duration'))
	sample.current_regimen_id = _parse_int(post_data.get('current_regimen'))
	sample.other_regimen = post_data.get('other_regimen') or None
	sample.pregnant = post_data.get('pregnant') or None
	sample.anc_number = post_data.get('anc_number') or None
	sample.breast_feeding = post_data.get('breast_feeding') or None
	sample.consented_sample_keeping = post_data.get('consented_sample_keeping') or None
	sample.active_tb_status = post_data.get('active_tb_status') or None
	sample.current_who_stage = _parse_int(post_data.get('current_who_stage'))
	sample.treatment_indication_id = _parse_int(post_data.get('treatment_indication'))
	sample.treatment_indication_other = post_data.get('treatment_indication_other') or None
	sample.failure_reason_id = _parse_int(post_data.get('failure_reason'))
	sample.tb_treatment_phase_id = _parse_int(post_data.get('tb_treatment_phase'))
	sample.arv_adherence_id = _parse_int(post_data.get('arv_adherence'))
	sample.treatment_care_approach = _parse_int(post_data.get('treatment_care_approach'))
	sample.last_test_date = _parse_date(post_data.get('last_test_date'))
	sample.last_value = post_data.get('last_value') or None
	sample.last_sample_type = post_data.get('last_sample_type') or None
	sample.reception_art_number = art_number or None
	sample.data_art_number = post_data.get('data_hep_number') or art_number or None
	sample.viral_load_testing_id = _parse_int(post_data.get('viral_load_testing'))
	sample.updated_by_id = vl_user_id
	sample.data_entered_by_id = vl_user_id
	sample.data_entered_at = now
	sample.verifier_id = vl_user_id
	sample.verified_at = now
	sample.received_by_id = vl_user_id
	sample.verified = True
	sample.required_verification = False
	sample.is_data_entered = True
	sample.medical_lab_id = medical_lab_id
	sample.facility_reference = post_data.get('facility_reference') or None
	sample.is_study_sample = bool(post_data.get('is_study_sample'))
	sample.stage = 0
	sample.save(using='vl_lims')

	verification = VLVerification.objects.using('vl_lims').filter(sample_id=sample.id).first()
	if verification is None:
		verification = VLVerification(sample_id=sample.id, verified_by_id=vl_user_id)
	verification.accepted = True
	verification.verified_by_id = vl_user_id
	verification.rejection_reason_id = None
	verification.pat_edits = 0
	verification.sample_edits = 0
	verification.save(using='vl_lims')

	return {
		'sample_id': sample.id,
		'barcode': sample.barcode,
		'next_barcode': sample_utils.get_next_barcode(sample.barcode, sample.sample_type),
	}


def create_range(post_data, user):
	vl_user_id = get_vl_user_id(user)
	if not vl_user_id:
		raise ValueError("Current user has no vl_id mapping in hepb.auth_user")

	now = datetime.now()
	year_month = post_data.get('year') + post_data.get('month')
	lower_limit = int(post_data.get('lower_limit'))
	upper_limit = int(post_data.get('upper_limit'))
	if upper_limit < lower_limit:
		raise ValueError("Upper limit must be greater than or equal to lower limit")

	env_range = VLEnvelopeRange(
		year_month=year_month,
		lower_limit=post_data.get('lower_limit'),
		upper_limit=post_data.get('upper_limit'),
		sample_type=post_data.get('sample_type'),
		accessioned_by_id=_parse_int(post_data.get('accessioned_by')) or vl_user_id,
		accessioned_at=now,
		entered_by_id=vl_user_id,
	)
	env_range.save(using='vl_lims')

	for lim in range(lower_limit, upper_limit + 1):
		env_number = year_month + '-' + str(lim).zfill(4)
		envelope = VLEnvelope.objects.using('vl_lims').filter(envelope_number=env_number).first()
		if envelope is None:
			envelope = VLEnvelope(envelope_number=env_number)
		envelope.sample_type = post_data.get('sample_type')
		envelope.accessioned_at = now
		envelope.envelope_range_id = env_range.id
		envelope.accessioner_id = _parse_int(post_data.get('accessioned_by')) or vl_user_id
		envelope.assignment_by_id = vl_user_id
		envelope.sample_medical_lab_id = _resolve_medical_lab_id(user)
		envelope.save(using='vl_lims')
		if not VLEnvelopeAssignment.objects.using('vl_lims').filter(the_envelope_id=envelope.id, assigned_to_id=vl_user_id, type=1).exists():
			VLEnvelopeAssignment(
				the_envelope_id=envelope.id,
				assigned_to_id=vl_user_id,
				assigned_by_id=vl_user_id,
				type=1,
			).save(using='vl_lims')
	return env_range


def get_or_create_tracking_code(code, user, facility_id=None):
	vl_user_id = get_vl_user_id(user)
	if not vl_user_id:
		raise ValueError("Current user has no vl_id mapping in hepb.auth_user")
	code = (code or '').strip()
	if not code:
		raise ValueError("Tracking code is required")
	tr = VLTrackingCode.objects.using('vl_lims').filter(code=code).first()
	if tr is None:
		tr = VLTrackingCode(
			code=code,
			status=0,
			creation_by_id=vl_user_id,
			facility_id=facility_id,
			no_samples=0,
		)
		tr.save(using='vl_lims')
	return tr


def resolve_tracking_code(post_data, user, facility_id=None):
	tracking_code_id = _parse_int(post_data.get('tracking_code_id') or post_data.get('tr_code_id'))
	if tracking_code_id:
		tracking_code = VLTrackingCode.objects.using('vl_lims').filter(pk=tracking_code_id).first()
		if tracking_code:
			return tracking_code
	code = post_data.get('code') or post_data.get('current_tr_code')
	return get_or_create_tracking_code(code, user, facility_id)


def get_envelope_details(envelope_number):
	envelope = VLEnvelope.objects.using('vl_lims').filter(envelope_number=envelope_number).first()
	if envelope is None:
		envelope = _get_envelope_from_legacy(envelope_number=envelope_number)
	if envelope is None:
		return {
			'envelope_id': '',
			'date_received': '',
			'program_mismatch': False,
			'err_msg': '',
			'program_code': '3',
		}
	return {
		'envelope_id': envelope.id,
		'date_received': envelope.created_at.strftime('%Y-%m-%d') if envelope.created_at else '',
		'program_mismatch': False,
		'err_msg': '',
		'program_code': '3',
	}


def receive_sample(post_data, user):
	vl_user_id = get_vl_user_id(user)
	if not vl_user_id:
		raise ValueError("Current user has no vl_id mapping in hepb.auth_user")
	now = datetime.now()
	barcode = post_data.get('the_barcode') or post_data.get('barcode')
	facility_id = _parse_int(post_data.get('facility'))
	envelope = _resolve_envelope(post_data)
	if envelope is None:
		raise ValueError("Envelope was not found, did you accession it?")
	tracking_code = resolve_tracking_code(post_data, user, facility_id)
	form_number = post_data.get('facility_reference') or post_data.get('barcode') or barcode
	sample = VLSample.objects.using('vl_lims').filter(barcode=barcode).first()
	if sample is None:
		sample = VLSample(
			barcode=barcode,
			form_number=form_number,
			created_by_id=vl_user_id,
		)
	sample.tracking_code_id = tracking_code.id
	sample.locator_category = post_data.get('locator_category') or 'V'
	sample.locator_position = post_data.get('the_position') or post_data.get('locator_position') or ''
	sample.facility_id = facility_id
	sample.envelope_id = envelope.id
	sample.sample_type = post_data.get('sample_type')
	sample.date_collected = _parse_date(post_data.get('date_collected'))
	sample.date_received = now
	sample.reception_art_number = post_data.get('reception_hep_number') or None
	sample.facility_reference = post_data.get('facility_reference') or None
	sample.received_by_id = vl_user_id
	sample.updated_by_id = vl_user_id
	sample.medical_lab_id = _resolve_medical_lab_id(user)
	sample.stage = 0
	sample.verified = False
	sample.required_verification = False
	sample.is_data_entered = False
	sample.save(using='vl_lims')
	if sample.locator_position == '01':
		envelope.is_received = True
		envelope.save(using='vl_lims')
	return sample


def receive_sample_only(post_data, user):
	vl_user_id = get_vl_user_id(user)
	if not vl_user_id:
		raise ValueError("Current user has no vl_id mapping in hepb.auth_user")

	now = datetime.now()
	barcode = post_data.get('the_barcode') or post_data.get('barcode')
	facility_reference = (post_data.get('facility_reference') or '').strip()
	art_number = (post_data.get('reception_hep_number') or '').strip()
	if not art_number:
		raise ValueError("ART number is required")

	facility_id = _parse_int(post_data.get('facility'))
	envelope = _resolve_envelope(post_data)
	if envelope is None:
		raise ValueError("Envelope was not found, did you accession it?")

	tracking_code = resolve_tracking_code(post_data, user, facility_id)
	sanitized_art_number = utils.removeSpecialCharactersFromString(art_number) if art_number else None
	unique_id = f"{facility_id}-A-{sanitized_art_number}" if facility_id and sanitized_art_number else None
	patient = VLPatient.objects.using('vl_lims').filter(unique_id=unique_id).first() if unique_id else None
	if patient is None:
		patient = VLPatient(
			unique_id=unique_id,
			art_number=art_number or None,
			sanitized_art_number=sanitized_art_number,
			facility_id=facility_id,
			created_by_id=vl_user_id,
			is_verified=True,
		)
		patient.save(using='vl_lims')
		if not patient.parent_id:
			patient.parent_id = patient.id
			patient.save(using='vl_lims')
	elif not patient.art_number:
		patient.art_number = art_number
		patient.sanitized_art_number = sanitized_art_number or patient.sanitized_art_number
		patient.save(using='vl_lims')

	sample = None
	if facility_reference:
		sample = VLSample.objects.using('vl_lims').filter(facility_reference=facility_reference).first()
	if sample is None and barcode:
		sample = VLSample.objects.using('vl_lims').filter(barcode=barcode).first()
	if sample is None:
		sample = VLSample(created_by_id=vl_user_id)
	elif sample.envelope_id:
		raise ValueError(f"already on {sample.barcode}")

	sample.patient_id = patient.id
	sample.patient_unique_id = patient.unique_id
	sample.tracking_code_id = tracking_code.id
	sample.locator_category = 'V'
	sample.locator_position = post_data.get('the_position') or post_data.get('locator_position') or ''
	sample.barcode = barcode
	sample.form_number = facility_reference or barcode
	sample.facility_id = facility_id
	sample.data_facility_id = facility_id
	sample.envelope_id = envelope.id
	sample.sample_type = post_data.get('sample_type')
	sample.date_collected = _parse_date(post_data.get('date_collected'))
	sample.date_received = now
	sample.reception_art_number = art_number or None
	sample.data_art_number = art_number or sample.data_art_number
	sample.facility_reference = facility_reference or None
	sample.received_by_id = vl_user_id
	sample.updated_by_id = vl_user_id
	sample.data_entered_by_id = vl_user_id
	sample.data_entered_at = now
	sample.verifier_id = vl_user_id
	sample.verified_at = now
	sample.medical_lab_id = _resolve_medical_lab_id(user)
	sample.stage = 0
	sample.verified = True
	sample.required_verification = False
	sample.is_data_entered = True
	sample.save(using='vl_lims')

	verification = VLVerification.objects.using('vl_lims').filter(sample_id=sample.id).first()
	if verification is None:
		verification = VLVerification(sample_id=sample.id, verified_by_id=vl_user_id)
	verification.accepted = True
	verification.verified_by_id = vl_user_id
	verification.rejection_reason_id = None
	verification.pat_edits = 0
	verification.sample_edits = 0
	verification.save(using='vl_lims')

	if sample.locator_position == '01':
		envelope.is_received = True
		envelope.save(using='vl_lims')

	return sample


def get_receive_hie_details(facility_reference):
	facility_reference = (facility_reference or '').strip()
	if not facility_reference:
		return {
			'hep_number': '',
			'date_collected': '',
			'err_msg': 'Not found',
		}

	sample = VLSample.objects.using('vl_lims').filter(facility_reference=facility_reference).first()
	if sample is None:
		return {
			'hep_number': '',
			'date_collected': '',
			'err_msg': 'Not found',
		}

	if sample.date_received is not None:
		return {
			'hep_number': '',
			'date_collected': '',
			'err_msg': 'Already received',
		}

	return {
		'hep_number': sample.data_art_number or sample.reception_art_number or '',
		'date_collected': sample.date_collected.strftime('%Y-%m-%d') if sample.date_collected else '',
		'err_msg': '',
	}


def _adapt_sample(sample):
	facility = _facility_obj(sample.facility_id or sample.data_facility_id)
	patient_facility = facility
	patient = SimpleNamespace(
		hep_number=sample.data_art_number or sample.reception_art_number or '',
		gender='',
		treatment_initiation_date=sample.treatment_initiation_date,
		facility=patient_facility,
	)
	envelope = SimpleNamespace(program_code=3, envelope_number='')
	verification = SimpleNamespace(accepted=bool(sample.verified), pk='')
	return SimpleNamespace(
		id=sample.id,
		pk=sample.id,
		tracking_code_id=sample.tracking_code_id,
		facility_reference=sample.facility_reference,
		form_number=sample.form_number,
		barcode=sample.barcode,
		patient_id=sample.patient_id,
		patient=patient,
		facility=facility,
		sample_reception=SimpleNamespace(facility=facility),
		is_data_entered=sample.is_data_entered,
		reception_hep_number=sample.reception_art_number,
		program_code=3,
		envelope_id=sample.envelope_id,
		envelope=envelope,
		date_collected=sample.date_collected,
		date_received=sample.date_received,
		verified=sample.verified,
		verification=verification,
		stage=sample.stage,
		created_by='VL User %s' % (sample.created_by_id or ''),
		created_at=sample.created_at,
		data_entered_by='VL User %s' % (sample.data_entered_by_id or ''),
		data_entered_at=sample.data_entered_at,
		worksheetsample_set=SimpleNamespace(count=0),
		get_sample_type_display=lambda: _sample_display(sample.sample_type),
	)


def get_adapted_sample(sample_id):
	sample = VLSample.objects.using('vl_lims').filter(pk=sample_id).first()
	return _adapt_sample(sample) if sample else None


def get_envelope_samples(envelope_id):
	if not envelope_id:
		return []
	return [
		SimpleNamespace(id=row.id, pk=row.id, barcode=row.barcode)
		for row in VLSample.objects.using('vl_lims').filter(envelope_id=envelope_id).order_by('barcode')
	]


def _worksheet_ref(sample_type, worksheet_id):
	count = VLWorksheet.objects.using('vl_lims').filter(
		created_at__year=utils.year(),
		created_at__month=utils.month(),
		id__lte=worksheet_id,
	).count()
	num = str(count + 1).zfill(3)
	return "%s%s%s%s" % (utils.year('yy'), utils.month('mm'), sample_type, num)


def worksheet_create_envelope_rows(sample_type, user, search=''):
	qs = VLEnvelope.objects.using('vl_lims').filter(
		sample_medical_lab_id=_resolve_medical_lab_id(user),
		sample_type=sample_type,
		processed_by_id__isnull=True,
	).order_by('created_at')
	if search:
		qs = qs.filter(envelope_number__icontains=search)
	rows = []
	for env in qs:
		s_count = VLSample.objects.using('vl_lims').filter(envelope_id=env.id, locator_category='V', stage=0).count()
		if s_count:
			rows.append({'id': env.id, 'envelope_number': env.envelope_number, 's_count': s_count, 'program': 'HIV Viral Load'})
	return rows


def create_worksheet(post_data, user, sample_type):
	vl_user_id = get_vl_user_id(user)
	generator_id = _parse_int(post_data.get('generated_by_id')) or vl_user_id
	worksheet = VLWorksheet(
		sample_type=sample_type,
		generated_by_id=generator_id,
		worksheet_medical_lab_id=_resolve_medical_lab_id(user),
		worksheet_reference_number=utils.timestamp(),
		stage=12,
	)
	worksheet.save(using='vl_lims')
	worksheet.worksheet_reference_number = _worksheet_ref(sample_type, worksheet.id)
	worksheet.save(using='vl_lims')
	for envelope_id in post_data.getlist('envelope_ids'):
		env = VLEnvelope.objects.using('vl_lims').filter(pk=envelope_id).first()
		if env is None:
			continue
		env.processed_at = datetime.now()
		env.processed_by_id = generator_id
		env.save(using='vl_lims')
		if not VLEnvelopeAssignment.objects.using('vl_lims').filter(the_envelope_id=env.id, assigned_to_id=generator_id, type=2).exists():
			VLEnvelopeAssignment(the_envelope_id=env.id, assigned_to_id=generator_id, assigned_by_id=vl_user_id, type=2).save(using='vl_lims')
		for sample in VLSample.objects.using('vl_lims').filter(envelope_id=env.id, stage=0):
			inst_id = sample.facility_reference if sample.facility_reference and sample.sample_type == 'P' else sample.barcode
			VLWorksheetSample(
				worksheet_id=worksheet.id,
				instrument_id=(inst_id or '').strip(),
				other_instrument_id=sample.barcode,
				sample_id=sample.id,
				sample_run=1,
				stage=1,
				sample_type=sample.sample_type,
			).save(using='vl_lims')
			sample.stage = 1
			sample.save(using='vl_lims')
	return worksheet


def worksheet_list_rows(user, sample_type='', search=''):
	qs = VLWorksheet.objects.using('vl_lims').filter(worksheet_medical_lab_id=_resolve_medical_lab_id(user)).order_by('-id')
	if sample_type:
		qs = qs.filter(sample_type=sample_type)
	if search:
		qs = qs.filter(worksheet_reference_number__icontains=search)
	rows = []
	for row in qs:
		envelopes = VLSample.objects.using('vl_lims').filter(worksheet_id=row.id if hasattr(VLSample, 'worksheet_id') else None)
		rows.append(row)
	return list(qs)


def worksheet_envelope_links(worksheet_id):
	envelope_ids = list(VLSample.objects.using('vl_lims').filter(
		id__in=VLWorksheetSample.objects.using('vl_lims').filter(worksheet_id=worksheet_id).values_list('sample_id', flat=True)
	).values_list('envelope_id', flat=True).distinct())
	parts = []
	for env in VLEnvelope.objects.using('vl_lims').filter(id__in=envelope_ids):
		parts.append('<a href="/samples/search/?search_val=%s&search_env=1" style="margin-left:5px;">%s</a>' % (env.envelope_number, env.envelope_number))
	return ','.join(parts)


def worksheet_detail(worksheet_id):
	worksheet = VLWorksheet.objects.using('vl_lims').filter(pk=worksheet_id).first()
	if worksheet is None:
		return None, []
	samples = []
	for ws in VLWorksheetSample.objects.using('vl_lims').filter(worksheet_id=worksheet_id).order_by('instrument_id'):
		sample = VLSample.objects.using('vl_lims').filter(pk=ws.sample_id).first()
		if sample is None:
			continue
		adapted_sample = _adapt_sample(sample)
		samples.append(SimpleNamespace(
			id=ws.id,
			pk=ws.id,
			worksheet=worksheet,
			sample=adapted_sample,
			sample_id=sample.id,
			instrument_id=ws.instrument_id,
			is_diluted=ws.is_diluted,
			stage=ws.stage,
		))
	worksheet.pk = worksheet.id
	worksheet.machine_type = worksheet.machine_type or 'H'
	return worksheet, samples


def authorize_runs(stage=1):
	if int(stage) == 1:
		qs = VLResultRun.objects.using('vl_lims').filter(stage=1).order_by('-id')
	else:
		qs = VLResultRun.objects.using('vl_lims').filter(stage__lte=4).order_by('-id')
	rows = []
	for run in qs:
		run.no_results = VLResultRunDetail.objects.using('vl_lims').filter(the_result_run_id=run.id).count()
		run.invalid_results = VLResultRunDetail.objects.using('vl_lims').filter(the_result_run_id=run.id, result_alphanumeric='Invalid').count()
		run.pk = run.id
		rows.append(run)
	return rows


def authorize_result_rows(run_id):
	rows = []
	for rd in VLResultRunDetail.objects.using('vl_lims').filter(the_result_run_id=run_id).order_by('result_run_position'):
		ws = VLWorksheetSample.objects.using('vl_lims').filter(result_run_detail_id=rd.id).first()
		if ws:
			sample = VLSample.objects.using('vl_lims').filter(pk=ws.sample_id).first()
			adapted_sample = _adapt_sample(sample) if sample else None
			ws_ns = SimpleNamespace(
				id=ws.id,
				pk=ws.id,
				stage=ws.stage,
				repeat_test=ws.repeat_test or 2,
				authorised=ws.authorised,
				result_alphanumeric=ws.result_alphanumeric,
				sample=adapted_sample,
			)
		else:
			ws_ns = SimpleNamespace(id=None, pk='', stage=0, repeat_test=2, authorised=False, result_alphanumeric='', sample=SimpleNamespace(barcode=''))
		rows.append(SimpleNamespace(
			instrument_id=rd.instrument_id,
			result_run_position=rd.result_run_position,
			result_numeric=rd.result_numeric,
			result_alphanumeric=rd.result_alphanumeric,
			result_run_detail=ws_ns,
		))
	return rows


def authorize_worksheet_sample(ws_id, choice, user):
	vl_user_id = get_vl_user_id(user)
	ws = VLWorksheetSample.objects.using('vl_lims').filter(pk=ws_id).first()
	if ws is None:
		return
	stage = 4 if choice == 'reschedule' else 3
	ws.stage = stage
	ws.authoriser_id = vl_user_id
	ws.authorised_at = datetime.now()
	ws.authorised = choice != 'reschedule'
	ws.save(using='vl_lims')
	if ws.sample_id:
		sample = VLSample.objects.using('vl_lims').filter(pk=ws.sample_id).first()
		if sample:
			sample.stage = stage
			sample.save(using='vl_lims')


def release_pending_worksheets(machine_type, released=False, medical_lab_id=None):
	stage = 4 if released else 3
	ws_ids = VLWorksheetSample.objects.using('vl_lims').filter(stage=stage, method=machine_type).values_list('worksheet_id', flat=True).distinct()
	qs = VLWorksheet.objects.using('vl_lims').filter(id__in=ws_ids)
	if medical_lab_id:
		qs = qs.filter(worksheet_medical_lab_id=medical_lab_id)
	return list(qs.order_by('-id'))


def release_result_rows(run_id=None, sample_type='', worksheet_id=None):
	qs = VLWorksheetSample.objects.using('vl_lims').filter(stage=3)
	if run_id:
		qs = qs.filter(result_run_id=run_id)
	if worksheet_id:
		qs = qs.filter(worksheet_id=worksheet_id)
	if sample_type:
		qs = qs.filter(sample_type=sample_type)
	rows = []
	for ws in qs.order_by('result_run_position'):
		sample = VLSample.objects.using('vl_lims').filter(pk=ws.sample_id).first()
		adapted = _adapt_sample(sample) if sample else None
		result = VLResult.objects.using('vl_lims').filter(sample_id=ws.sample_id).first() if ws.sample_id else None
		resultsqc = VLResultsQC.objects.using('vl_lims').filter(result_id=result.id).first() if result else None
		if adapted and result and resultsqc:
			adapted.result = SimpleNamespace(resultsqc=SimpleNamespace(released=resultsqc.released))
		elif adapted:
			adapted.result = SimpleNamespace(resultsqc=SimpleNamespace(released=None))
		rows.append(SimpleNamespace(
			id=ws.id,
			pk=ws.id,
			stage=ws.stage,
			repeat_test=ws.repeat_test or 2,
			result_alphanumeric=ws.result_alphanumeric,
			result_numeric=ws.result_numeric,
			sample=adapted,
			instrument_id=ws.instrument_id,
		))
	return rows


def release_worksheet_sample(ws_id, choice, user, comments=''):
	vl_user_id = get_vl_user_id(user)
	ws = VLWorksheetSample.objects.using('vl_lims').filter(pk=ws_id).first()
	if ws is None or not ws.sample_id:
		return
	if choice == 'reschedule':
		ws.stage = 4
		ws.save(using='vl_lims')
		return
	result = VLResult.objects.using('vl_lims').filter(sample_id=ws.sample_id).first()
	if result is None:
		result = VLResult(
			repeat_test=2,
			result1=ws.result_alphanumeric or '',
			result_alphanumeric='Failed' if choice == 'invalid' else (ws.result_alphanumeric or ''),
			result_numeric=ws.result_numeric,
			failure_reason=ws.failure_reason,
			method=ws.method,
			test_date=ws.test_date,
			authorised_at=ws.authorised_at or datetime.now(),
			authorised_by_id=ws.authoriser_id,
			sample_id=ws.sample_id,
			test_by_id=ws.tester_id,
			suppressed=ws.suppressed or 0,
			authorised=True,
			result_upload_date=datetime.now(),
			worksheet_sample_id=ws.id,
			supression_cut_off_id=ws.supression_cut_off_id,
			has_low_level_viramia=ws.has_low_level_viramia,
		)
	else:
		result.result_alphanumeric = 'Failed' if choice == 'invalid' else (ws.result_alphanumeric or '')
		result.authorised = True
		result.authorised_at = datetime.now()
		result.authorised_by_id = ws.authoriser_id or vl_user_id
	result.save(using='vl_lims')
	qc = VLResultsQC.objects.using('vl_lims').filter(result_id=result.id).first()
	if qc is None:
		qc = VLResultsQC(result_id=result.id)
	qc.released = True
	qc.comments = comments or ''
	qc.released_by_id = vl_user_id
	qc.released_at = datetime.now()
	qc.qc_date = datetime.now()
	qc.save(using='vl_lims')
	ws.stage = 5
	ws.save(using='vl_lims')
	sample = VLSample.objects.using('vl_lims').filter(pk=ws.sample_id).first()
	if sample:
		sample.stage = 5
		sample.verified = True
		sample.save(using='vl_lims')


def search_samples(search, search_env=False, search_sample=False):
	search = (search or '').strip()
	if not search:
		return []
	if search_env:
		envelope = VLEnvelope.objects.using('vl_lims').filter(envelope_number=search).first()
		if envelope is None:
			return []
		samples = VLSample.objects.using('vl_lims').filter(envelope_id=envelope.id).order_by('locator_position')[:300]
		return [_adapt_sample(sample) for sample in samples]
	direct_filter = Q(barcode=search) | Q(form_number=search) | Q(facility_reference=search)
	samples = VLSample.objects.using('vl_lims').filter(direct_filter).order_by('-id')[:300]
	if not samples and not search_sample:
		samples = VLSample.objects.using('vl_lims').filter(
			Q(form_number__icontains=search) |
			Q(barcode__icontains=search) |
			Q(facility_reference__icontains=search) |
			Q(reception_art_number__icontains=search) |
			Q(data_art_number__icontains=search)
		).order_by('-id')[:300]
	return [_adapt_sample(sample) for sample in samples]


def get_result_run(filename, user):
	vl_user_id = get_vl_user_id(user)
	if not vl_user_id:
		raise ValueError("Current user has no vl_id mapping in hepb.auth_user")
	rn = VLResultRun.objects.using('vl_lims').filter(file_name=filename).first()
	if rn is None:
		rn = VLResultRun(
			file_name=filename,
			upload_date=timezone.now(),
			run_uploaded_by_id=vl_user_id,
			stage=1,
		)
		rn.save(using='vl_lims')
	if rn.stage == 3:
		return 'completed'
	return rn


def _compare_results_for_adjacency_contamination(cohort):
	value_is_gte = 0
	for item in cohort:
		if not item.result_numeric or item.result_numeric < settings.CONTAMINATION_CHECK_NUMERIC_VALUE:
			return 0
		value_is_gte = 1
	return value_is_gte


def update_run_with_contamination_info(result_run):
	details = list(
		VLResultRunDetail.objects.using('vl_lims').filter(the_result_run_id=result_run.id).order_by('result_run_position')
	)
	no_of_res_gte_1k = len([row for row in details if row.result_numeric and row.result_numeric >= settings.CONTAMINATION_CHECK_NUMERIC_VALUE])
	adjacent_size = settings.NUMBER_OF_RESULTS_FOR_ADJANCENCY_CONTAMINATION_CHECK - 1
	is_run_contaminated = 0
	no_results = len(details)
	if no_results >= adjacent_size and adjacent_size > 0:
		indices_arr = []
		counter = 0
		while counter <= (no_results - adjacent_size):
			compare_indices = utils.get_indices(indices_arr, adjacent_size, counter)
			cohort = [details[i] for i in compare_indices]
			is_run_contaminated = _compare_results_for_adjacency_contamination(cohort)
			if is_run_contaminated:
				break
			counter += 1
	result_run.has_squential_samples_with_more_than_thou_copies = is_run_contaminated
	result_run.samples_with_more_than_thou_copies = no_of_res_gte_1k
	result_run.save(using='vl_lims')
	return True


def save_upload_result(result, multiplier, machine_type, instrument_id, user, active_program_code='3'):
	sample = VLSample.objects.using('vl_lims').filter(barcode=instrument_id).first()
	if sample and sample.is_data_entered == 1:
		result_dict = result_utils.get_result(result, multiplier, machine_type, 0, sample.sample_type, '', active_program_code)
		the_test_date = timezone.now()
		final_result = VLResult(
			repeat_test=2,
			authorised=True,
			result1=result_dict.get('alphanumeric_result'),
			result_numeric=result_dict.get('numeric_result'),
			failure_reason='',
			method=machine_type,
			test_date=the_test_date,
			authorised_at=the_test_date,
			authorised_by_id=get_vl_user_id(user),
			test_by_id=get_vl_user_id(user),
			sample_id=sample.id,
			suppressed=result_dict.get('suppressed') or 0,
			supression_cut_off_id=result_dict.get('supression_cut_off'),
			has_low_level_viramia=result_dict.get('has_low_level_viramia'),
			result_alphanumeric=result_dict.get('alphanumeric_result'),
			result_upload_date=the_test_date,
		)
		final_result.save(using='vl_lims')
		qc = VLResultsQC.objects.using('vl_lims').filter(result_id=final_result.id).first()
		if qc is None:
			qc = VLResultsQC(result_id=final_result.id)
		qc.released = True
		qc.comments = ''
		qc.released_by_id = get_vl_user_id(user)
		qc.released_at = timezone.now()
		qc.qc_date = timezone.now()
		qc.save(using='vl_lims')


def update_sample_and_save_result(machine_type, instrument_id, result, multiplier, user, test_date, result_run, row_index, sample_volume='', active_program_code='3'):
	try:
		if user.userprofile.medical_lab_id == 2:
			save_upload_result(result, multiplier, machine_type, instrument_id, user, active_program_code=active_program_code)
			return 0
	except Exception:
		pass
	ins_filter = Q(instrument_id=instrument_id) | Q(other_instrument_id=instrument_id)
	stage_filter = Q(stage__lte=3) | Q(stage=4)
	ws = VLWorksheetSample.objects.using('vl_lims').filter(ins_filter & stage_filter).first()
	if ws is None:
		return None
	sample = VLSample.objects.using('vl_lims').filter(pk=ws.sample_id).first() if ws.sample_id else None
	if sample is None or sample.sample_type is None:
		ws.sample_id = None
		ws.save(using='vl_lims')
		return None
	result_dict = result_utils.get_result(
		result,
		multiplier,
		machine_type,
		ws.is_diluted,
		sample.sample_type,
		sample_volume,
		active_program_code,
	)
	the_test_date = timezone.now() if machine_type == 'H' else timezone.now()
	run_detail = VLResultRunDetail.objects.using('vl_lims').filter(the_result_run_id=result_run.id, instrument_id=instrument_id).first()
	if run_detail is None:
		run_detail = VLResultRunDetail(
			result_numeric=result_dict.get('numeric_result'),
			result_alphanumeric=result_dict.get('alphanumeric_result'),
			result_run_position=row_index,
			test_date=the_test_date,
			testing_by_id=get_vl_user_id(user),
			the_result_run_id=result_run.id,
			instrument_id=instrument_id,
		)
		run_detail.save(using='vl_lims')
	result = result.strip() if isinstance(result, str) else result
	if ws.stage in (1, 4):
		ws.repeat_test = result_dict.get('rep_test')
		ws.result_numeric = result_dict.get('numeric_result')
		alf_num_result = result_dict.get('alphanumeric_result')
		ws.result_alphanumeric = alf_num_result
		ws.suppressed = result_dict.get('suppressed')
		ws.method = machine_type
		ws.result_run_detail_id = run_detail.id
		ws.test_date = the_test_date
		ws.tester_id = get_vl_user_id(user)
		ws.stage = 2
		ws.result_run_id = result_run.id
		ws.result_run_position = row_index
		ws.supression_cut_off_id = result_dict.get('supression_cut_off')
		ws.has_low_level_viramia = result_dict.get('has_low_level_viramia')
		sample.stage = 2
		if alf_num_result == 'Failed':
			ws.repeat_test = 1
			ws.stage = 4
			sample.stage = 4
			ws.authorised_at = timezone.now()
			ws.authoriser_id = get_vl_user_id(user)
		sample.save(using='vl_lims')
		ws.save(using='vl_lims')
	return ws


def process_hologic(actual_file_name, tmp_name, request):
	reader = pandas.read_csv(tmp_name, sep='\t')
	test_date = timezone.now()
	multiplier = request.POST.get('multiplier')
	active_program_code = programs.get_active_program_code(request)
	result_run = VLResultRun.objects.using('vl_lims').filter(file_name=actual_file_name).first()
	reagent_expiry_date = reader.iloc[5]["Assay Reagent Kit ML Exp Date UTC"]
	if result_run is None:
		result_run = VLResultRun(
			file_name=actual_file_name,
			upload_date=timezone.now(),
			run_uploaded_by_id=get_vl_user_id(request.user),
			low_positive_ctrl=reader.iloc[3]["Interpretation 1"],
			high_positive_ctrl=reader.iloc[4]["Interpretation 1"],
			negative_ctrl=reader.iloc[5]["Interpretation 1"],
			reagent_lot=reader.iloc[5]["Assay Reagent Kit ML #"],
			reagent_expiry_date=datetime.strptime(reagent_expiry_date, '%d-%B-%y %H:%M:%S'),
			serial_number=reader.iloc[5]["Serial Number"],
		)
		result_run.save(using='vl_lims')
	for row in reader.iterrows():
		index, data = row
		result = data['Interpretation 1'] if data['Interpretation 4'] == 'Valid' else 'Invalid'
		vl_sample_id = data['Specimen Barcode']
		analyte = data['Analyte']
		vl_sample_id = vl_sample_id.strip() if isinstance(vl_sample_id, str) else vl_sample_id
		result_run.reagent_lot = data['Assay Reagent Kit ML #']
		result_run.serial_number = data['Serial Number']
		if analyte == 'HIV-1':
			update_sample_and_save_result('H', vl_sample_id, result, multiplier, request.user, test_date, result_run, index, active_program_code=active_program_code)
	result_run.save(using='vl_lims')
	update_run_with_contamination_info(result_run)
	return result_run
