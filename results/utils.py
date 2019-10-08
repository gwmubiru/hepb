from home import utils

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

		check = (result in repeat_list_results) or (flag in repeat_list_flags) or not result or utils.isnan(result)
		repeat = 3 if check else 2

	return repeat


def get_result(result, multiplier):
	result = result.strip() if type(result) is str else result
	numeric_result = 0
	alphanumeric_result = ''
	suppressed = 3
	repeat_test = 2

	if eq(result,'Target Not Detected') or eq(result,'Not detected'):
		numeric_result = 0
		alphanumeric_result = result
		suppressed = 1
	elif eq(result,'invalid') or eq(result, 'failed') or utils.isnan(result) or result == '':
		numeric_result = 0
		alphanumeric_result = 'Failed'
		suppressed = 3
		repeat_test = 3
	
	elif result.startswith('<') or result.startswith('>'):
		numeric_result = get_numeric_result(result)
		suppressed = 1 if numeric_result<1000 else 2
		alphanumeric_result = "%s {:,d} IU / mL".format(numeric_result) %result[0]
	elif result[-5:] == 'cp/ml':
		numeric_result = int(float(result[:-6]))
		numeric_result *= multiplier 
		alphanumeric_result = "{:,d} IU / mL".format(numeric_result)
		suppressed = 1 if numeric_result<1000 else 2
	else:
		numeric_result = get_numeric_result(result)
		numeric_result *= multiplier
		alphanumeric_result = "{:,d} IU / mL".format(numeric_result)
		suppressed = 1 if numeric_result<1000 else 2	

	return {
			'numeric_result':numeric_result, 
			'alphanumeric_result':alphanumeric_result, 
			'suppressed': suppressed,
			'repeat_test': repeat_test,
			}

def get_result2(result, multiplier, machine_type):
	result = result.strip() if type(result) is str else result
	numeric_result = 0
	alphanumeric_result = ''
	suppressed = 3
	if not multiplier:
		multiplier = 1

	if eq(result,'Target Not Detected') or eq(result,'Not detected'):
		numeric_result = 0
		alphanumeric_result = result
		suppressed = 1
	elif eq(result,'invalid') or eq(result, 'failed') or utils.isnan(result) or result == '':
		numeric_result = 0
		alphanumeric_result = 'Failed'
		suppressed = 3
	elif result.startswith('<') or result.startswith('>'):
		numeric_result = get_numeric_result(result)
		suppressed = 1 if numeric_result<1000 else 2
		alphanumeric_result = "%s {:,d} Copies / mL".format(numeric_result) %result[0]
	else:
		numeric_result = get_numeric_result(result)
		numeric_result *= multiplier
		if machine_type=='A' and result.find('Copies')==-1:
			numeric_result = 0
			alphanumeric_result = 'Failed'
			suppressed = 3 
		elif numeric_result > 10000000:
			suppressed = 2
			alphanumeric_result = "> 10,000,000 Copies / mL"
		else:
			alphanumeric_result = "{:,d} Copies / mL".format(numeric_result)
			suppressed = 1 if numeric_result<1000 else 2	

	return {
			'numeric_result':numeric_result, 
			'alphanumeric_result':alphanumeric_result, 
			'suppressed': suppressed,
			}

def get_numeric_result(result):
	numeric_result = 0
	result_new = result.replace('Copies / mL', '')
	result_new = result_new.replace(' ', '')
	result_new = result_new.replace(',', '')
	result_new = result_new.replace('>', '')
	result_new = result_new.replace('<', '')
	result_new = result_new.replace(')', '')
	result_new = result_new.replace('(', '')
	result_new = result_new.replace('Log', '')
	try:
		numeric_result = int(float(result_new))
	except :
		pass
	return numeric_result

def eq(a,b):
	return a.upper() == b.upper()