import csv, pandas, io
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils import timezone

from .forms import UploadForm, CobasUploadForm
from worksheets.models import Worksheet
from samples.models import Sample
from .models import Result,ResultsPrinting
from . import utils as result_utils

# patient, pat_created = Patient.objects.get_or_create(
# 						unique_id=unique_id,
# 						defaults=patient_form.cleaned_data
# 						)
# Create your views here.

# def store_final_result(machine_type, sample, result):
# 	fr = FinalResult();
# 	fr.sample = sample	
# 	fr.valid = True
# 	fr.final_result = get_status(result)
# 	fr.result_numeric = get_numeric_result(result)
# 	fr.result_alphanumeric = get_alphanumeric_result(result)
# 	fr.method = machine_type
# 	fr.test_date = timezone.now()
# 	fr.test_by = 2
# 	fr.save()

def store_result(machine_type, sample, result, repeat):
	sr = Result.objects
	sample_result, sr_created = sr.get_or_create(sample=sample)
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

	#sample_result.repeat_test = repeat
	sample_result.save()

	# if repeat==False:
	# 	store_final_result(machine_type, sample, result)


def handle_files(f, worksheet):
	if worksheet.machine_type == 'R':
		reader = pandas.read_csv(f, sep=',')
		for row in reader.iterrows():
			# try:
			index, data = row
			result = data["Result"]
			vl_sample_id = data["Sample ID"]
			sample = Sample.objects.get(vl_sample_id=vl_sample_id)
			#repeat = result_utils.repeat_test('R', result, '')
			store_result('R', sample, result)
			# except:
			# 	pass			
			
	else:			
		reader = pandas.read_csv(f, sep='\t', skiprows=20)		
		for row in reader.iterrows():
			# try:
			index, data = row
			result = data.get("RESULT")
			vl_sample_id = data.get("SAMPLE ID")
			sample = Sample.objects.get(vl_sample_id=vl_sample_id)
			#repeat = result_utils.repeat_test('A', result, data.get("FLAGS"))
			store_result('A', sample,result)
			# except:
			# 	pass


def upload(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	if(request.method == 'POST'):
		form = UploadForm(request.POST, request.FILES)
		if form.is_valid():
			upload = form.save(commit=False)
			upload.uploaded_by = request.user	
			upload.save()
			worksheet.results_uploaded = True
			worksheet.save()

			#f = request.FILES['results_file']
			#return HttpResponse(upload.results_file)
			handle_files(upload.results_file, worksheet)

			return redirect('worksheets:list')
	else:
		form = UploadForm(initial={'multiplier':1, 'worksheet': worksheet})
		
	return render(request, 'results/upload.html', {'form': form, 'worksheet': worksheet})

# def cobas_upload(request):
# 	if(request.method == 'POST'):
# 		form = CobasUploadForm(request.POST, request.FILES)
# 		if form.is_valid():
# 			upload = form.save(commit=False)
# 			upload.cobas_uploaded_by = request.user	
# 			upload.save()

# 			reader = pandas.read_csv(upload.results_file, sep=',')
# 			for row in reader.iterrows():
# 				# try:
# 				index, data = row
# 				result = data["Target 1"]
# 				vl_sample_id = data["Sample ID"]
# 				sample = Sample.objects.filter(vl_sample_id=vl_sample_id)[0].sample

# 				#repeat = result_utils.repeat_test('R', result, '')
# 				store_result('R', sample, result)
				
# 			return redirect('worksheets:list')
# 	else:
# 		form = CobasUploadForm(initial={'multiplier':1})

# 	return render(request, 'results/cobas_upload.html', {'form': form})

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

def release_list(request, machine_type):
	worksheets = Worksheet.objects.filter(stage=3, machine_type=machine_type)
	return render(request,'results/release_list.html',{'worksheets':worksheets})

def release_results(request, worksheet_id):
	if request.method == 'POST':
		result = Result.objects.get(pk=request.POST.get('result_pk'))
		choice = request.POST.get('choice')
		rp = ResultsPrinting()
		if choice == 'release':
			rp.released = True
		else:
			rp.released =False
		rp.released_by = request.user
		rp.released_at = timezone.now()
		rp.result = result
		rp.save()
		return HttpResponse("saved")
	else:
		worksheet = Worksheet.objects.get(pk=worksheet_id)
		sample_pads = 11 if worksheet.include_calibrators else 3
		context = {'worksheet': worksheet, 'sample_pads': sample_pads}
		return render(request, 'results/release_results.html', context)

