from home import utils
from worksheets.models import Worksheet,WorksheetSample, ResultRunDetail, MACHINE_TYPES,ResultRun
from django.utils import timezone
from django.db.models import Q
from . import utils as result_utils
from django.core.exceptions import ObjectDoesNotExist


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
				"Failed Internal control cycle number is too high. Valid range is [18.48, 22.48].",
				"Failed Failed Internal control cycle number is too high. Valid range is [18.48,",
				"Failed Failed Internal control cycle number is too high. Valid range is [18.48, 2",
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


def get_result(result, multiplier,machine_type,is_diluted,sample_type,sample_volume=200):
	
	numeric_result = 0
	alphanumeric_result = ''
	suppressed = 3
	repeat_test = 2
	sup_cut_off_dict = {
    	'id': None,
    	'name': ''
    }

	if utils.isnan(result) or result == '':
		result = 'Failed' 
	if eq(result,'Target Not Detected') or eq(result,'Not detected'):
		numeric_result = 0
		alphanumeric_result = 'Target Not Detected'
		suppressed = 1
	elif eq(result,'invalid') or eq(result, 'failed') or utils.isnan(result) or result == '':
		numeric_result = 0
		alphanumeric_result = 'Failed'
		suppressed = 3
		repeat_test = 3
	elif eq(result, '< Titer min'):
		if sample_volume is not None and sample_volume == 500:
			numeric_result = 20
			alphanumeric_result = '< 20.00 Copies / mL'
		else:
			numeric_result = 50
			alphanumeric_result = '< 50.00 Copies / mL'
	elif eq(result, '> Titer max'):
		numeric_result = 10000000
		alphanumeric_result = '> 10,000,000 Copies / mL'
		suppressed = 2
	elif result.startswith('<') or result.startswith('>'):
		if(machine_type =='N'):
			numeric_result = get_alinity_numeric_result(result)
		else:
			numeric_result = get_numeric_result(result)
		alphanumeric_result = "%s {:,d} Copies / mL".format(numeric_result) %result[0]
	elif result[-5:] == 'cp/ml':
		numeric_result = int(float(result[:-6]))
		#numeric_result *= multiplier
		alphanumeric_result = "{:,d} Copies / mL".format(numeric_result)
	else:
		if(machine_type == 'N'):
			numeric_result = get_alinity_numeric_result(result)
		else:
			numeric_result = get_numeric_result(result)
		#numeric_result = numeric_result*multiplier
		if numeric_result > 10000000:
			suppressed = 2
			alphanumeric_result = "> 10,000,000 Copies / mL"
		else:
			alphanumeric_result = "{:,d} Copies / mL".format(numeric_result)
			
			
	if is_diluted == 1 and not result.startswith('<') and not result.startswith('>'):
		numeric_result = numeric_result*2
		if numeric_result != 0:
			alphanumeric_result = "{:,d} Copies / mL".format(numeric_result)
	
	
	if sample_type is None:
		suppressed = 4
		suppression_cut_off_int = 0
		supression_cut_off = 0
	else:
		sup_cut_off_dict = utils.getSupressionCutOff(sample_type)
		suppression_cut_off_int = int(sup_cut_off_dict['appendix'])
		suppressed = 1 if numeric_result <= suppression_cut_off_int else 2
		supression_cut_off = int(sup_cut_off_dict['id'])
		
	return {
			'numeric_result':numeric_result,
			'alphanumeric_result':alphanumeric_result,
			'suppressed': suppressed,
			'rep_test': repeat_test,
			'has_low_level_viramia':has_ll_viramia(numeric_result,machine_type,sample_type,suppression_cut_off_int),
			'supression_cut_off':supression_cut_off
			}

def has_ll_viramia(numeric_result,machine_type,sample_type,supp_cut_off_val):
	if not sample_type:
		return 3
	else:
		if numeric_result < 1000 and numeric_result >= supp_cut_off_val:
			return 1
		else:
			return 0

def get_result2(result, multiplier, machine_type):
	result = result.strip() if type(result) is str else result
	numeric_result = 0
	alphanumeric_result = ''
	suppressed = 3
	repeat_test = 2
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
		repeat_test = 3
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
			'repeat_test':repeat_test,
			}

