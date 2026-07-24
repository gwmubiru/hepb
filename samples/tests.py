from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from samples.data_table_views import ListJson
from samples.views import (
	_resolve_tracking_code,
	_resolve_tracking_code_for_sample,
	_should_block_tracking_code_facility_mismatch,
)
from vl import services as vl_services


class FakeQuerySet:
	def __init__(self):
		self.filter_calls = []
		self.order_by_calls = []

	def filter(self, *args, **kwargs):
		self.filter_calls.append((args, kwargs))
		return self

	def order_by(self, *fields):
		self.order_by_calls.append(fields)
		return self


class SampleListSearchFilterTests(SimpleTestCase):
	def filter_queryset(self, params):
		view = ListJson()
		view.request = SimpleNamespace(GET=params, session={})
		qs = FakeQuerySet()
		view.filter_queryset(qs)
		return qs

	def test_default_list_keeps_data_entry_completed_scope(self):
		qs = self.filter_queryset({})

		self.assertIn(((), {'patient_id__isnull': False}), qs.filter_calls)

	def test_explicit_sample_search_does_not_require_patient_data_entry(self):
		qs = self.filter_queryset({'global_search': 'SAMPLE-001'})

		self.assertNotIn(((), {'patient_id__isnull': False}), qs.filter_calls)


class VLSearchAdapterTests(SimpleTestCase):
	def sample(self, **overrides):
		values = {
			'id': 1,
			'facility_id': None,
			'data_facility_id': None,
			'clinician_id': None,
			'lab_tech_id': None,
			'tracking_code_id': None,
			'data_art_number': '',
			'reception_art_number': '',
			'treatment_initiation_date': None,
			'facility_reference': 'FAC-001',
			'form_number': 'FAC-001',
			'barcode': '',
			'patient_id': None,
			'is_data_entered': False,
			'envelope_id': None,
			'date_collected': None,
			'date_received': None,
			'verified': False,
			'stage': 0,
			'created_by_id': None,
			'created_at': None,
			'data_entered_by_id': None,
			'data_entered_at': None,
			'sample_type': 'P',
		}
		values.update(overrides)
		return SimpleNamespace(**values)

	def test_adapted_vl_sample_with_null_tracking_code_can_render_tracking_column(self):
		adapted = vl_services._adapt_sample(self.sample())

		self.assertIsNone(adapted.tracking_code_id)
		self.assertEqual(adapted.tracking_code.code, '')

	def test_adapted_vl_sample_uses_tracking_code_map_when_present(self):
		tracking_code = SimpleNamespace(id=7, code='TRK-7', facility_id=3)
		adapted = vl_services._adapt_sample(
			self.sample(tracking_code_id=7),
			tracking_codes={7: tracking_code},
		)

		self.assertEqual(adapted.tracking_code_id, 7)
		self.assertEqual(adapted.tracking_code.code, 'TRK-7')


