import csv, pandas, io, json, math, os, StringIO as SI
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils import timezone

from django.db import models
from django.db.models import Q
from django.contrib.auth.decorators import permission_required

from home import utils
from .forms import UploadForm, CobasUploadForm
from worksheets.models import Worksheet,WorksheetSample, MACHINE_TYPES
from samples.models import Sample
from .models import Result,ResultsQC
from . import utils as result_utils

# patient, pat_created = Patient.objects.get_or_create(
# 						unique_id=unique_id,
# 						defaults=patient_form.cleaned_data
# 						)
# Create your views here.

# def store_final_result(machine_type, sample, result):
# 	fr = FinalResult()
# 	fr.sample = sample	
# 	fr.valid = True
# 	fr.final_result = get_status(result)
# 	fr.result_numeric = get_numeric_result(result)
# 	fr.result_alphanumeric = get_alphanumeric_result(result)
# 	fr.method = machine_type
# 	fr.test_date = timezone.now()
# 	fr.test_by = 2
# 	fr.save()
def get_anomalies(request, worksheet_id):
	#return HttpResponse(SI.StringIO(request.FILES['results_file'].read()))
	uploaded_file = request.FILES['results_file']
	ext = os.path.splitext(uploaded_file.name)[1]

	tmp_name = "/tmp/%s"%uploaded_file.name
	with open(tmp_name, 'wb+') as destination:
		for chunk in uploaded_file.chunks():
			destination.write(chunk)
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	
	if worksheet.machine_type == 'R' or worksheet.machine_type == 'C':
		if not utils.eq(ext, '.csv'):
			return HttpResponse("<b>Expecting a .csv, but we are getting %s</b>"%ext)
		reader = pandas.read_csv(tmp_name, sep=',')
		sample_ids = tuple(reader["Sample ID"])
	else:
		if not utils.eq(ext, '.txt'):
			return HttpResponse("<b>Expecting a .txt, but we are getting %s</b>"%ext)
		reader = pandas.read_csv(tmp_name, sep='\t', skiprows=20)

		sample_ids = tuple(reader["SAMPLE ID"])

	duplicates = set(["%s"%x for x in sample_ids if x and not utils.isnan(x) and sample_ids.count(x) > 1])
	csv_samples_set = set(["%s"%x.strip() for x in sample_ids if x and not utils.isnan(x) and x not in ('HIV_LOPOS','HIV_NEG','HIV_HIPOS')])

	w_samples = WorksheetSample.objects.filter(worksheet=worksheet.pk)
	w_samples_set = set([x.sample.vl_sample_id for x in w_samples])
	non_samples_set = csv_samples_set-w_samples_set

	anomalies = ""
	if( not duplicates and not non_samples_set):
		return HttpResponse("0")

	duplicates_str = "<b>Duplicates:</b> %s" %(', '.join(duplicates)) if duplicates else ""
	non_samples_str = "<b>Samples not in this worksheet:</b> %s" %(', '.join(non_samples_set)) if non_samples_set else ""
	destination.close()
	return HttpResponse("%s <br> %s" %(duplicates_str, non_samples_str))


def store_result(machine_type, sample, result, multiplier, user):
	result = 'failed' if utils.isnan(result) else result
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

	result_dict = result_utils.get_result(result, multiplier)
	sample_result.repeat_test = result_dict.get('repeat_test')
	sample_result.result_numeric = result_dict.get('numeric_result')
	sample_result.result_alphanumeric = result_dict.get('alphanumeric_result')
	sample_result.suppressed = result_dict.get('suppressed')
	sample_result.method = machine_type
	sample_result.test_date = timezone.now()
	sample_result.test_by = user

	sample_result.save()

	# if repeat==False:
	# 	store_final_result(machine_type, sample, result)

def handle_files(form, worksheet, user):
	#return HttpResponse(form.cleaned_data.get('results_file'))
	results_file = form.cleaned_data.get('results_file')
	multiplier = form.cleaned_data.get('multiplier')
	tmp_name = "/tmp/%s"%results_file.name

	if worksheet.machine_type == 'R':
		reader = pandas.read_csv(tmp_name, sep=',')
		for row in reader.iterrows():
			# try:
			index, data = row
			result = data["Result"]
			vl_sample_id = data["Sample ID"]
			vl_sample_id = vl_sample_id.strip() if type(vl_sample_id) is str else vl_sample_id
			sample = Sample.objects.filter(vl_sample_id=vl_sample_id).first()
			if sample:
				#repeat = result_utils.repeat_test('R', result, '')
				store_result('R', sample, result, multiplier, user)
				ws = WorksheetSample.objects.filter(worksheet=worksheet, sample=sample).first()
				if ws:
					ws.stage = 2
					ws.save()
			# except:
			# 	pass			
			
	else:			
		reader = pandas.read_csv(tmp_name, sep='\t', skiprows=20)	
		for row in reader.iterrows():
			# try:
			index, data = row
			result = data.get("RESULT")
			vl_sample_id = data.get("SAMPLE ID")
			vl_sample_id = vl_sample_id.strip() if type(vl_sample_id) is str else vl_sample_id
			sample = Sample.objects.filter(vl_sample_id=vl_sample_id).first()
			if sample:
				#repeat = result_utils.repeat_test('A', result, data.get("FLAGS"))
				store_result('A', sample,result, multiplier, user)
				ws = WorksheetSample.objects.filter(worksheet=worksheet, sample=sample).first()
				if ws:
					ws.stage = 2
					ws.save()
			# except:
			# 	pass