def get_numeric_result(result):
	numeric_result = 0
	rresult_new = result.strip()
	result_new = result.replace('Copies / mL', '')
	# result_new = result.replace('Copies/mL', '')
	result_new = result_new.replace('detected', '')
	result_new = result_new.replace(' ', '')
	result_new = result_new.replace(',', '')
	result_new = result_new.replace('>', '')
	result_new = result_new.replace('<', '')
	result_new = result_new.replace(')', '')
	result_new = result_new.replace('(', '')
	result_new = result_new.replace('Log', '')
	# result_new = result_new.strip()
	try:
		numeric_result = int(float(result_new))
	except :
		pass
	return numeric_result

def eq(a,b):
	return a.upper() == b.upper()

def get_alinity_numeric_result(result):
	numeric_result = 0
	rresult_new = result.strip()
	result_new = result.replace('Copies / mL', '')
	result_new = result.replace('Copies/mL', '')
	result_new = result_new.replace('detected', '')
	result_new = result_new.replace(' ', '')
	result_new = result_new.replace(',', '')
	result_new = result_new.replace('>', '')
	result_new = result_new.replace('<', '')
	result_new = result_new.replace(')', '')
	result_new = result_new.replace('(', '')
	result_new = result_new.replace('Log', '')
	result_new = result_new.strip()
	try:
		numeric_result = int(float(result_new))
	except :
		pass
	return numeric_result


def eq(a,b):
	return a.upper() == b.upper()

def generate_radios(ws_id):
	redio_inputs = "<label><input type='radio' required='true' name='choices{0}' class='choices r' res_pk='{0}' value='release'> Release</label>".format(ws_id,ws_id)
	redio_inputs = redio_inputs+"<label><input type='radio' required='true' name='choices{0}' class='choices' res_pk={0} value='retain'> Retain</label>".format(ws_id,ws_id)	
	redio_inputs = redio_inputs+"<div class='comments' id='comments_sect{0}'> <input type='text'  name='comments{0}' placeholder='comments' id='comment{0}' class='comments_input' res_pk='{0}' value=''></div>".format(ws_id,ws_id,ws_id,ws_id)
	return redio_inputs

def get_result_run(filename,user):
	rn = ResultRun.objects.filter(file_name=filename).first()
	if not rn:
		rn = ResultRun()
		rn.file_name = filename
		rn.upload_date = timezone.now()
		rn.run_uploaded_by=user
		rn.stage=1
		rn.save()
	if rn.stage == 3:
		rn = 'completed'
	return rn

