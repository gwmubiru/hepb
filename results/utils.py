

def repeat_test(machine_type, result, flag):
	repeat = False
	if machine_type == 'R':
		repeat = 3 if result == 'Invalid' or result == 'Failed' else 2
	else:
		repeat_list_results = [
				"-1.00",
				"3153 There is insufficient volume in the vessel to perform an aspirate or dispense operation.",
				"3109 A no liquid detected error was encountered by the Liquid Handler.",
				"A no liquid detected error was encountered by the Liquid Handler.",
				"Unable to process result, instrument response is invalid.",
				"3118 A clot limit passed error was encountered by the Liquid Handler.",
				"3119 A no clot exit detected error was encountered by the Liquid Handler.",
				"3130 A less liquid than expected error was encountered by the Liquid Handler.",
				"3131 A more liquid than expected error was encountered by the Liquid Handler.",
				"3152 The specified submerge position for the requested liquid volume exceeds the calibrated Z bottom",
				"4455 Unable to process result, instrument response is invalid.",
				"A no liquid detected error was encountered by the Liquid Handler.",
				"Failed          Internal control cycle number is too high. Valid range is [18.48, 22.48].",
				"Failed          Failed            Internal control cycle number is too high. Valid range is [18.48,",
				"Failed          Failed          Internal control cycle number is too high. Valid range is [18.48, 2",
				"OPEN",
				"There is insufficient volume in the vessel to perform an aspirate or dispense operation.",
				"Unable to process result, instrument response is invalid.",
				]

		repeat_list_flags = [
				"4442 Internal control cycle number is too high.",
				"4450 Normalized fluorescence too low.",
				"4447 Insufficient level of Assay reference dye.",
				"4457 Internal control failed.",
			]

		check = (result in repeat_list_results) or (flag in repeat_list_flags)
		repeat = 3 if check else 2

	return repeat


def get_result(result, multiplier):
	result = result.strip()
	numeric_result = 0
	alphanumeric_result = ''
	suppressed = 3

	if eq(result,'Target Not Detected') or eq(result,'Not detected'):
		numeric_result = 0
		alphanumeric_result = result
		suppressed = 1
	elif eq(result,'invalid') or eq(result, 'failed'):
		numeric_result = 0
		alphanumeric_result = 'Failed'
		suppressed = 3
	elif result[-5:] == 'cp/ml':
		numeric_result = int(float(result[:-6]))
		numeric_result *= multiplier 
		alphanumeric_result = "%d Copies / mL" %numeric_result
		suppressed = 1 if numeric_result<1000 else 2
	elif eq(result, '< Titer min'):
		numeric_result = 20
		alphanumeric_result = '< 20.00 Copies / mL'
		suppressed = 1
	else:
		result_new = result.replace('Copies / mL', '')
		result_new = result_new.replace(' ', '')
		result_new = result_new.replace(',', '')
		result_new = result_new.replace('>', '')
		result_new = result_new.replace('<', '')
		numeric_result = int(float(result_new))
		if result[0] == '<' or result[0] == '>':
			alphanumeric_result = result
			suppressed = 1 if numeric_result<1000 else 2
		else:
			numeric_result *= multiplier
			alphanumeric_result = "%d Copies / mL" %numeric_result
			suppressed = 1 if numeric_result<1000 else 2	

	return {'numeric_result':numeric_result, 'alphanumeric_result':alphanumeric_result, 'suppressed': suppressed}

def eq(a,b):
	return a.upper() == b.upper()