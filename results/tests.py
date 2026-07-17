import pandas

from django.test import SimpleTestCase

from results import utils as result_utils
from results.views import _interpret_cobas_panel_result, _is_cobas_panel_results


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

	def test_interprets_all_panel_results_from_one_row(self):
		row = pandas.Series({
			'Validity': 'Valid',
			'Overall result': 'Reactive',
			'Target 1': 'HIV Reactive',
			'Target 2': 'HBV Non-Reactive',
			'Target 3': 'HCV Reactive',
		})

		self.assertEqual(_interpret_cobas_panel_result(row), 'HIV: Positive; HBV: Negative; HCV: Detected')

	def test_qualitative_result_is_not_converted_to_numeric_viral_load_text(self):
		result = result_utils.get_result('Positive', 1, 'C', 0, 'P', active_program_code='1')

		self.assertEqual(result['alphanumeric_result'], 'Positive')
		self.assertEqual(result['numeric_result'], 1)
		self.assertEqual(result['result_type'], result_utils.RESULT_TYPE_QUALITATIVE)

	def test_panel_result_is_kept_for_review_and_split_for_final_result_columns(self):
		panel_result = 'HIV: Positive; HBV: Negative; HCV: Target Not Detected'
		result = result_utils.get_result(panel_result, 1, 'C', 0, 'P', active_program_code='1')

		self.assertEqual(result['alphanumeric_result'], panel_result)
		self.assertEqual(result['result_type'], result_utils.RESULT_TYPE_QUALITATIVE)
		self.assertEqual(result_utils.get_final_result_alphanumeric(panel_result), 'Target Not Detected')
		self.assertEqual(result_utils.get_panel_result_fields(panel_result), {
			'result1': 'Target Not Detected',
			'result2': 'Negative',
			'result3': 'Positive',
		})

	def test_old_quantitative_result_type_stays_quantitative(self):
		result = result_utils.get_result('8.24e+002 IU/ml', 1, 'C', 0, None, active_program_code='1')

		self.assertEqual(result['result_type'], result_utils.RESULT_TYPE_QUANTITATIVE)
