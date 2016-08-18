from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse

from .forms import WorksheetForm
from .models import Worksheet, WorksheetSample
from samples.models import Sample

# Create your views here.

def create(request):
	if request.method == 'POST':
		form = WorksheetForm(request.POST)
		if form.is_valid():
			r = form.cleaned_data
			w = Worksheet()
			w.machine_type = r.get('machine_type')
			w.sample_type = r.get('sample_type')
			w.sample_prep = r.get('sample_prep')
			w.sample_prep_expiry_date = r.get('sample_prep_expiry_date')
			w.bulk_lysis_buffer = r.get('bulk_lysis_buffer')
			w.bulk_lysis_buffer_expiry_date = r.get('bulk_lysis_buffer_expiry_date')
			w.control = r.get('control')
			w.control_expiry_date = r.get('control_expiry_date')
			w.calibrator = r.get('calibrator')
			w.calibrator_expiry_date = r.get('calibrator_expiry_date')
			w.include_calibrators = r.get('include_calibrators')
			w.amplication_kit = r.get('amplication_kit')
			w.amplication_kit_expiry_date = r.get('amplication_kit_expiry_date')
			w.assay_date = r.get('assay_date')
			w.generated_by_id = 2
			w.save()
			return redirect('worksheets:attach_samples', worksheet_id=w.id)

	else:
		form = WorksheetForm()

	return render(request, 'worksheets/create.html', {'form': form})

def list(request):
	pass

def attach_samples(request, worksheet_id):
	samples = Sample.objects.filter(verified=True, in_worksheet=False).order_by('created_at')[:80]
	return render(request, 'worksheets/attach_samples.html', {'samples': samples, 'worksheet_id': worksheet_id})