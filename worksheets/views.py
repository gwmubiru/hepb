from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse

from .forms import WorksheetForm,AttachSamplesForm
from .models import Worksheet
from samples.models import Sample

# Create your views here.

def create(request):
	if request.method == 'POST':
		form = WorksheetForm(request.POST)
		if form.is_valid():
			worksheet = form.save(commit=False)
			worksheet.generated_by = request.user
			worksheet.save()
			return redirect('worksheets:attach_samples', worksheet_id=worksheet.id)
	else:
		form = WorksheetForm()

	return render(request, 'worksheets/create.html', {'form': form})

def list(request):
	worksheets = Worksheet.objects.all()
	return render(request,'worksheets/list.html',{'worksheets':worksheets})

def attach_samples(request, worksheet_id):
	if request.method == 'POST':
		# pass
		attached_samples = request.POST.getlist('samples')
		w = Worksheet.objects.get(pk=worksheet_id)
		for sample_id in attached_samples:
			sample = Sample.objects.get(pk=sample_id)
			w.samples.add(sample)
			sample.in_worksheet = True
			sample.save()
			
		return redirect('worksheets:create')
	else:
		#form = AttachSamplesForm()
		samples = Sample.objects.filter(verified=True, in_worksheet=False).order_by('created_at')[:80]
		return render(request, 'worksheets/attach_samples.html', {'samples':samples, 'worksheet_id': worksheet_id})