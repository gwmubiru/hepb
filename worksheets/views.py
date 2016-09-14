from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from easy_pdf.views import PDFTemplateView
from django.views import generic
from django.template import Context
from django.template.loader import get_template
from xhtml2pdf import pisa 

from .forms import WorksheetForm,AttachSamplesForm
from .models import Worksheet
from samples.models import Sample


# Create your views here.

# class PDFView(PDFTemplateView):
# 	model = Worksheet
# 	template_name = "worksheets/pdf.html"
# 	def get_context_data(self, **kwargs):
# 		return super(PDFView, self).get_context_data(
# 			pagesize="A4", 
# 			title="Worksheet",
# 			worksheet=Worksheet.objects.get(pk=self.kwargs['pk']),
# 			 **kwargs)

def generate_pdf(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	template = get_template("worksheets/pdf.html")
	html = template.render(Context({'worksheet': worksheet}))	
	f = open('worksheet.pdf', "w+b")
	pisa_status = pisa.CreatePDF(html.encode('utf-8'), dest=f, encoding='utf-8')

	f.seek(0)
	pdf = f.read()
	f.close()
	return HttpResponse(pdf, 'application/pdf')

	
def create(request, machine_type):
	if request.method == 'POST':
		form = WorksheetForm(request.POST)
		if form.is_valid():
			worksheet = form.save(commit=False)
			worksheet.machine_type = machine_type
			worksheet.generated_by = request.user
			worksheet.save()
			return redirect('worksheets:attach_samples', worksheet_id=worksheet.id)
	else:
		form = WorksheetForm(initial={'machine_type':machine_type})

	return render(request, 'worksheets/create.html', {'form': form, 'machine_type':machine_type})

def attach_samples(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	if request.method == 'POST':
		# pass
		attached_samples = request.POST.getlist('samples')
		
		for sample_id in attached_samples:
			sample = Sample.objects.get(pk=sample_id)
			worksheet.samples.add(sample)
			sample.in_worksheet = True
			sample.save()
			
		return redirect('worksheets:show',worksheet_id)
	else:
		#form = AttachSamplesForm()
		sample_limit = 21 if worksheet.machine_type == 'R' else 93
		sample_pads = 11 if worksheet.include_calibrators else 3
		samples = Sample.objects.filter(verified=True, in_worksheet=False).order_by('created_at')[:sample_limit]
		context = {
			'samples':samples, 
			'worksheet': worksheet,
			'sample_limit': sample_limit,
			'sample_pads':sample_pads,
			}
		return render(request, 'worksheets/attach_samples.html', context)

def list(request):
	search_val = request.GET.get('search_val')

	if search_val:
		worksheets = Worksheet.objects.filter(worksheet_reference_number__contains=search_val).order_by('-pk')[:1]
		if worksheets:
			worksheet = worksheets[0]
			return redirect('/worksheets/show/%d' %worksheet.pk)

	worksheets = Worksheet.objects.all()
	return render(request,'worksheets/list.html',{'worksheets':worksheets})

def show(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	sample_pads = 11 if worksheet.include_calibrators else 3
	context = {'worksheet': worksheet, 'sample_pads': sample_pads}
	return render(request, 'worksheets/show.html', context)

def vlprint(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	sample_pads = 11 if worksheet.include_calibrators else 3
	context = {'worksheet': worksheet, 'sample_pads': sample_pads}
	return render(request, 'worksheets/vlprint.html', context)
