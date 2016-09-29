import csv, pandas, io
from django.shortcuts import render, redirect
from django.http import HttpResponse

from .forms import UploadForm
from worksheets.models import Worksheet
from samples.models import Sample
from .models import FinalResult,SampleResults

# patient, pat_created = Patient.objects.get_or_create(
# 						unique_id=unique_id,
# 						defaults=patient_form.cleaned_data
# 						)
# Create your views here.
def store_result(sample,result):
	sr = SampleResults.objects
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
	sample_result.save()


def handle_files(f, worksheet):
	if worksheet.machine_type == 'R':
		reader = pandas.read_csv(f, sep=',')
		for row in reader.iterrows():
			# try:
			index, data = row
			result = data["Result"]
			vl_sample_id = data["Sample ID"]
			sample = Sample.objects.get(vl_sample_id=vl_sample_id)
			store_result(sample,result)
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
			store_result(sample,result)
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

			#return redirect('worksheets:list')
	else:
		form = UploadForm(initial={'multiplier':1, 'worksheet': worksheet})
		
	return render(request, 'results/upload.html', {'form': form, 'worksheet': worksheet})
