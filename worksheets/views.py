import json
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from easy_pdf.views import PDFTemplateView
from django.views import generic
from django.template import Context
from django.template.loader import get_template
from xhtml2pdf import pisa 

from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q

from home import utils
from .forms import WorksheetForm,AttachSamplesForm
from .models import Worksheet,WorksheetSample
from samples.models import Sample
from results.models import Result
from . import utils as worksheet_utils


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
	context = { 'machine_type':machine_type}
	if request.method == 'POST':
		form = WorksheetForm(request.POST)
		if form.is_valid():
			worksheet = form.save(commit=False)
			worksheet.worksheet_reference_number = worksheet_utils.create_worksheet_ref_number(machine_type,worksheet.sample_type)
			worksheet.machine_type = machine_type
			worksheet.generated_by = request.user
			worksheet.save()

			if machine_type == 'C':
				attached_samples = request.POST.getlist('samples')
				worksheet_samples = []
				
				for sample_id in attached_samples:
					instrument_id = request.POST.get('instrument'+sample_id)
					if instrument_id:
						sample = Sample.objects.get(pk=sample_id)
						worksheet_samples.append(WorksheetSample(worksheet=worksheet, sample=sample, instrument_id=instrument_id))
						sample.in_worksheet = True
						sample.save()

				#return HttpResponse(ret)
				WorksheetSample.objects.bulk_create(worksheet_samples)
				return redirect('worksheets:show',worksheet.pk)


			return redirect('worksheets:attach_samples', worksheet_id=worksheet.id)
	else:
		form = WorksheetForm(initial={'machine_type':machine_type})
		context = {'form': form, 'machine_type':machine_type}
		if machine_type == 'C':
			repeat_samples = Sample.objects.filter(result__repeat_test = True)[:50]
			context.update({'samples':Sample.objects.filter(verification__accepted=True, in_worksheet=False).\
									extra({'lposition_int': "CAST(locator_position as UNSIGNED)"}).\
									order_by('envelope__envelope_number', 'lposition_int')[:50], 'repeat_samples':repeat_samples})


	return render(request, 'worksheets/create.html', context)

def attach_samples(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	if request.method == 'POST':
		# pass
		attached_samples = request.POST.getlist('samples')
		worksheet_samples = []
		
		for sample_id in attached_samples:
			sample = Sample.objects.get(pk=sample_id)			
			#worksheet.samples.add(sample)
			worksheet_samples.append(WorksheetSample(worksheet=worksheet, sample=sample))
			sample.in_worksheet = True
			sample.save()

		WorksheetSample.objects.bulk_create(worksheet_samples)
			
		return redirect('worksheets:show',worksheet_id)
	else:
		#form = AttachSamplesForm()
		sample_limit = 21 if worksheet.machine_type == 'R' else 93
		sample_pads = 11 if worksheet.include_calibrators else 3
		samples = Sample.objects.filter(verification__accepted=True, in_worksheet=False).\
					extra({'lposition_int': "CAST(locator_position as UNSIGNED)"}).\
					order_by('envelope__envelope_number', 'lposition_int')
		repeat_samples = Sample.objects.filter(result__repeat_test = True)[:sample_limit]
		# samples = Sample.objects.filter(in_worksheet=False).order_by('created_at')[:sample_limit]
		# repeat_samples = Sample.objects.all()[:sample_limit]
		context = {
			'samples': samples, 
			'worksheet': worksheet,
			'sample_limit': sample_limit,
			'sample_pads': sample_pads,
			'repeat_samples': repeat_samples, 
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

def authorize_list(request, machine_type):
	worksheets = Worksheet.objects.filter(stage=2, machine_type=machine_type)
	return render(request,'worksheets/authorize_list.html',{'worksheets':worksheets})

def authorize_results(request, worksheet_id):
	if request.method == 'POST':
		result = Result.objects.get(pk=request.POST.get('result_pk'))
		choice = request.POST.get('choice')
		if choice == 'reschedule':
			result.repeat_test = 1
		elif choice == 'invalid':
			result.result_alphanumeric = 'FAILED'
			result.suppressed = 3
			result.authorised = True
			result.authorised_by_id = request.user
			result.authorised_at = timezone.now()
		else:
			result.authorised = True
			result.authorised_by_id = request.user
			result.authorised_at = timezone.now()

		result.save()
		return HttpResponse("saved");
	else:
		worksheet = Worksheet.objects.get(pk=worksheet_id)
		sample_pads = 11 if worksheet.include_calibrators else 3
		context = {'worksheet': worksheet, 'sample_pads': sample_pads}
		return render(request, 'worksheets/authorize_results.html', context)

def pending_samples(request):	
	repeat = request.GET.get('repeat')
	if repeat:
		samples = Sample.objects.filter(sampleresults__repeat_test = True)[:50]
	else:
		envelope_number =request.GET.get('envelope_number')
		samples = Sample.objects.filter(verification__accepted=True, in_worksheet=False, envelope__envelope_number=envelope_number) if envelope_number else\
					Sample.objects.filter(verification__accepted=True, in_worksheet=False)
		samples = samples.extra({'lposition_int': "CAST(locator_position as UNSIGNED)"}).order_by('envelope__envelope_number', 'lposition_int')[:50]
	ret=[]

	for i,s in enumerate(samples):
		ret.append({
				'index': i,
				'id': s.id,
				'vl_sample_id': s.vl_sample_id,
				'locator_id': "%s%s/%s"  %(s.locator_category, s.envelope.envelope_number, s.locator_position),
				'form_number': s.form_number,
				'art_number': s.patient.art_number,
			})
	return HttpResponse(json.dumps(ret))


class ListJson(BaseDatatableView):
	model = Worksheet
	columns = ['worksheet_reference_number', 'machine_type', 'sample_type', 'created_at', 'pk']
	order_columns = ['worksheet_reference_number', 'machine_type', 'sample_type', 'created_at', '']
	max_display_length = 500

	def render_column(self, row, column):
		if column == 'pk':
			url0 = "/worksheets/show/{0}".format(row.pk)
			url1 = "javascript:windPop(\"/worksheets/vlprint/{0}\")".format(row.pk)
			url2 = "javascript:windPop(\"/worksheets/pdf/{0}\")".format(row.pk)
			url3 = "/results/upload/{0}".format(row.pk)
			links = utils.dropdown_links([
					{"label":"view", "url":url0},
					{"label":"Print", "url":url1},
					{"label":"PDF", "url":url2},
					{"label":"Upload Results", "url": url3},
				])
			return links
		else:
			return super(ListJson, self).render_column(row, column)
