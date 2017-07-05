import csv, pandas, io, json
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils import timezone

from django.db import models

from .forms import UploadForm, CobasUploadForm
from worksheets.models import Worksheet,WorksheetSample
from samples.models import Sample
from .models import Result,ResultsQC
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

def store_result(machine_type, sample, result, repeat, multiplier, user):
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

	sample_result.repeat_test = repeat
	result_dict = result_utils.get_result(result, multiplier)
	sample_result.result_numeric = result_dict.get('numeric_result')
	sample_result.result_alphanumeric = result_dict.get('alphanumeric_result')
	sample_result.suppressed = result_dict.get('suppressed')
	sample_result.method = machine_type
	sample_result.test_date = timezone.now()
	sample_result.test_by = user

	sample_result.save()

	# if repeat==False:
	# 	store_final_result(machine_type, sample, result)


def handle_files(f, worksheet, user):
	if worksheet.machine_type == 'R':
		reader = pandas.read_csv(f, sep=',')
		for row in reader.iterrows():
			# try:
			index, data = row
			result = data["Result"]
			vl_sample_id = data["Sample ID"]
			sample = Sample.objects.get(vl_sample_id=vl_sample_id)
			repeat = result_utils.repeat_test('R', result, '')
			store_result('R', sample, result, repeat, worksheet.multiplier, user)
			ws = WorksheetSample.objects.filter(worksheet=worksheet, sample=sample).first()
			ws.stage = 2
			ws.save()
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
			repeat = result_utils.repeat_test('A', result, data.get("FLAGS"))
			store_result('A', sample,result, repeat, worksheet.multiplier, user)
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
			worksheet.stage = 1
			worksheet.save()

			#f = request.FILES['results_file']
			#return HttpResponse(upload.results_file)
			handle_files(upload.results_file, worksheet, request.user)

			return redirect('worksheets:list')
	else:
		form = UploadForm(initial={'multiplier':1, 'worksheet': worksheet})
		
	return render(request, 'results/upload.html', {'form': form, 'worksheet': worksheet})

def cobas_upload(request):
	if(request.method == 'POST'):
		form = CobasUploadForm(request.POST, request.FILES)
		if form.is_valid():
			upload = form.save(commit=False)
			upload.upload_date = timezone.now()
			upload.cobas_uploaded_by = request.user	
			upload.save()

			reader = pandas.read_csv(upload.results_file, sep=',')
			for row in reader.iterrows():
				# try:
				index, data = row
				result = data["Target 1"]
				instrument_id = data["Sample ID"]
				#sample = Sample.objects.filter(vl_sample_id=vl_sample_id)[0].sample
				ws = WorksheetSample.objects.filter(instrument_id=instrument_id).first()
				if ws:
					sample = ws.sample
					repeat = 3 if result_utils.eq(result, 'invalid') else 2
					store_result('C', sample, result, repeat, 1, request.user)
					ws.stage = 2
					ws.save()
				
			return redirect('worksheets:list')
	else:
		form = CobasUploadForm(initial={'multiplier':1})

	return render(request, 'results/cobas_upload.html', {'form': form})

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
	auth_count = models.Count(models.Case(models.When(worksheetsample__stage__gte=3, then=1)))
	samples_count = models.Count('worksheetsample')
	worksheets = Worksheet.objects.annotate(sc=samples_count,ac=auth_count).filter(ac=samples_count, machine_type=machine_type)
	#worksheets = Worksheet.objects.filter(stage=3, machine_type=machine_type)
	return render(request,'results/release_list.html',{'worksheets':worksheets})

def release_results(request, worksheet_id):
	if request.method == 'POST':
		result = Result.objects.get(pk=request.POST.get('result_pk'))
		choice = request.POST.get('choice')
		rp = ResultsQC()
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

def api(request):

	
	ret=[]
	results = Result.objects.all()

	for i,r in enumerate(results):
		s = r.sample
		p = r.sample.patient
		ret.append({
				'sample_id': s.pk,
				'art_number': p.art_number,
				'vl_sample_id': s.vl_sample_id,
				'locator_id': "%s%s/%s"  %(s.locator_category, s.envelope.envelope_number, s.locator_position),
				'form_number': s.form_number,
				'art_number': s.patient.art_number,
			})
	return HttpResponse(json.dumps(ret))