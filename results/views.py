import csv, pandas, io, json, math, os as SI
import openpyxl
#from datetime import *
from datetime import datetime as dt, timedelta,date
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction
from django.db import models
from django.db.models import Q
from django.contrib.auth.decorators import permission_required
from backend.models import Appendix,Facility,MedicalLab
from home import utils
from home import programs
from .forms import UploadForm, CobasUploadForm
from worksheets.models import Worksheet,WorksheetSample, ResultRunDetail, MACHINE_TYPES,ResultRun
from samples.models import Sample
from .models import Result,ResultsQC
from . import utils as result_utils
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import connections
from django.utils.text import slugify

import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.exceptions import ObjectDoesNotExist

def _normalize_dataframe_columns(reader):
	reader = reader.rename(
		columns=lambda col: col.strip() if isinstance(col, str) else col
	)
	return reader

def _get_row_value(row, *column_names, default=''):
	for column_name in column_names:
		if column_name in row.index:
			return row[column_name]
	return default

def get_anomalies(request, machine_type):
	#return HttpResponse(SI.StringIO(request.FILES['results_file'].read()))
	uploaded_file = request.FILES['results_file']
	ext = os.path.splitext(uploaded_file.name)[1]

	tmp_name = "/tmp/%s"%uploaded_file.name
	with open(tmp_name, 'wb+') as destination:
		for chunk in uploaded_file.chunks():
			destination.write(chunk)

	if machine_type == 'R' or machine_type == 'C' or machine_type == 'S':
		if not utils.eq(ext, '.csv'):
			return HttpResponse("<b>Expecting a .csv, but we are getting %s</b>"%ext)
		reader = pandas.read_csv(tmp_name, sep=',')
		sample_ids = tuple(reader["Sample ID"])
	elif machine_type == 'H':
		reader = pandas.read_csv(tmp_name, sep='\t')
		if not utils.eq(ext, '.lis'):
			return HttpResponse("<b>Expecting a .lis, but we are getting %s</b>"%ext)
		sample_ids = tuple(reader["Specimen Barcode"])
	else:
		if not utils.eq(ext, '.txt'):
			return HttpResponse("<b>Expecting a .txt, but we are getting %s</b>"%ext)
		reader = pandas.read_csv(tmp_name, sep='\t', skiprows=20)

		sample_ids = tuple(reader["SAMPLE ID"])

	return HttpResponse(0)


def store_result(machine_type, sample, result, multiplier, user, test_date,test='',worksheet_sample_id=''):
	#result = 'failed' if utils.isnan(result) else result
	if pandas.isna(result) or utils.isnan(result):
		result = 'failed'
	if sample:
		sample_result, sr_created = Result.objects.get_or_create(sample=sample)
		if sample_result.result1 == '':
			sample_result.result1 = result
		elif sample_result.result2 == '':
			sample_result.result2 = result
		elif sample_result.result3 == '':
			sample_result.result3 = result
		elif sample_result.result4 == '':
			sample_result.result4 = result
		else:
			sample_result.result5 = result
		result_dict = result_utils.get_result(result, multiplier,machine_type, sample.sample_type)
		sample_result.repeat_test = result_dict.get('rep_test')
		sample_result.result_numeric = result_dict.get('numeric_result')
		sample_result.result_alphanumeric = result_dict.get('alphanumeric_result')
		sample_result.suppressed = result_dict.get('suppressed')
		sample_result.supression_cut_off = result_dict.get('supression_cut_off')
		sample_result.method = machine_type

		if(machine_type == 'H'):
			sample_result.test_date = timezone.now()
		else:
			sample_result.test_date = test_date.strftime("%Y-%m-%d %H:%M:%S.%f")
		sample_result.result_upload_date = timezone.now()
		sample_result.test_by = user
		if worksheet_sample_id:
			sample_result.worksheet_sample_id = worksheet_sample_id
		sample_result.save()


