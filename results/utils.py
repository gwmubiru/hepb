

def repeat_test(machine_type, result, flag):
	repeat = False
	if machine_type == 'R':
		repeat = True if result == 'Invalid' or result == 'Failed' else False
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

		repeat == (result in repeat_list_results) or (flag in repeat_list_flags) 

	return repeat