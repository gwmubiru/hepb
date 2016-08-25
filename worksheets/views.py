from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from easy_pdf.views import PDFTemplateView
from django.views import generic

from .forms import WorksheetForm,AttachSamplesForm
from .models import Worksheet
from samples.models import Sample

# Create your views here.

class PDFView(PDFTemplateView):
	model = Worksheet
	template_name = "worksheets/pdf.html"
	def get_context_data(self, **kwargs):
		return super(PDFView, self).get_context_data(
			pagesize="A4", 
			title="Worksheet",
			worksheet=Worksheet.objects.get(pk=self.kwargs['pk']),
			 **kwargs)
	
	
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
			
		return redirect('worksheets:show',worksheet_id)
	else:
		#form = AttachSamplesForm()
		samples = Sample.objects.filter(verified=True, in_worksheet=False).order_by('created_at')[:10]
		return render(request, 'worksheets/attach_samples.html', {'samples':samples, 'worksheet_id': worksheet_id})

def list(request):
	worksheets = Worksheet.objects.all()
	return render(request,'worksheets/list.html',{'worksheets':worksheets})

def show(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	return render(request, 'worksheets/show.html', {'worksheet': worksheet})

def vlprint(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	return render(request, 'worksheets/vlprint.html', {'worksheet': worksheet})
