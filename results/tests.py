import pandas
from types import SimpleNamespace

from django.test import SimpleTestCase

from results import utils as result_utils
from results.views import (
	_get_cobas_result_for_row,
	_interpret_cobas_panel_result,
	_is_cobas_panel_result_row,
	_is_cobas_panel_results,
)


class CobasPanelResultTests(SimpleTestCase):
	def test_detects_panel_results_from_mpx_targets(self):
		reader = pandas.DataFrame([{
			'Test': 'MPX',
			'Target 1': 'HIV Non-Reactive',
			'Target 2': 'HBV Reactive',
			'Target 3': 'HCV Non-Reactive',
		}])

		self.assertTrue(_is_cobas_panel_results(reader))

	def test_does_not_detect_old_quantitative_cobas_template_as_panel(self):
		reader = pandas.DataFrame([{
			'Test': 'HBV',
			'Target 1': '8.24e+002 IU/ml',
			'Target 2': '',
			'Target 3': '',
		}])

		self.assertFalse(_is_cobas_panel_results(reader))

	def test_specific_cobas_test_row_uses_quantitative_target_result(self):
		row = pandas.Series({
			'Test': 'HBV',
			'Validity': 'Valid',
			'Overall result': 'Titer',
			'Target 1': '3.90E+06',
			'Target 2': '',
			'Target 3': '',
		})

		self.assertFalse(_is_cobas_panel_result_row(row))
		self.assertEqual(_get_cobas_result_for_row(row), '3.90E+06')

	def test_hiv_specific_cobas_test_row_uses_quantitative_target_result(self):
		row = pandas.Series({
			'Test': 'HIV-1',
			'Validity': 'Valid',
			'Overall result': 'Target Not Detected',
			'Target 1': 'Target Not Detected',
			'Target 2': '',
			'Target 3': '',
		})

		self.assertFalse(_is_cobas_panel_result_row(row))
		self.assertEqual(_get_cobas_result_for_row(row), 'Target Not Detected')

	def test_interprets_all_panel_results_from_one_row(self):
		row = pandas.Series({
			'Test': 'MPX',
			'Validity': 'Valid',
			'Overall result': 'Reactive',
			'Target 1': 'HIV Reactive',
			'Target 2': 'HBV Non-Reactive',
			'Target 3': 'HCV Reactive',
		})

		self.assertEqual(_interpret_cobas_panel_result(row), 'HIV: Positive; HBV: Negative; HCV: Detected')
		self.assertTrue(_is_cobas_panel_result_row(row))
		self.assertEqual(_get_cobas_result_for_row(row), 'HIV: Positive; HBV: Negative; HCV: Detected')

	def test_specific_test_value_is_not_panel_just_because_targets_are_populated(self):
		reader = pandas.DataFrame([{
			'Test': 'HBV',
			'Target 1': '3.90E+06',
			'Target 2': 'unexpected extra target',
			'Target 3': 'unexpected extra target',
		}])

		self.assertFalse(_is_cobas_panel_results(reader))

	def test_qualitative_result_is_not_converted_to_numeric_viral_load_text(self):
		result = result_utils.get_result('Positive', 1, 'C', 0, 'P', active_program_code='1')

		self.assertEqual(result['alphanumeric_result'], 'Positive')
		self.assertEqual(result['numeric_result'], 1)
		self.assertEqual(result['result_type'], result_utils.RESULT_TYPE_QUALITATIVE)

	def test_panel_result_is_kept_for_review_and_split_for_final_result_columns(self):
		panel_result = 'HIV: Positive; HBV: Negative; HCV: Target Not Detected'
		result = result_utils.get_result(panel_result, 1, 'C', 0, 'P', active_program_code='1')

		self.assertEqual(result['alphanumeric_result'], panel_result)
		self.assertEqual(result['result_type'], result_utils.RESULT_TYPE_MULTIPLEX)
		self.assertEqual(result['suppressed'], 0)
		self.assertEqual(result_utils.get_final_result_alphanumeric(panel_result), 'Target Not Detected')
		self.assertEqual(result_utils.get_panel_result_fields(panel_result), {
			'result1': 'Target Not Detected',
			'result2': 'Negative',
			'result3': 'Positive',
		})

	def test_panel_result_suppression_overrides_existing_suppressed_value(self):
		panel_result = 'HIV: Positive; HBV: Negative; HCV: Target Not Detected'

		self.assertEqual(result_utils.get_suppressed_for_result(panel_result, 3), 0)
		self.assertEqual(result_utils.get_suppressed_for_result('Positive', 2), 2)

	def test_non_panel_display_ignores_historical_quantitative_result_columns(self):
		result = SimpleNamespace(
			result_type=result_utils.RESULT_TYPE_QUANTITATIVE,
			result1='first old quantitative result',
			result2='second old quantitative result',
			result3='third old quantitative result',
			result_alphanumeric='824 IU/ml',
		)

		self.assertEqual(result_utils.format_result_for_display(result), '824 IU/ml')
		self.assertEqual(result_utils.get_result_for_program(result, program_code=2), '824 IU/ml')

	def test_non_panel_display_ignores_historical_qualitative_result_columns(self):
		result = SimpleNamespace(
			result_type=result_utils.RESULT_TYPE_QUALITATIVE,
			result1='first old qualitative result',
			result2='second old qualitative result',
			result3='third old qualitative result',
			result_alphanumeric='Positive',
		)

		self.assertEqual(result_utils.format_result_for_display(result), 'Positive')
		self.assertEqual(result_utils.get_result_for_program(result, program_code=1), 'Positive')

	def test_panel_display_and_program_results_use_panel_columns_only_for_panel(self):
		result = SimpleNamespace(
			result_type=result_utils.RESULT_TYPE_MULTIPLEX,
			result1='Target Not Detected',
			result2='Negative',
			result3='Positive',
			result_alphanumeric='Target Not Detected',
		)

		self.assertEqual(result_utils.get_result_for_program(result, program_code=2), 'Target Not Detected')
		self.assertEqual(result_utils.get_result_for_program(result, program_code=1), 'Negative')
		self.assertEqual(result_utils.get_result_for_program(result, program_code=3), 'Positive')
		self.assertEqual(
			result_utils.format_result_for_display(result),
			'HIV: Positive; HBV: Negative; HCV: Target Not Detected'
		)

	def test_invalidated_panel_display_uses_final_result(self):
		result = SimpleNamespace(
			result_type=result_utils.RESULT_TYPE_MULTIPLEX,
			result1='Target Not Detected',
			result2='Negative',
			result3='Positive',
			result_alphanumeric='Failed',
		)

		self.assertEqual(result_utils.format_result_for_display(result), 'Failed')
		self.assertEqual(result_utils.get_result_for_program(result, program_code=2), 'Failed')

	def test_old_quantitative_result_type_stays_quantitative(self):
		result = result_utils.get_result('8.24e+002 IU/ml', 1, 'C', 0, None, active_program_code='1')

		self.assertEqual(result['result_type'], result_utils.RESULT_TYPE_QUANTITATIVE)