def handle_files(form, user, request):
    files = request.FILES.getlist('results_file')
    m_type = request.POST.get('machine_type')
    multiplier = form.cleaned_data.get('multiplier')
    
    # Ensure results directory exists
    results_dir = os.path.join(settings.MEDIA_ROOT, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    for uploaded_file in files:
        try:
            # 1. Safer file path construction
            file_name = default_storage.get_valid_name(uploaded_file.name)
            tmp_name = os.path.join(results_dir, file_name)
            
            # 2. Check for existing result run first (before file operations)
            result_run = get_result_run(file_name, user)
            if result_run == 'completed':
                return HttpResponse('This file has already been used')
            
            # 3. More efficient file saving with Django's storage API
            with default_storage.open(tmp_name, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # 4. Process file based on machine type
            if m_type == 'R':
                self._process_type_r(tmp_name, result_run, m_type, multiplier, user, request)
            else:
                self._process_other_types(tmp_name, result_run, m_type, multiplier, user, uploaded_file.name)
            
            # 5. Save and update run
            result_run.save()
            update_run_with_contamination_info(result_run)
            
            return redirect(f'/worksheets/authorize_runs/?stage=1&auth_by=runs&run_id={result_run.pk}&stage=1&tab=received')
            
        except Exception as e:
            # Clean up if something went wrong
            if 'tmp_name' in locals() and os.path.exists(tmp_name):
                os.unlink(tmp_name)
            logger.error(f"Error processing file {uploaded_file.name}: {str(e)}")
            return HttpResponse(f"Error processing file: {str(e)}", status=500)

def _process_type_r(self, file_path, result_run, m_type, multiplier, user, request):
	"""Process files for machine type R"""
	try:
		with open(file_path, 'rb') as f:
			reader = pd.read_csv(f)
			test_date = reader.iloc[0]["Detection End Date/Time"]
			# Parse date based on format
			date_format = request.POST.get('date_format')
			date_formats = {
                "1": '%Y/%m/%d %H:%M:%S',
                "2": '%m/%d/%Y %H:%M',
                "default": '%d/%m/%Y %H:%M'
            }
			fmt = date_formats.get(date_format, date_formats["default"])
			test_date = datetime.strptime(test_date, fmt)
			# Process rows
			for index, data in reader.iterrows():
				self._process_row(data, result_run, m_type, multiplier, user, test_date, index, is_type_r=True)
	except Exception as e:
		logger.error(f"Error processing R-type file {file_path}: {str(e)}")
		raise

def _process_other_types(self, file_path, result_run, m_type, multiplier, user, original_filename):
	"""Process files for other machine types"""
	try:
		with open(file_path, 'rb') as f:
			# Read header info
			reader0 = pd.read_csv(f, sep='\t', skiprows=6, nrows=1, header=None)
			test_date = datetime.strptime(reader0.iloc[0][1], '%d/%m/%Y  %I:%M:%S %p')
			# Reset file pointer and read main data
			f.seek(0)
			reader = pd.read_csv(f, sep='\t', skiprows=20)
			# Extract serial number
			serial_no = original_filename[:17][-9:]
			# Process rows
			for index, data in reader.iterrows():
				self._process_row(data, result_run, m_type, multiplier, user, test_date, index, 
    				is_type_r=False, serial_no=serial_no)
	except Exception as e:
		logger.error(f"Error processing file {file_path}: {str(e)}")
		raise

def _process_row(self, data, result_run, m_type, multiplier, user, test_date, index, 
                is_type_r=False, serial_no=None):
	"""Process a single row of data"""
	if is_type_r:
		result = data["Result"]
		instrument_id = data["Sample ID"]
		sample_location = data["SAMPLE LOCATION"]
	else:
		result = data.get("RESULT")
		instrument_id = data.get("SAMPLE ID")
		sample_location = data["SAMPLE LOCATION"]
		reagent_lot = data["REAGENT LOT NUMBER"]
		reagent_expiry_date = data["REAGENT LOT EXPIRATION DATE"]

	# Clean instrument ID
	instrument_id = instrument_id.strip() if isinstance(instrument_id, str) else instrument_id
	# Handle control samples
	if sample_location == 'A1':
		result_run.negative_ctrl = result
	elif sample_location == 'B1':
		result_run.low_positive_ctrl = result
	elif sample_location == 'C1' and not is_type_r:
		result_run.high_positive_ctrl = result
		result_run.reagent_expiry_date = utils.get_mysql_from_uk_date(reagent_expiry_date)
		result_run.reagent_lot = reagent_lot
		result_run.serial_number = serial_no

	# Process regular samples
	if sample_location not in ['A1', 'B1', 'C1']:
		update_sample_and_save_result(
            m_type, instrument_id, result, multiplier, 
            user, test_date, result_run, index
        )

def update_sample_and_save_result(machine_type,instrument_id,result, multiplier, user, test_date,result_run,row_index,sample_volume='',active_program_code=None):
	if user.userprofile.medical_lab_id == 2:
		save_upload_result(result, multiplier,machine_type,instrument_id,user)
		return 0
	ins_filter = Q(instrument_id=instrument_id) | Q(other_instrument_id=instrument_id)
	stage_filter = Q(stage__lte=3) | Q(stage=4)
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
	            sample_volume,
	            active_program_code
	        )
			#result_dict = result_utils.get_result(result, multiplier,machine_type,ws.is_diluted,ws.sample.sample_type)
			if(machine_type == 'H'):
				the_test_date = timezone.now()
			else:
				the_test_date = test_date.strftime("%Y-%m-%d %H:%M:%S.%f")
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

def save_upload_result(result, multiplier,machine_type,instrument_id,user):
	sample = Sample.objects.filter(barcode=instrument_id).first()
	if sample and sample.is_data_entered ==1:
		result_dict = result_utils.get_result(result, multiplier,machine_type,0,sample.sample_type)
		the_test_date = timezone.now()
		result = Result()
		result.repeat_test = 2
		result.authorised = 1
		result.result1 = result_dict.get('alphanumeric_result')
		result.result_numeric = result_dict.get('numeric_result')
		result.failure_reason = ''
		result.method = machine_type
		result.test_date = the_test_date
		result.authorised_at = the_test_date
		result.authorised_by_id = user.id
		result.test_by_id = user.id
		result.sample_id = sample.id
		result.suppressed = result_dict.get('suppressed')
		result.supression_cut_off_id = result_dict.get('supression_cut_off')
		result.has_low_level_viramia = result_dict.get('has_low_level_viramia')
		result.save()
		#set release date based on whether sample's data is entered
		
		other_params = {
			'released': True,
			'comments': '',
			'released_by': user,
			'released_at': timezone.now(),
			'qc_date': timezone.now(),
		}
		rqc, rqc_created = ResultsQC.objects.update_or_create(result=result, defaults=other_params)


def compare_results_for_adjacency_contamination(cohort,no_of_adjance_results_for_contamination):
	value_is_gte = 0
	for c in cohort:
		#c = cohort[i]
		if c.result_numeric < settings.CONTAMINATION_CHECK_NUMERIC_VALUE:
			return 0
		else:
			value_is_gte = 1
		return value_is_gte


@permission_required('worksheets.add_worksheet', login_url='/login/')
def upload(request):

	if(request.method == 'POST'):
		form = UploadForm(request.POST, request.FILES)
		if form.is_valid():
			upload = form.save(commit=False)
			upload.uploaded_by = request.user
			upload.multiplier = form.cleaned_data.get('multiplier')

			handle_files(form, request.user, request)

			return redirect('worksheets:authorize_runs')


	form = UploadForm(initial={'multiplier':1})

	return render(request, 'results/upload.html', {'form': form, 'mtype': request.POST.get('type')})



@permission_required('worksheets.add_worksheet', login_url='/login/')
@transaction.atomic
def alinity_upload(request):
	if(request.method == 'POST'):
		form = UploadForm(request.POST, request.FILES)
		if form.is_valid():
			upload = form.save(commit=False)
			user = request.user
			upload.uploaded_by = user
			upload.multiplier = form.cleaned_data.get('multiplier')

			upload = form.save(commit=False)
			files = request.FILES.getlist('results_file')
			for uploaded_file in files:
				tmp_name = settings.MEDIA_ROOT+"results/%s"%uploaded_file.name
				high_positive_ctrl = ''
				low_positive_ctrl = ''
				negative_ctrl = ''
				#save the result run sample run
				result_run = get_result_run(uploaded_file.name,user)
				if result_run == 'completed':
					return HttpResponse('This file has already been used')
				with open(tmp_name, 'wb+') as destination:
					for chunk in uploaded_file.chunks():
						destination.write(chunk)
				mtype = request.POST.get('machine_type')

				reader = pandas.read_excel(tmp_name, sheet_name=0, header=0)

				no_of_lines = len(reader)
				for row in reader.iterrows():
					index, data = row

					result = data["Final Result Value"]
					instrument_id = data["Sample ID"]
					
					if index == 1:
						result_run.reagent_lot = data["Amp Kit Lot Number"]
						result_run.serial_number = data["System Serial Number"]
						result_run.reagent_expiry_date = dt.strptime(data["Amp Kit Lot Expiration Date"], '%m.%d.%Y  %I:%M %p')						
						result_run.save()

					multiplier = form.cleaned_data.get('multiplier')
					#use the current date as the date of upload
					test_date =  timezone.now()

					update_sample_and_save_result('N',instrument_id,result, multiplier, user, test_date,result_run,index)


				update_run_with_contamination_info(result_run)
			return redirect('/worksheets/authorize_runs/?stage=1&auth_by=runs&run_id=%d&stage=1&tab=received' %result_run.pk)
	else:
		form = UploadForm(initial={'multiplier':1})

	return render(request, 'results/cobas_upload.html', {'form': form})

@permission_required('worksheets.add_worksheet', login_url='/login/')
@transaction.atomic
def override_results(request):
	return HttpResponse('Not yet ready for this')
	if(request.method == 'POST'):
		form = UploadForm(request.POST, request.FILES)
		if form.is_valid():
			upload = form.save(commit=False)
			user = request.user
			upload.uploaded_by = user
			upload.multiplier = form.cleaned_data.get('multiplier')

			upload = form.save(commit=False)
			files = request.FILES.getlist('results_file')
			for uploaded_file in files:
				tmp_name = settings.MEDIA_ROOT+"results/%s"%uploaded_file.name
				high_positive_ctrl = ''
				low_positive_ctrl = ''
				negative_ctrl = ''
				#save the result run sample run
				result_run = get_result_run(uploaded_file.name,user)
				if result_run == 'completed':
					return HttpResponse('This file has already been used')
				with open(tmp_name, 'wb+') as destination:
					for chunk in uploaded_file.chunks():
						destination.write(chunk)
				mtype = 'N'

				reader = pandas.read_excel(tmp_name, sheet_name=0, header=0)

				no_of_lines = len(reader)
				for row in reader.iterrows():
					index, data = row

					result = data["RESULTS"]
					instrument_id = data["LOCATOR ID"]
					#get the affected result
					multiplier = 1
					#use the current date as the date of upload
					test_date =  timezone.now()
					result_dict = result_utils.get_result(result, multiplier,machine_type,0,'ws.sample.sample_type')
									
			return redirect('/worksheets/authorize_runs/?stage=1&auth_by=runs&run_id=%d&stage=1&tab=received' %result_run.pk)
	else:
		form = UploadForm(initial={'multiplier':1})

	return render(request, 'results/override_results.html', {'form': form})

@permission_required('worksheets.add_worksheet', login_url='/login/')
@transaction.atomic
def cobas_upload(request):
	if(request.method == 'POST'):
		active_program_code = programs.get_active_program_code(request)
		
		files = request.FILES.getlist('results_file')
		for uploaded_file in files:
			tmp_name = settings.MEDIA_ROOT+"results/%s"%uploaded_file.name
			high_positive_ctrl = ''
			low_positive_ctrl = ''
			negative_ctrl = ''
			#save the result run sample run
			result_run = get_result_run(uploaded_file.name,request.user)
			#return HttpResponse(result_run)
			if result_run == 'completed':
				return HttpResponse('This file has already been used')
			#with open(tmp_name, 'r', encoding='utf-8') as f:
			#	reader = csv.DictReader(f)
			#	print("Column names:", reader.fieldnames)
			#return HttpResponse('te')
			with open(tmp_name, 'wb+') as destination:
				for chunk in uploaded_file.chunks():
					destination.write(chunk)

			mtype = request.POST.get('mtype')
			if mtype == 'H':
				process_hologic(uploaded_file.name,tmp_name, request)
			else:
				reader = _normalize_dataframe_columns(pandas.read_csv(tmp_name, sep=','))
				no_of_lines = len(reader)
				multiplier = 1
				user = request.user
				for row in reader.iterrows():
					index, data = row

					test = data["Test"]
					instrument_id = str(data["Sample ID"])
					sample_volume_value = _get_row_value(
						data,
						"Sample volume (µL)",
						"Sample volume (µL) ",
						"Sample volume (uL)",
						default='',
					)
					sample_volume = int(sample_volume_value) if str(sample_volume_value).strip() else ''
					#get the controls
					
					if mtype == 'S':
						if index == 1:
							result_run.high_positive_ctrl = data["Result"]
							result_run.save()
						if index == 2:
							result_run.low_positive_ctrl = data["Result"]
							result_run.save()
						if index == 0:
							result_run.negative_ctrl = data["Result"]
							result_run.save()

						result = data["Result"]
					else:
						result = data["Target 1"]
						if index == (no_of_lines-3):
							result_run.high_positive_ctrl = data["Target 1"]
							result_run.save()
						if index == (no_of_lines-2):
							result_run.low_positive_ctrl = data["Target 1"]
							result_run.save()
						if index == (no_of_lines-1):
							result_run.negative_ctrl = data["Target 1"]
							result_run.save()
						result_run.serial_number = data["Instrument"]


					#if instrument_id and instrument_id.strip():
					if instrument_id and not instrument_id.startswith("C") and not instrument_id.startswith("HI"):

						date_format = request.POST.get('date_format')
						if mtype == 'S':
							#start_date = dt.strptime(data["Custom date"], '%Ym%md%d %H:%M:%S')
							dt_str = data["Result creation date/time"]
							santized_date = result_utils.single_space(dt_str)
							if date_format=="1":
								start_date = dt.strptime(santized_date, '%d-%b-%Y  %I:%M:%S %p')
							else:
								start_date = dt.strptime(santized_date, '%m/%d/%Y %H:%M')
						else:
							dt_str = data["Date/time"]
							santized_date = result_utils.single_space(dt_str)
							if date_format=="1":
								start_date = dt.strptime(santized_date, '%d-%b-%Y  %I:%M:%S %p')
							else:
								start_date = dt.strptime(santized_date, '%m/%d/%Y %H:%M')

							test_date =  start_date + timedelta(hours=3)
							update_sample_and_save_result('C',instrument_id,result, multiplier, user, test_date,result_run,index,sample_volume,active_program_code)
						
				update_run_with_contamination_info(result_run)
				
			
		return redirect('/worksheets/authorize_runs/?stage=1&auth_by=runs')
		#return redirect('/worksheets/authorize_runs/?stage=1&auth_by=runs&run_id=%d&stage=1&tab=received' %result_run.pk)

	else:
		form = CobasUploadForm(initial={'multiplier':1})

	return render(request, 'results/cobas_upload.html', {'form': form})

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

def process_hologic(actual_file_name,tmp_name, request):
	reader = pandas.read_csv(tmp_name, sep='\t')
	test_date = reader.iloc[0]["Completion Time UTC"]
	test_date = timezone.now()
	multiplier = request.POST.get('multiplier')
	active_program_code = programs.get_active_program_code(request)
	result_run = ResultRun.objects.filter(file_name=actual_file_name).first()
	
	reagent_expiry_date = reader.iloc[5]["Assay Reagent Kit ML Exp Date UTC"]
	if not result_run:
		result_run, result_run_created = ResultRun.objects.create(
				defaults={'file_name':actual_file_name},
				upload_date = timezone.now(),
				run_uploaded_by=request.user,
				low_positive_ctrl = reader.iloc[3]["Interpretation 1"],
				high_positive_ctrl = reader.iloc[4]["Interpretation 1"] ,
				negative_ctrl = reader.iloc[5]["Interpretation 1"],
				reagent_lot = reader.iloc[5]["Assay Reagent Kit ML #"],
				reagent_expiry_date = datetime.strptime(reagent_expiry_date, '%d-%B-%y %H:%M:%S'),
				serial_number = reader.iloc[5]["Serial Number"],
				)
	for row in reader.iterrows():
		index, data = row
		result = data['Interpretation 1'] if data['Interpretation 4']=='Valid' else 'Invalid'
		vl_sample_id = data['Specimen Barcode']
		analyte = data['Analyte']
		vl_sample_id = vl_sample_id.strip() if type(vl_sample_id) is str else vl_sample_id
		result_run.reagent_lot = data['Assay Reagent Kit ML #']
		result_run.serial_number = data['Serial Number']
		reagent_expiry_date = data['Assay Reagent Kit ML Exp Date UTC']
		#result_run.reagent_expiry_date = dt.strptime(reagent_expiry_date, '%d-%b-%y %H:%M:%S')
		if analyte == 'HIV-1':
			update_sample_and_save_result('H',vl_sample_id,result, multiplier, request.user, test_date,result_run,index,active_program_code=active_program_code)
	result_run.save();	
	update_run_with_contamination_info(result_run)


def list(request):
	search_val = request.GET.get('search_val')

	if search_val:
		worksheets = Worksheet.objects.filter(worksheet_reference_number__contains=search_val).order_by('-pk')[:1]
		if worksheets:
			worksheet = worksheets[0]
			return redirect('/results/worksheet/%d' %worksheet.pk)

	worksheets = Worksheet.objects.all()
	return render(request,'worksheets/list.html',{'worksheets':worksheets})

def worksheet_results(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	return render(request, 'results/worksheet_results.html', {'worksheet':worksheet})

@permission_required('results.add_resultsqc', login_url='/login/')
def release_list(request, machine_type):
	tab = request.GET.get('tab')
	if tab=='released':
		filters = Q(stage=4, machine_type=machine_type,worksheet_medical_lab=utils.user_lab(request))
	else:
		filters = Q(stage=3, machine_type=machine_type,worksheet_medical_lab=utils.user_lab(request))

	worksheets = Worksheet.objects.filter(filters).order_by("-pk")
	context = {'worksheets':worksheets, 'machine_type':dict(MACHINE_TYPES).get(machine_type)}
	return render(request,'results/release_list.html',context)

@permission_required('results.add_resultsqc', login_url='/login/')
@transaction.atomic
def release_results(request):
	r_tab = request.GET.get('tab')
	facility_id = request.GET.get('facility_id')
	sample_type = request.GET.get('sample_type')
	envelope_id = request.GET.get('envelope_id')
	run_id = request.GET.get('run_id')
	facilities = Facility.objects.all()
	if envelope_id:
		filters = Q(sample__envelope__id = envelope_id,stage=3,id__gte=settings.WORKSHEET_SAMPLES_CUT_OFF)
	else:
		filters = Q(stage=3, sample__sample_type=sample_type, id__gte=settings.WORKSHEET_SAMPLES_CUT_OFF)

	if r_tab == 'received':
		filters = filters & Q(sample__is_data_entered = 1)
	elif r_tab == 'pending_data_entry':
		filters = filters & Q(sample__is_data_entered = 0)
	elif r_tab == 'not_received':
		filters = filters & Q(sample_id__isnull=True)

	if facility_id:
		filters = filters & Q(sample__facility_id=facility_id)
	
	if request.GET.get('complete_run'):
		ResultRun.objects.filter(id=run_id).update(stage=3)
		return redirect('/worksheets/authorize_runs/?stage=1&auth_by=runs')

	ws = WorksheetSample.objects.filter(filters).order_by('result_run_position')
	page = request.GET.get('page', 1)
	paginator = Paginator(ws, 10)
	try:
		worksheetsamples = paginator.page(page)
	except PageNotAnInteger:
		worksheetsamples = paginator.page(1)
	except EmptyPage:
		worksheetsamples = paginator.page(paginator.num_pages)

	if request.method == 'POST':
		if request.POST.get('post_type') == 'single':
			si_pk = request.POST.get('sample_pk')
			if si_pk:
				#get the last worksheet sample for the sample
				ws = WorksheetSample.objects.filter(sample_id=_clean_autopk_value(si_pk), stage=4).last()

			else:
				ws = WorksheetSample.objects.filter(pk=_clean_autopk_value(request.POST.get('result_pk'))).first()
			release_retain_result(ws, request.POST.get('choice_type'),request.POST.get('comments'),
				request.POST.get('completed'), request.user,request.POST.get('reason'))
			return HttpResponse("saved")
		elif request.POST.get('post_type') == 'full_run':
			#get all worksheets on run
			result_run = ResultRun.objects.filter(pk=_clean_autopk_value(request.POST.get('run_id'))).first()
			worksheet_samples = WorksheetSample.objects.filter(result_run_detail__the_result_run = result_run)
			if result_run is not None:
				result_run.stage = 3
				result_run.save()
			for ws in worksheet_samples:
				release_retain_result(ws, request.POST.get('choice_type'),'','', request.user)
			return HttpResponse("saved")
		else:

			#save the multiple approvals
			worksheet_samples = request.POST.getlist('worksheet_samples')
			for ws_id in worksheet_samples:
				ws = WorksheetSample.objects.filter(pk=_clean_autopk_value(ws_id)).first()
				release_retain_result(ws, request.POST.get('choice_type'),'',
				'', request.user)
			run_id = _clean_autopk_value(request.POST.get('run_id'))
			if run_id is None:
				return redirect('/worksheets/authorize_runs/?stage=1&auth_by=runs&stage=1')
			return redirect('/worksheets/authorize_runs/?stage=1&auth_by=runs&run_id=%d&stage=1' % run_id)
	else:
		context = {'worksheetsamples':worksheetsamples,'facilities':facilities}
		return render(request, 'results/release_results.html', context)

def _clean_autopk_value(value):
	if value in (None, '', 0, '0'):
		return None
	try:
		value = int(value)
	except (TypeError, ValueError):
		return None
	return value if value > 0 else None

def release_retain_result(ws, choice,comments,completed, user, reason = ''): 
	#create the result
	if ws is None:
		return False
	if (choice == 'release' and ws.stage == 2) or (choice == 'invalid' and ws.stage == 4):
		#if it was repeat that is being invalidated (due to hemolysis or insufficient vol), 
		#delete this record and use the previous one	
		result = Result()
		result.repeat_test = 2
		result.authorised = 1
		result.result1 = ws.result_alphanumeric
		result.result_numeric = ws.result_numeric
		result.failure_reason = reason
		if choice == 'invalid':
			result.result_alphanumeric = 'Failed'
		else:
			result.result_alphanumeric = ws.result_alphanumeric
		result.method = ws.method
		result.test_date = ws.test_date
		result.authorised_at = timezone.now()
		result.authorised_by_id = _clean_autopk_value(ws.authoriser_id)
		result.test_by_id = _clean_autopk_value(ws.tester_id)
		result.sample_id = _clean_autopk_value(ws.sample_id)
		result.suppressed = ws.suppressed
		result.worksheet_sample_id = _clean_autopk_value(ws.id)
		result.supression_cut_off_id = _clean_autopk_value(ws.supression_cut_off_id)
		result.has_low_level_viramia = ws.has_low_level_viramia
		result.save()
		#set release date based on whether sample's data is entered
		if ws.sample is not None and ws.sample.is_data_entered == 1 and ws.sample.verified == 1:
			released_at = timezone.now()
			released = True
			comments = ''
		else:
			released_at = None
			released = False
			comments = 'Pending data entry'

		other_params = {
			'released': released,
			'comments': comments,
			'released_by': user,
			'released_at': released_at,
			'qc_date': timezone.now(),
		}
		rqc, rqc_created = ResultsQC.objects.update_or_create(result=result, defaults=other_params)
		ws.stage = 5
		ws.failure_reason = reason
		if ws.sample is not None:
			ws.sample.stage = 5
		ws.save()
		if ws.sample is not None:
			ws.sample.save()
		update_sample(ws)
	else:
		if ws.stage != 4 and ws.stage != 5:
			manage_results(ws, choice,user)	

# authorize, reschedule or invalidate
def manage_results(ws,choice,user):
	
	#set worksheet sample stage
	if choice == 'release' or choice == 'invalid':
		ws.stage = ws.sample.stage = 5
	else:
		ws.stage = ws.sample.stage = 4
		if ws.sample.sample_type == 'D':
			ws.repeat_test = 1
	ws.authorised_at = timezone.now()
	ws.authoriser = user
	ws.sample.save();
	ws.save()
	update_sample(ws)
	return True

def update_sample(ws):
	if ws.sample is None:
		sample = Sample.objects.filter(barcode = ws.sample.barcode).first()
		if sample:
			ws.sample.save()
			ws.sample = sample
			ws.save()
	return True

def intervene_list(request):
	intervene_results = ResultsQC.objects.filter(released=False,result__sample__envelope__sample_medical_lab=utils.user_lab(request))[:500]
	return render(request, 'results/intervene_list.html', {'intervene_results':intervene_results})

def dr_results(request):
	#results after 2022-11-08
	dr_results = ResultsQC.objects.filter(released=True,result__result_numeric__gte=1000, result__id__gte=9039314, is_reviewed_for_dr=False, result__sample__verified=True, result__sample__envelope__sample_medical_lab=utils.user_lab(request))
	return render(request, 'results/dr_results.html', {'dr_results':dr_results,'stats':dr_results.count()})


def reschedule(request, result_pk):
	resultsqc = ResultsQC.objects.filter(result_id=result_pk).first()
	if resultsqc:
		resultsqc.result.repeat_test = 1
		resultsqc.result.authorised = False
		resultsqc.result.save()
		resultsqc.delete()
		return HttpResponse(1)
	else:
		return HttpResponse(0)

def approve_for_dr(request, result_pk):
	resultsqc = ResultsQC.objects.filter(result_id=result_pk).first()
	if resultsqc:
		resultsqc.is_reviewed_for_dr = True
		resultsqc.dr_reviewed_by_id = request.user
		resultsqc.dr_reviewed_at = timezone.now()
		resultsqc.save()
		return HttpResponse(1)
	else:
		return HttpResponse(0)


def api(request):
	ret=[]
	results = Result.objects.all()

	for i,r in enumerate(results):
		s = r.sample
		p = r.sample.patient
		ret.append({
				'sample_id': s.pk,
				'hep_number': p.hep_number,
				'vl_sample_id': s.vl_sample_id,
				'locator_id': "%s%s/%s"  %(s.locator_category, s.envelope.envelope_number, s.locator_position),
				'form_number': s.form_number,
				'hep_number': s.patient.hep_number,
			})
	return HttpResponse(json.dumps(ret))

def authorize_sample(request):
	if request.method == 'POST':
		sample_pk = request.POST.get('sample_pk')
		search = request.POST.get('search')
		if sample_pk:
			result = Result.objects.filter(sample_id=sample_pk).first()
			choice = request.POST.get('choice')
			if choice == 'reschedule':
				result.repeat_test = 1
				result.authorised = False
			elif choice == 'invalid':
				result.result_alphanumeric = 'FAILED'
				result.repeat_test = 2
				result.suppressed = 3
				result.authorised = True
				result.authorised_by_id = request.user
				result.authorised_at = timezone.now()
			else:
				result.repeat_test = 2
				result.authorised = True
				result.authorised_by_id = request.user
				result.authorised_at = timezone.now()

			result.save()

			return HttpResponse("saved")
		else:
			search = search.strip()
			samples = Sample.objects.filter(form_number=search)
			context = {'samples':samples}
	else:
		context = {}


	return render(request, 'results/authorize_sample.html', context)

def dictfetchall(cursor):
	"Return all rows from a cursor as a list of dicts"
	desc = cursor.description
	return [
		dict(zip([col[0] for col in desc], row))
		for row in cursor.fetchall()
	]

def trouble_shoot_results(request):
    if request.method == 'POST':
    	search_by = request.POST.get('search_by')  # e.g., 'form_number'
    	search_string = request.POST.get('search_string')  # e.g., 'A123,B456'

    	if not search_by or not search_string:
    		return HttpResponse("Missing search parameters", status=400)

    	# Clean and split the search string
    	search_values = [v.strip().strip("'").strip('"') for v in search_string.split(',') if v.strip()]
    	if not search_values:
    		return HttpResponse("No valid search values provided", status=400)

    	placeholders = ', '.join(['%s'] * len(search_values))

    	# Validate `search_by` to prevent SQL injection
    	allowed_fields = ['form_number', 'barcode', 'facility_reference', 'instrument_id']
    	if search_by not in allowed_fields:
    		return HttpResponse("Invalid search field", status=400)

    	# Build the SQL query dynamically and safely
    	sql = f"""SELECT barcode, form_number, facility_reference, instrument_id, ws.stage, qc.released, r.result_alphanumeric 
            FROM vl_samples s 
            LEFT JOIN vl_worksheet_samples ws ON s.id = ws.sample_id 
            LEFT JOIN vl_results r ON r.sample_id = s.id 
            LEFT JOIN vl_results_qc qc ON qc.result_id = r.id 
            WHERE s.{search_by} IN ({placeholders})"""

    	with connections['default'].cursor() as cursor:
    		cursor.execute(sql, search_values) 
    		samples = dictfetchall(cursor)

    	response = HttpResponse(content_type='text/csv')
    	filename = f"troubleshoot_results_{slugify(search_by)}.csv"
    	response['Content-Disposition'] = f'attachment; filename="{filename}"'

    	writer = csv.DictWriter(response, fieldnames=samples[0].keys() if samples else [])
    	writer.writeheader()
    	writer.writerows(samples)
    	return response

    return render(request, 'results/trouble_shoot_results.html')


def trouble_shoot_ranges(request):
	if request.method == 'POST':
		pst = request.POST
		year = pst.get('year')
		month = pst.get('month')
		lower_limit = pst.get('lower_limit')
		number_of_envelopes = pst.get('number_of_envelopes')
		envelope_numbers = [
   			f"{str(year)[-2:]}{int(month):02d}-{int(lower_limit) + i:04d}"
    		for i in range(int(number_of_envelopes))
        ]
		# Create a proper SQL list of quoted strings
		envelope_numbers_sql = ", ".join([f"'{num}'" for num in envelope_numbers])
		#samples_without_results = Sample.objects.filter(envelope__envelope_number__in=envelope_numbers).exclude(
    	#	id__in=Result.objects.values('sample_id')).select_related('envelope')
		#
		## Create CSV response
		#response = HttpResponse(
        #    content_type='text/csv',
        #    headers={'Content-Disposition': 'attachment; filename="samples_without_results.csv"'},
        #)
		#
		#writer = csv.writer(response)
		## Write header
		#writer.writerow([
        #    'Barcode', 
        #    'Facility Reference', 
        #    'Form Number',
        #    'Stage' 
        #    # Add other sample fields you want to export
        #])
		## Write data
		#for sample in samples_without_results:
		#	writer.writerow([
        #        sample.barcode,
        #        sample.facility_reference,
        #        sample.form_number,
        #        sample.stage,
        #        # Add other sample fields
        #    ])
		#return response
		sql = f"""SELECT barcode, form_number, facility_reference, instrument_id, ws.stage, qc.released, r.result_alphanumeric 
            FROM vl_samples s 
            LEFT JOIN vl_worksheet_samples ws ON s.id = ws.sample_id 
            LEFT JOIN vl_results r ON r.sample_id = s.id 
            LEFT JOIN vl_results_qc qc ON qc.result_id = r.id 
            WHERE (r.result_alphanumeric IS NULL OR r.result_alphanumeric = '') and s.envelope_id IN (select id from vl_envelopes where envelope_number in({envelope_numbers_sql}))"""

		with connections['default'].cursor() as cursor:
			cursor.execute(sql) 
			samples = dictfetchall(cursor)
		response = HttpResponse(content_type='text/csv')
		filename = f"troubleshoot_results.csv"
		response['Content-Disposition'] = f'attachment; filename="{filename}"'
		writer = csv.DictWriter(response, fieldnames=samples[0].keys() if samples else [])
		writer.writeheader()
		writer.writerows(samples)
		return response
	context = {
		'years': range(int((dt.now().strftime('%y')))-1, int((dt.now().strftime('%y')))+1),
		'months': utils.get_months(),
	}
	return render(request, 'results/trouble_shoot_ranges.html',context)

def release_sample(request):
	if request.method == 'POST':
		result_pk = request.POST.get('result_pk')
		search = request.POST.get('search')
		if result_pk:
			result = Result.objects.get(pk=result_pk)
			choice = request.POST.get('choice')
			released = True if choice == 'release' else False
			comments = request.POST.get('comments')
			completed = request.POST.get('completed')
			other_params = {
				'released': released,
				'comments': comments,
				'released_by': request.user,
				'released_at': timezone.now(),
			}
			rqc, rqc_created = ResultsQC.objects.update_or_create(result=result, defaults=other_params)

			return HttpResponse("saved")
		else:
			search = search.strip()

			samples = Sample.objects.filter(Q(form_number=search) | Q(barcode=search))
			context = {'samples':samples}
	else:
		context = {}


	return render(request, 'results/release_sample.html', context)

@permission_required('results.add_result', login_url='/login/')
def samples_pending_results(request):
	worksheet_samples = WorksheetSample.objects.filter(stage=2)

	context = {'worksheet_samples': worksheet_samples}
	return render(request, 'results/list.html', context)

def list(request):
	search_val = request.GET.get('search_val')
	is_data_entered = request.GET.get('is_data_entered')

	return render(request, 'results/list.html', {'global_search':search_val,'is_data_entered':is_data_entered })

def force_create_result(request):
	cursor = connections['default'].cursor()
	#get generated matched and unmatched records of facility
	cursor.execute("select ws.id, ws.sample_id, ws.repeat_test, ws.authorised, ws.suppressed,ws.method,ws.tester_id,ws.result_numeric, ws.result_alphanumeric,ws.test_date,ws.authorised_at,ws.authoriser_id FROM  vl_worksheet_samples ws left join vl_results r  on ws.id = r.worksheet_sample_id where ws.stage = 5 and r.id is null")
	row = cursor.fetchone()
	
	if row is not None:
		
		result = Result()
		result.worksheet_sample_id = row[0]
		result.sample_id = row[1]
		result.repeat_test = row[2]
		result.authorised = row[3]
		result.suppressed = row[4]
		result.method =  row[5]
		result.test_by_id = row[6]
		result.result_numeric =row[7]
		result.result1 = row[8]
		result.result_alphanumeric = row[8]
		result.test_date = row[9]
		result.authorised_at = row[10]
		result.authorised_by_id = row[11]
		  	
		result.save()
		other_params = {
			'released': True,
			'comments': 'manual',
			'released_by_id': 6463900,
			'released_at': timezone.now(),
		}
		rqc, rqc_created = ResultsQC.objects.update_or_create(result=result, defaults=other_params)
	return HttpResponse('done')

class ListJson(BaseDatatableView):
	model = WorksheetSample
	columns = ['sample.barcode','instrument_id','sample.form_number','sample.patient.facility','sample.patient.facility.district',
	'sample.patient.hep_number','sample.patient.other_id','sample.patient.gender','sample.date_collected','sample.date_received',
	'sample.result.result_alphanumeric','action','status']
	order_columns = ['barcode','instrument_id']
	max_display_length = 500
					
	def render_column(self, row, column):
		if column == 'action':
			return result_utils.generate_radios(row.pk)
		elif column =='status':
			return "<span id='saved{0}' class='status alert alert-success vl-alert' role='alert'>saved&nbsp;</span>".format(row.pk)
		else:
			return super(ListJson, self).render_column(row, column)

	def filter_queryset(self, qs):
		search = self.request.GET.get(u'search[value]', None)
		global_search = self.request.GET.get('global_search', None)
		
		qs_params = Q()
		if search:
			qs_params = Q(sample__barcode__icontains=search) | Q(instrument_id__icontains=search)
		qs = programs.filter_queryset_by_program(self.request, qs, 'sample__envelope__program_code')
		return qs.filter(qs_params).order_by('instrument_id')	

	