@permission_required('worksheets.add_worksheet', login_url='/login/')
def upload(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	if(request.method == 'POST'):
		form = UploadForm(request.POST, request.FILES)
		if form.is_valid():			
			upload = form.save(commit=False)
			upload.uploaded_by = request.user
			upload.multiplier = form.cleaned_data.get('multiplier')	
			# results_file = form.cleaned_data.get('results_file')
			# return HttpResponse(results_file.name)							

			#f = request.FILES['results_file']
			#return HttpResponse(upload.results_file)
			handle_files(form, worksheet, request.user)
			worksheet.stage = 2
			worksheet.save()
			upload.save()

			#return redirect('worksheets:show',worksheet_id)
			return redirect('/worksheets/show/%d/?show_results=saved' %worksheet.pk)


	form = UploadForm(initial={'multiplier':1, 'worksheet': worksheet})
		
	return render(request, 'results/upload.html', {'form': form, 'worksheet': worksheet})

@permission_required('worksheets.add_worksheet', login_url='/login/')
def cobas_upload(request):
	if(request.method == 'POST'):
		form = CobasUploadForm(request.POST, request.FILES)
		if form.is_valid():
			upload = form.save(commit=False)
			upload.cobas_uploaded_by = request.user
			uploaded_file = form.cleaned_data.get('results_file')
			tmp_name = "/tmp/%s"%uploaded_file.name
			with open(tmp_name, 'wb+') as destination:
				for chunk in uploaded_file.chunks():
					destination.write(chunk)

			reader = pandas.read_csv(tmp_name, sep=',')
			#worksheets_set = set()
			for row in reader.iterrows():
				# try:
				index, data = row
				result = data["Target 1"]
				instrument_id = data["Sample ID"]
				#sample = Sample.objects.filter(vl_sample_id=vl_sample_id)[0].sample
				ws = WorksheetSample.objects.filter(instrument_id=instrument_id).first()
				if ws:
					sample = ws.sample
					#repeat = 3 if result_utils.eq(result, 'invalid') else 2
					store_result('C', sample, result, form.cleaned_data.get('multiplier'), request.user)
					ws.stage = 2
					ws.save()
					ws.worksheet.stage = 2
					ws.worksheet.save()

					#worksheets_set.add(ws.worksheet.pk)
					# if(WorksheetSample.objects.filter(worksheet=ws.worksheet,stage=1).count()==0):
					# 	ws.worksheet.stage = 2
					# 	ws.worksheet.save()

			# for w_id in worksheets_set:
			# 	 if(WorksheetSample.objects.filter(worksheet_id=w_id,stage=1).count()==0):
			# 	 	worksheet = Worksheet.objects.get(pk=w_id)
			# 	 	worksheet.stage = 2
			# 	 	worksheet.save()

			upload.save()
				
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

@permission_required('results.add_resultsqc', login_url='/login/')
def release_list(request, machine_type):
	tab = request.GET.get('tab')
	if tab=='released':
		filters = Q(stage=4, machine_type=machine_type)
	else:
		filters = Q(stage=3, machine_type=machine_type)

	worksheets = Worksheet.objects.filter(filters)
	context = {'worksheets':worksheets, 'machine_type':dict(MACHINE_TYPES).get(machine_type)}
	return render(request,'results/release_list.html',context)

@permission_required('results.add_resultsqc', login_url='/login/')
def release_results(request, worksheet_id):
	if request.method == 'POST':
		result = Result.objects.get(pk=request.POST.get('result_pk'))
		choice = request.POST.get('choice')
		released = True if choice == 'release' else False
		comments = request.POST.get('comments')
		completed = request.POST.get('completed')
		other_params = {
			'released': released,
			'comments': request.POST.get('comments'),
			'released_by': request.user,
			'released_at': timezone.now(),
		}
		rqc, rqc_created = ResultsQC.objects.update_or_create(result=result, defaults=other_params)
		sample = rqc.result.sample

		ws = WorksheetSample.objects.filter(sample=sample, worksheet=worksheet_id).first()
		ws.stage = 4
		ws.save()

		if(completed=='yes'):
			worksheet = Worksheet.objects.get(pk=worksheet_id)
			worksheet.stage = 4
			worksheet.save()
			return HttpResponse("completed")
			
		return HttpResponse("saved")
	else:
		worksheet = Worksheet.objects.get(pk=worksheet_id)
		sample_pads = 11 if worksheet.include_calibrators else 3
		context = {'worksheet': worksheet, 'sample_pads': sample_pads}
		return render(request, 'results/release_results.html', context)

def intervene_list(request):
	intervene_results = ResultsQC.objects.filter(released=False)[:500]
	return render(request, 'results/intervene_list.html', {'intervene_results':intervene_results})

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
