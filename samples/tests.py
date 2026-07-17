from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from samples.views import _resolve_tracking_code


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
