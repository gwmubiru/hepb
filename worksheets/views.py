import json, base64
import os.path
from django.core.serializers import serialize
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from easy_pdf.views import PDFTemplateView
from django.contrib.auth.decorators import permission_required
from django.views import generic
from django.template import Context
from django.template.loader import get_template
from xhtml2pdf import pisa 

from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q
from django.db import models
from django.core import serializers

from home import utils, mybarcode
from backend.models import DeleteLog
from .forms import WorksheetForm,AttachSamplesForm
from .models import Worksheet,WorksheetSample, WorksheetPrinting, MACHINE_TYPES
from samples.models import Sample, Envelope
from results.models import Result
from . import utils as worksheet_utils

from reportlab.graphics.barcode import code39, code128, code93
from reportlab.graphics.barcode import eanbc, qr, usps
from reportlab.graphics.shapes import Drawing 
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF


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
@permission_required('worksheets.add_worksheet', login_url='/login/')
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

@permission_required('worksheets.add_worksheet', login_url='/login/')	
def create(request, machine_type):
	context = { 'machine_type':machine_type}
	r_file = "media/regimen_info_%s.json"%machine_type
	if request.method == 'POST':
		form = WorksheetForm(request.POST)
		if form.is_valid():
			worksheet = form.save(commit=False)
			worksheet.worksheet_reference_number = worksheet_utils.create_worksheet_ref_number(machine_type,worksheet.sample_type)
			worksheet.machine_type = machine_type
			worksheet.generated_by = request.user
			worksheet.worksheet_medical_lab = utils.user_lab(request)
			worksheet.save()

			return redirect('worksheets:attach_samples', worksheet_id=worksheet.id)
	else:
		init = {'machine_type': machine_type}
		if os.path.exists(r_file):
			with open(r_file, "r") as out:
				data = json.loads(out.read())
				init.update(data)
		form = WorksheetForm(initial=init)
		context = {'form': form, 'machine_type':machine_type}


	return render(request, 'worksheets/create.html', context)