def update_sample_and_save_result(machine_type,instrument_id,result, multiplier, user, test_date,result_run,row_index,the_test_date):
	ins_filter = Q(instrument_id=instrument_id) | Q(other_instrument_id=instrument_id)
	stage_filter = Q(stage__lte=3) | Q(stage=4)
	sample_volume = 200
	ws = WorksheetSample.objects.filter(ins_filter & stage_filter).first()
	result_run_detail = {
		'numeric_result':'',
		'alphanumeric_result':''
	}
	if ws:
		try:
			# First verify sample exists before doing anything
			sample = ws.sample
			# Now we can safely access sample attributes
			if not sample or not hasattr(sample, 'sample_type') or sample.sample_type is None:
				raise ObjectDoesNotExist("Sample exists but sample_type is invalid")
			result_dict = result_utils.get_result(
	            result, 
	            multiplier,
	            machine_type,
	            ws.is_diluted,
	            sample.sample_type, # Use the already fetched sample object
	            sample_volume
	        )
			#result_dict = result_utils.get_result(result, multiplier,machine_type,ws.is_diluted,ws.sample.sample_type)
			
			the_test_date = timezone.now()
			#save a copy of the result_run results
			#helpful if the instrument_id was not partially captured on the testing platform
			result_run_detail = ResultRunDetail.objects.filter(the_result_run_id= result_run.id,instrument_id=instrument_id).first()
			if not result_run_detail:
				result_run_detail = ResultRunDetail.objects.create(			
					result_numeric = result_dict.get('numeric_result'),
					result_alphanumeric = result_dict.get('alphanumeric_result'),
					result_run_position = row_index,
					test_date = the_test_date,
					testing_by = user,
					the_result_run_id= result_run.id,
					instrument_id=instrument_id
					)
			result = result.strip() if type(result) is str else result
			#only upload results where stage is 1, meaning awaiting results or stage is 4, meaning repeat waiting for results
			if ws.stage == 1 or ws.stage == 4:
				# Update worksheet fields that don't depend on sample
				ws.repeat_test = result_dict.get('rep_test')
				ws.result_numeric = result_dict.get('numeric_result')
				alf_num_result = result_dict.get('alphanumeric_result')
				ws.result_alphanumeric = alf_num_result
				ws.suppressed = result_dict.get('suppressed')
				ws.method = machine_type
				ws.result_run_detail_id = result_run_detail.id
				ws.test_date = the_test_date
				ws.tester = user
				ws.stage = 2
				
				# Update sample fields
				sample.stage = 2
				ws.supression_cut_off_id = result_dict.get('supression_cut_off')
				ws.has_low_level_viramia = result_dict.get('has_low_level_viramia')

				# Handle Failed case
				if alf_num_result == 'Failed':
					ws.repeat_test = 1
					ws.stage = 4
					sample.stage = 4
					ws.authorised_at = timezone.now()
					ws.authoriser = user
		            
		        # Handle stage 4 non-Failed case
				if ws.stage == 4 and alf_num_result != 'Failed':
					ws_igno = WorksheetSample()
					ws_igno.stage = 9
					ws_igno.save()
		            
				# Save both objects
				sample.save()
				ws.result_run = result_run
				ws.result_run_position = row_index
				ws.save()
		        
		except ObjectDoesNotExist:
			# Handle invalid sample case
			import logging
			logger = logging.getLogger(__name__)
			logger.error(f"Invalid sample reference in worksheet {ws.id}")
	        
	        # Clear the invalid reference and save minimal worksheet info
			ws.sample_id = None
			ws.save()
		

#update sample run with information of contamination.
def update_run_with_contamination_info(result_run):
	no_of_res_gte_1k = ResultRunDetail.objects.filter(the_result_run=result_run,result_numeric__gte=settings.CONTAMINATION_CHECK_NUMERIC_VALUE).count()
	#get samples on the run
	result_run_details = ResultRunDetail.objects.filter(the_result_run=result_run).order_by('result_run_position')
	#less the adjancent number of results for contamination by 1 because indices in the loop start from 0
	no_of_adjance_results_for_contamination = settings.NUMBER_OF_RESULTS_FOR_ADJANCENCY_CONTAMINATION_CHECK - 1
	is_run_contaminated = 0
	no_results = len(result_run_details)

	indices_arr = []
	if no_results >= no_of_adjance_results_for_contamination:
		counter = 0
		for res in result_run_details:
			#get the cohorts for adjacency contamination check
			cohort_check = []
			if counter <= (no_results-no_of_adjance_results_for_contamination):
				result_indices_for_comparison = utils.get_indices(indices_arr,no_of_adjance_results_for_contamination,counter)
				for i in result_indices_for_comparison:
					cohort_check.append(result_run_details[i])
					#print(result_run_details[i].result_run_position)
				#now compare thes for sample
				is_run_contaminated = compare_results_for_adjacency_contamination(cohort_check,no_of_adjance_results_for_contamination)
				if is_run_contaminated:
					break
				counter += 1
			else:
				break

	#udate the run information
	result_run.has_squential_samples_with_more_than_thou_copies = is_run_contaminated
	result_run.samples_with_more_than_thou_copies = no_of_res_gte_1k
	result_run.save()
	return True

def compare_results_for_adjacency_contamination(cohort,no_of_adjance_results_for_contamination):
	value_is_gte = 0
	for c in cohort:
		#c = cohort[i]
		if c.result_numeric < settings.CONTAMINATION_CHECK_NUMERIC_VALUE:
			return 0
		else:
			value_is_gte = 1
		return value_is_gte

def single_space(value):
	return " ".join(value.strip().split())