class TrackingCodeResolutionTests(SimpleTestCase):
	def mock_tracking_code_lookup(self, tracking_code_model, tracking_code):
		tracking_code_model.objects.using.return_value.filter.return_value.first.return_value = tracking_code

	@patch('samples.views._get_or_create_tracking_code')
	@patch('samples.views.TrackingCode')
	def test_new_visible_code_wins_over_stale_hidden_tracking_code_id(self, tracking_code_model, get_or_create):
		old_tracking_code = SimpleNamespace(id=1, code='OLD-CODE', facility_id=2)
		new_tracking_code = SimpleNamespace(id=3, code='NEW-CODE', facility_id=4)
		self.mock_tracking_code_lookup(tracking_code_model, old_tracking_code)
		get_or_create.return_value = new_tracking_code

		tracking_code = _resolve_tracking_code(
			old_tracking_code.id,
			'NEW-CODE',
			5,
			4,
		)

		self.assertEqual(tracking_code, new_tracking_code)
		get_or_create.assert_called_once_with('NEW-CODE', 5, 4, db_alias='default')

	@patch('samples.views._get_or_create_tracking_code')
	@patch('samples.views.TrackingCode')
	def test_matching_visible_code_keeps_hidden_tracking_code_id(self, tracking_code_model, get_or_create):
		old_tracking_code = SimpleNamespace(id=1, code='OLD-CODE', facility_id=2)
		self.mock_tracking_code_lookup(tracking_code_model, old_tracking_code)

		tracking_code = _resolve_tracking_code(
			old_tracking_code.id,
			'OLD-CODE',
			5,
			2,
		)

		self.assertEqual(tracking_code, old_tracking_code)
		get_or_create.assert_not_called()

	@patch('samples.views._get_or_create_tracking_code')
	@patch('samples.views._get_tracking_code_by_id')
	def test_existing_sample_tracking_code_wins_when_present(self, get_tracking_code_by_id, get_or_create):
		existing_tracking_code = SimpleNamespace(id=9, code='PACKAGE-CODE', facility_id=4)
		sample = SimpleNamespace(tracking_code_id=existing_tracking_code.id)
		get_tracking_code_by_id.return_value = existing_tracking_code

		tracking_code = _resolve_tracking_code_for_sample(
			sample,
			'',
			'VISIBLE-CODE',
			5,
			4,
		)

		self.assertEqual(tracking_code, existing_tracking_code)
		get_tracking_code_by_id.assert_called_once_with(existing_tracking_code.id, db_alias='default')
		get_or_create.assert_not_called()

	@patch('samples.views._get_or_create_tracking_code')
	@patch('samples.views._get_tracking_code_by_id')
	def test_placeholder_sample_tracking_code_can_be_replaced(self, get_tracking_code_by_id, get_or_create):
		placeholder_tracking_code = SimpleNamespace(id=9, code='None', facility_id=None)
		new_tracking_code = SimpleNamespace(id=12, code='ENTERED-CODE', facility_id=4)
		sample = SimpleNamespace(tracking_code_id=placeholder_tracking_code.id)
		get_tracking_code_by_id.return_value = placeholder_tracking_code
		get_or_create.return_value = new_tracking_code

		tracking_code = _resolve_tracking_code_for_sample(
			sample,
			placeholder_tracking_code.id,
			'ENTERED-CODE',
			5,
			4,
		)

		self.assertEqual(tracking_code, new_tracking_code)
		get_or_create.assert_called_once_with('ENTERED-CODE', 5, 4, db_alias='default')

	@patch('samples.views._get_or_create_tracking_code')
	@patch('samples.views._get_tracking_code_by_id')
	def test_placeholder_sample_tracking_code_without_entered_code_is_rejected(self, get_tracking_code_by_id, get_or_create):
		placeholder_tracking_code = SimpleNamespace(id=9, code='Non', facility_id=None)
		sample = SimpleNamespace(tracking_code_id=placeholder_tracking_code.id)
		get_tracking_code_by_id.return_value = placeholder_tracking_code

		tracking_code = _resolve_tracking_code_for_sample(
			sample,
			placeholder_tracking_code.id,
			'',
			5,
			4,
		)

		self.assertIsNone(tracking_code)
		get_or_create.assert_not_called()

	def test_existing_sample_with_null_tracking_code_can_take_entered_code_from_other_facility(self):
		sample = SimpleNamespace(tracking_code_id=None)
		tracking_code = SimpleNamespace(id=11, code='ENTERED-CODE', facility_id=7)

		self.assertFalse(_should_block_tracking_code_facility_mismatch(sample, tracking_code, 4))

	def test_new_sample_still_blocks_entered_code_from_other_facility(self):
		tracking_code = SimpleNamespace(id=11, code='ENTERED-CODE', facility_id=7)

		self.assertTrue(_should_block_tracking_code_facility_mismatch(None, tracking_code, 4))


class VLTrackingCodeResolutionTests(SimpleTestCase):
	@patch('vl.services.get_or_create_tracking_code')
	@patch('vl.services.VLTrackingCode')
	def test_existing_sample_tracking_code_wins_when_present(self, tracking_code_model, get_or_create):
		existing_tracking_code = SimpleNamespace(id=9, code='PACKAGE-CODE', facility_id=4)
		tracking_code_model.objects.using.return_value.filter.return_value.first.return_value = existing_tracking_code
		sample = SimpleNamespace(tracking_code_id=existing_tracking_code.id)

		tracking_code = vl_services.resolve_tracking_code(
			{'code': 'VISIBLE-CODE'},
			SimpleNamespace(),
			4,
			sample=sample,
		)

		self.assertEqual(tracking_code, existing_tracking_code)
		get_or_create.assert_not_called()

	@patch('vl.services.get_or_create_tracking_code')
	@patch('vl.services.VLTrackingCode')
	def test_placeholder_sample_tracking_code_can_be_replaced(self, tracking_code_model, get_or_create):
		placeholder_tracking_code = SimpleNamespace(id=9, code='None', facility_id=None)
		new_tracking_code = SimpleNamespace(id=12, code='ENTERED-CODE', facility_id=4)
		tracking_code_model.objects.using.return_value.filter.return_value.first.return_value = placeholder_tracking_code
		get_or_create.return_value = new_tracking_code
		sample = SimpleNamespace(tracking_code_id=placeholder_tracking_code.id)
		user = SimpleNamespace()

		tracking_code = vl_services.resolve_tracking_code(
			{'tracking_code_id': placeholder_tracking_code.id, 'code': 'ENTERED-CODE'},
			user,
			4,
			sample=sample,
		)

		self.assertEqual(tracking_code, new_tracking_code)
		get_or_create.assert_called_once_with('ENTERED-CODE', user, 4)

	@patch('vl.services.get_or_create_tracking_code')
	def test_visible_code_used_when_sample_tracking_code_is_null(self, get_or_create):
		new_tracking_code = SimpleNamespace(id=10, code='VISIBLE-CODE', facility_id=4)
		get_or_create.return_value = new_tracking_code
		sample = SimpleNamespace(tracking_code_id=None)
		user = SimpleNamespace()

		tracking_code = vl_services.resolve_tracking_code(
			{'code': 'VISIBLE-CODE'},
			user,
			4,
			sample=sample,
		)

		self.assertEqual(tracking_code, new_tracking_code)
		get_or_create.assert_called_once_with('VISIBLE-CODE', user, 4)