@permission_required('worksheets.add_worksheet', login_url='/login/')
def attach_samples(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	if request.method == 'POST':
		# pass
		ref_number = request.POST.get('ref_number')
		if ref_number!=worksheet.worksheet_reference_number:
			worksheet.worksheet_reference_number = ref_number
			worksheet.save()
		attached_samples = request.POST.getlist('samples')
		worksheet_samples = []
		
		for sample_id in attached_samples:
			instrument_id = request.POST.get('instrument'+sample_id, None)
			sample_rack = request.POST.get('sample_rack'+sample_id, None)
			if sample_rack!=None:
				rack_id = request.POST.get('racks'+sample_rack, None) 
			else:
				rack_id = None
			sample = Sample.objects.get(pk=sample_id)			
			#worksheet.samples.add(sample)
			sample_run = 1+WorksheetSample.objects.filter(sample=sample).count()
			worksheet_samples.append(WorksheetSample(worksheet=worksheet, sample=sample, instrument_id=instrument_id, sample_run=sample_run, rack_id=rack_id))
			sample.in_worksheet = True
			sample.save()

			if(Sample.objects.filter(envelope=sample.envelope, in_worksheet=False, verification__accepted=True).count()==0):
				envelope = Envelope.objects.get(pk=sample.envelope.pk)
				envelope.stage = 3
				envelope.save()

			if Result.objects.filter(sample=sample).exists():
				s_result = Result.objects.get(sample=sample)
				s_result.repeat_test = False
				s_result.save()

		WorksheetSample.objects.bulk_create(worksheet_samples)
			
		return redirect('worksheets:show',worksheet_id)
	else:
		#form = AttachSamplesForm()
		sample_limit = worksheet_utils.sample_limit(worksheet.machine_type)
		#sample_pads = 11 if worksheet.include_calibrators else 3
		# samples = Sample.objects.filter(verification__accepted=True, in_worksheet=False).\
		# 			extra({'lposition_int': "CAST(locator_position as UNSIGNED)"}).\
		# 			order_by('envelope__envelope_number', 'lposition_int')
		# repeat_samples = Sample.objects.filter(result__repeat_test = True)[:sample_limit]
		# samples = Sample.objects.filter(in_worksheet=False).order_by('created_at')[:sample_limit]
		# repeat_samples = Sample.objects.all()[:sample_limit]
		context = {
			#'samples': samples, 
			'worksheet': worksheet,
			'sample_limit': sample_limit,
			# 'sample_pads': sample_pads,
			# 'repeat_samples': repeat_samples, 
			}
		return render(request, 'worksheets/attach_samples.html', context)

def list(request):
	search_val = request.GET.get('search_val')
	if search_val:
		worksheets = Worksheet.objects.filter(worksheet_reference_number__contains=search_val).order_by('-pk')[:1]
		if worksheets:
			worksheet = worksheets[0]
			return redirect('/worksheets/show/%d' %worksheet.pk)

	return render(request,'worksheets/list.html', {'machine_type':request.GET.get('type')})

def show(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	worksheet_samples = worksheet.worksheetsample_set.all().order_by("sample__envelope__envelope_number","sample__locator_position")
	sample_pads = 11 if worksheet.include_calibrators else 3
	context = {'worksheet': worksheet, 'sample_pads': sample_pads, "worksheet_samples":worksheet_samples}
	return render(request, 'worksheets/show.html', context)

def edit(request, worksheet_id):
	if request.method == 'POST':
		pst = request.POST
		rack_id = pst.get('rack_id')
		for x in xrange(1,6):
			pk = pst.get('pk%s'%x)
			instrument_id = pst.get('instrument%s'%x)
			if pk and instrument_id:
				ws = WorksheetSample.objects.get(pk=pk)
				ws.instrument_id = instrument_id 
				ws.rack_id = rack_id
				ws.save()
		return HttpResponse("saved")
	else:
		worksheet = Worksheet.objects.get(pk=worksheet_id)
		worksheet_samples = worksheet.worksheetsample_set.all().order_by("sample__envelope__envelope_number","sample__locator_position")
		sample_pads = 11 if worksheet.include_calibrators else 3
		context = {'worksheet': worksheet, 'sample_pads': sample_pads, "worksheet_samples":worksheet_samples}
		return render(request, 'worksheets/edit.html', context)

def vlprint(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	worksheet_samples = worksheet.worksheetsample_set.all().order_by("sample__envelope__envelope_number","sample__locator_position")
	sample_pads = 11 if worksheet.include_calibrators else 3
	context = {'worksheet': worksheet, 'sample_pads': sample_pads, "worksheet_samples":worksheet_samples}
	WorksheetPrinting.objects.update_or_create(worksheet=worksheet, defaults={'worksheet_printed_by': request.user})	
	return render(request, 'worksheets/vlprint.html', context)

@permission_required('results.add_result', login_url='/login/')
def authorize_list(request, machine_type):

	# has_results_count = models.Count(models.Case(models.When(worksheetsample__stage=2, then=1)))
	# samples_count = models.Count('worksheetsample')
	# worksheets = Worksheet.objects.annotate(sc=samples_count,hrc=has_results_count).filter(hrc=samples_count, machine_type=machine_type)
	tab = request.GET.get('tab')
	if tab=='authorised':
		filters = Q(stage=3, machine_type=machine_type)
	else:
		filters = Q(stage=2, machine_type=machine_type)

	worksheets = Worksheet.objects.filter(filters)
	return render(request,'worksheets/authorize_list.html',{'worksheets':worksheets, 'machine_type':dict(MACHINE_TYPES).get(machine_type)})

@permission_required('results.add_result', login_url='/login/')
def authorize_results(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	if request.method == 'POST':
		push_worksheet = request.POST.get('push_worksheet')
		if push_worksheet=='1':
			worksheet.stage = 3
			worksheet.save()
			return redirect("/worksheets/authorize_list/%s/"%worksheet.machine_type)

		sample_id = request.POST.get('sample_pk')
		result = Result.objects.filter(sample_id=sample_id).first()
		if not result:
			result = Result()
			result.sample_id = sample_id
			result.result1 = 'Invalid'
			result.result_numeric = 0
			result.result_alphanumeric = 'Failed'
			result.suppressed = 3
			result.method = worksheet.machine_type
			result.test_date = timezone.now()
			result.test_by = request.user
			result.save()

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
		ws = WorksheetSample.objects.filter(worksheet=worksheet, sample=result.sample).first()
		ws.stage = 4 if choice == 'reschedule' else 3
		ws.save()
		if(WorksheetSample.objects.filter(worksheet=worksheet, stage__lte=2).count()==0):
			worksheet.stage = 3
			worksheet.save()
			return HttpResponse("completed")

		return HttpResponse("saved")
	else:
		sample_pads = 11 if worksheet.include_calibrators else 3
		context = {'worksheet': worksheet, 'sample_pads': sample_pads}
		return render(request, 'worksheets/authorize_results.html', context)

def _get_pending_samples():
	pass

def pending_samples(request):	
	repeat = request.GET.get('repeat')
	sample_type = request.GET.get('sample_type')
	stats = request.GET.get('stats')

	if stats:
		rsc = Sample.objects.filter(result__repeat_test=1, sample_type=sample_type).count()
		psc = Sample.objects.filter(verified=True, verification__accepted=True, in_worksheet=False, result__pk=None, sample_type=sample_type).count()
		return HttpResponse(json.dumps({'repeat_samples_count':rsc, 'pending_samples_count':psc}))
	elif repeat:
		fltrs = {'result__repeat_test':True}
		if sample_type:
			fltrs.update({'sample_type':sample_type})

		samples = Sample.objects.filter(**fltrs)
	else:
		sample_search = request.GET.get('sample_search')
		env_pk = request.GET.get('env_pk')
		repeat_sample_search = request.GET.get('repeat_sample_search')
		filters = {'verified':True, 'verification__accepted':True}
		if env_pk:
			filters.update({'envelope':env_pk})
		elif sample_search:
			filters.update({'form_number':sample_search})
		elif repeat_sample_search:
			filters.update({'form_number':repeat_sample_search, 'result__repeat_test':True})

		samples = Sample.objects.filter(**filters)
	ret=[]
	samples = samples.extra({'lposition_int': "CAST(locator_position as UNSIGNED)"}).order_by('envelope__envelope_number', 'lposition_int')[:300]

	for i,s in enumerate(samples):
		ret.append({
				'index': i,
				'id': s.id,
				'vl_sample_id': s.vl_sample_id,
				'locator_id': "%s%s/%s"  %(s.locator_category, s.envelope.envelope_number, s.locator_position),
				'form_number': s.form_number,
				'hep_number': s.patient.hep_number,
				'sample_type': s.sample_type,
				'in_worksheet': s.in_worksheet,
			})
	return HttpResponse(json.dumps(ret))

def pending_envelopes(request):
	# unverified_count = models.Count(models.Case(models.When(sample__verified=False, then=1)))
	# nein_worksheet_count = models.Count(models.Case(models.When(sample__in_worksheet=False, then=1)))
	# st = request.GET.get('sample_type')
	# st_count = models.Count(models.Case(models.When(sample__sample_type=st, then=1)))
	# envelopes = Envelope.objects.annotate(smpl_count=models.Count('sample'),uc=unverified_count, nwc=nein_worksheet_count, stc=st_count).filter(uc=0, nwc__gt=0, stc__gt=0)
	#envelopes = Envelope.objects.annotate(models.Count('sample'))

	ret = []
	sample_type = request.GET.get('sample_type', '')
	filter_params = Q(stage=2, sample_type=request.GET.get('sample_type', ''), sample_medical_lab=utils.user_lab(request))
	envelopes = Envelope.objects.annotate(sample_count=models.Count('sample')).filter(filter_params).order_by('envelope_number')
	for i,e in enumerate(envelopes):
		ret.append({'pk':e.pk,'envelope_number':e.envelope_number,'sample_count':e.sample_count})
	return HttpResponse(json.dumps(ret))

def delete(request, pk):
	if request.method == 'POST':
		worksheet = Worksheet.objects.get(pk=pk)
		delete_reason = request.POST.get('delete_reason')
		delete_log = DeleteLog()
		delete_log.ref_number = worksheet.worksheet_reference_number
		delete_log.section = "worksheets"
		delete_log.delete_reason = delete_reason
		delete_log.data = "{worksheet:%s, worksheet_samples:%s}"%(serialize('json', [worksheet]), serialize('json', worksheet.worksheetsample_set.all()))
		delete_log.deleted_by = request.user
		delete_log.save()		
		
		for s in worksheet.samples.all():
			if hasattr(s, 'result'):
				s.result.repeat_test = 1
				s.result.save()
			else:
				s.in_worksheet = False
				s.envelope.stage = 2
				s.envelope.save()
				s.save()

		worksheet.delete()
		return HttpResponse("Successfully deleted")
	else:
		return HttpResponse("Deleting failed")

def reg_info(request, machine_type):
	context = { 'machine_type':machine_type}
	r_file = "media/regimen_info_%s.json"%machine_type
	if request.method == 'POST':
		posted_data = request.POST
		posted_data._mutable = True
		posted_data.pop('csrfmiddlewaretoken')
		with open(r_file, "w") as out:
			data = json.dumps(posted_data)
			out.write(data)
		return redirect('worksheets:reg_info', machine_type=machine_type)
	else:
		init = {'machine_type': machine_type}
		if os.path.exists(r_file):
			with open(r_file, "r") as out:
				data = json.loads(out.read())
				init.update(data)
		
		form = WorksheetForm(initial=init)
		context = {'form': form, 'machine_type':machine_type}


	return render(request, 'worksheets/reg_info.html', context)

def get_instrument_id(request):
	instrument_id = request.GET.get('instrument_id')
	ws = WorksheetSample.objects.filter(instrument_id=instrument_id).first()

	return HttpResponse(1) if ws else HttpResponse(0)

def barcodes(request, pk):
	worksheet = Worksheet.objects.get(pk=pk)
	worksheet_samples = worksheet.worksheetsample_set.all().order_by("sample__envelope__envelope_number","sample__locator_position")
	WorksheetPrinting.objects.update_or_create(worksheet=worksheet, defaults={'worksheet_printed_by': request.user})
	return render(request, 'worksheets/barcodes.html', {'worksheet':worksheet, 'worksheet_samples':worksheet_samples})

# def barcodes(request, pk):
# 	#instantiate a drawing object
# 	d = mybarcode.MyBarcodeDrawing("V1806-0001/002")
# 	binaryStuff = d.asString('gif')
# 	return HttpResponse(binaryStuff, 'image/gif')

	
class ListJson(BaseDatatableView):
	model = Worksheet
	columns = ['worksheet_reference_number', 'machine_type', 'sample_type', 'created_at','stage', 'printed','pk']
	order_columns = ['worksheet_reference_number', 'machine_type', 'sample_type', 'created_at','stage', 'worksheetprinting.pk','']
	max_display_length = 500

	def render_column(self, row, column):
		machine_type = self.request.GET.get('machine_type')
		if column == 'pk':
			url0 = "/worksheets/show/{0}".format(row.pk)
			url1 = "javascript:windPop(\"/worksheets/vlprint/{0}\")".format(row.pk)
			url2 = "/worksheets/edit/{0}".format(row.pk)
			#url2 = "javascript:windPop(\"/worksheets/pdf/{0}\")".format(row.pk)
			url3 = "/results/cobas_upload/?type=C" if row.machine_type=='C' else "/results/upload/{0}".format(row.pk) 
			#url4 = "/worksheets/delete/{0}".format(row.pk)
			url4 = "javascript:deleteWorksheet(\"{0}\", \"{1}\")".format(row.pk, row.worksheet_reference_number)
			url5 = "/worksheets/show/{0}/?show_results=1".format(row.pk)
			

			if machine_type:
				links = "<a href='%s'>upload</a>" %url3
			else:
				links = utils.dropdown_links([
					{"label":"view", "url":url0},
					{"label":"Print", "url":url1},
					{"label":"Edit", "url":url2},
					{"label":"Upload Results", "url": url3},
					{"label":"Delete", "url":url4},
					{"label":"view with results", "url":url5},
				])

			return links
		elif column == 'printed':
			return "yes" if hasattr(row, 'worksheetprinting') else "no"
		else:
			return super(ListJson, self).render_column(row, column)

	def filter_queryset(self, qs):
		tab = self.request.GET.get('tab')
		search = self.request.GET.get(u'search[value]', None)
		machine_type = self.request.GET.get('machine_type')
		qs = qs.filter(worksheet_medical_lab=utils.user_lab(self.request))

		if tab=='pending_p':
			qs = qs.filter(worksheetprinting__isnull=True)
		elif tab=='pending_r':
			qs = qs.filter(stage=1)

		if search:
			qs = qs.filter(worksheet_reference_number__icontains=search)
		if machine_type:
			qs = qs.filter(machine_type=machine_type, stage=1)
		return qs
