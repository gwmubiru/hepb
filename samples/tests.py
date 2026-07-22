from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from samples.data_table_views import ListJson
from samples.views import _resolve_tracking_code
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
