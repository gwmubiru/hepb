import json, base64
from datetime import date as dt, datetime as dtime,timedelta
import os.path
from django.conf import settings
from django.core.serializers import serialize
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
#from easy_pdf.views import PDFTemplateView
#from easy_pdf.rendering import render_to_pdf_response
from django.contrib.auth.decorators import permission_required
from django.views import generic
from django.template import Context
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q,Count, Case, When, IntegerField
from django.db import models
from django.core import serializers

from home import utils
from home import programs
from home import db_aliases
from backend.models import DeleteLog, Facility
from .forms import WorksheetForm,AttachSamplesForm
from .models import Worksheet,WorksheetSample, WorksheetPrinting,ResultRunDetail, MACHINE_TYPES,WorksheetEnvelope
from samples.models import Sample, Envelope,SampleReception,SampleIdentifier,EnvelopeAssignment
from results.models import Result
from worksheets.models import ResultRun
from . import utils as worksheet_utils
from samples import utils as sample_utils
from vl import services as vl_services

from reportlab.graphics.barcode import code39, code128, code93
from reportlab.graphics.barcode import eanbc, qr, usps
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from home import utils
from django.db import transaction
from django.db import connections
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import *


def get_program_db_alias(request):
	return db_aliases.get_program_db_alias(programs.get_active_program_code(request))

# Create your views here.

@permission_required('worksheets.add_worksheet', login_url='/login/')
#def generate_pdf(request, worksheet_id):
#	worksheet = Worksheet.objects.get(pk=worksheet_id)
#	template = get_template("worksheets/pdf.html")
#	html = template.render(Context({'worksheet': worksheet}))
#	f = open('worksheet.pdf', "w+b")
#	pisa_status = pisa.CreatePDF(html.encode('utf-8'), dest=f, encoding='utf-8')
#
#	f.seek(0)
#	pdf = f.read()
#	f.close()
#	return HttpResponse(pdf, 'application/pdf')

def generate_pdf(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	template = get_template("worksheets/pdf.html")
	html = template.render(Context({'worksheet': worksheet}))
	# Use BytesIO instead of physical file
	buffer = BytesIO()
	# Create PDF in memory
	pisa_status = pisa.CreatePDF(html.encode('utf-8'), dest=buffer, encoding='utf-8')
	if pisa_status.err:
		return HttpResponse('PDF generation error', status=500)
	# No file handles to worry about
	pdf = buffer.getvalue()
	buffer.close()
	response = HttpResponse(pdf, content_type='application/pdf')
	response['Content-Disposition'] = 'filename="worksheet.pdf"'
	return response

@permission_required('worksheets.add_worksheet', login_url='/login/')
def choose_machine_type(request):
	if request.method == 'POST':
		#add redirect to the relevant red
		context = {
			'sample_type': request.POST.get('sample_type'),
			'process_type': request.POST.get('process_type'),
			'machine_type':request.POST.get('machine_type')
		}
		if request.POST.get('process_type') == 'R':
			return redirect('worksheets:create',request.POST.get('machine_type'),request.POST.get('sample_type'),request.POST.get('process_type'))
		else:
			#return redirect('worksheets:create',request.POST.get('machine_type'),request.POST.get('sample_type'),request.POST.get('process_type'))
			d = timezone.now()

			#return HttpResponse(int(worksheet_reference_number[7:11]))
			worksheet, created = Worksheet.objects.update_or_create(
				starting_locator_id=d.strftime("%Y%m%d%H%M%S"),
				ending_locator_id=d.strftime("%Y%m%d%H%M%S")+'u',
				machine_type=request.POST.get('machine_type'),
				sample_type=request.POST.get('sample_type'),
				worksheet_reference_number = worksheet_utils.create_worksheet_ref_number(request.POST.get('machine_type'),request.POST.get('sample_type')),
				defaults={'generated_by': request.user,'worksheet_medical_lab':utils.user_lab(request)}
			)
			worksheet.save()
			return redirect('worksheets:attach_samples', worksheet_id=worksheet.id)
	else:
		return render(request, 'worksheets/choose_machine.html')

@permission_required('worksheets.add_worksheet', login_url='/login/')

def does_worksheet_sample_number_exist(request, ws):
	if WorksheetSample.objects.filter(instrument_id=ws).exists():
		return HttpResponse('exits')
	else:
		return HttpResponse('')


@permission_required('worksheets.add_worksheet', login_url='/login/')
@transaction.atomic
def update(request, sample_type):
	return redirect('worksheets:attach_samples', worksheet_id=115586)

def update_status(request, worksheet_id):
	#update the stage of worksheet and all corresponding worksheet_samples
	new_stage = request.GET.get('stage')
	
	with connections['default'].cursor() as cursor:
		cursor.execute("UPDATE vl_worksheets SET stage=%s WHERE id=%s",[new_stage,worksheet_id])
		cursor.execute("UPDATE vl_worksheet_samples SET stage=%s WHERE worksheet_id=%s",[new_stage,worksheet_id])
	envelopes = worksheet_utils.get_worksheet_envelopes(worksheet_id,'obj')
	
	for envelope in envelopes:
		envelope.stage = new_stage
		envelope.save()

	return redirect(request.META.get('HTTP_REFERER'))

@permission_required('worksheets.add_worksheet', login_url='/login/')
def attach_samples(request, stage,sample_type):

	if request.method == 'POST':
		# pass
		ref_number = request.POST.get('ref_number')
		attached_samples = request.POST.getlist('samples')
		worksheet_samples = []
		
		for sample_id in attached_samples:
			sample = Sample.objects.get(pk=sample_id)
			if stage == '10':
				ws = WorksheetSample.objects.get(sample=sample_id)
				if ws:
					ws.stage = 10
					ws.save()
					if(Sample.objects.filter(envelope=sample.envelope, in_worksheet=False, verification__accepted=True).count()==0):
						envelope = Envelope.objects.get(pk=sample.envelope.pk)
						envelope.stage = 15
						envelope.save()
			else:
				worksheet = Worksheet()
				worksheet.worksheet_reference_number = request.POST.get('worksheet_reference_number')
				worksheet.sample_type = sample_type
				worksheet.generated_by = request.user
				worksheet.worksheet_medical_lab = utils.user_lab(request)
				worksheet.save()
				
				sample_run = 1+WorksheetSample.objects.filter(sample=sample).count()
				worksheet_samples.append(WorksheetSample(worksheet=worksheet, sample=sample, instrument_id=instrument_id, sample_run=sample_run))
				sample.in_worksheet = True
				sample.save()

				if(Sample.objects.filter(envelope=sample.envelope, in_worksheet=False, verification__accepted=True).count()==0):
					envelope = Envelope.objects.get(pk=sample.envelope.pk)
					envelope.stage = 15
					envelope.save()

				if Result.objects.filter(sample=sample).exists():
					s_result = Result.objects.get(sample=sample)
					s_result.repeat_test = False
					s_result.save()

		if stage == 10:
			WorksheetSample.objects.bulk_create(worksheet_samples)
	else:

		sample_limit = worksheet_utils.sample_limit(sample_type)
		context = {
			'stage': stage,
			'sample_type': sample_type,
			'sample_limit': sample_limit,
			}
		return render(request, 'worksheets/attach_samples.html', context)

@permission_required('results.add_result', login_url='/login/')
def manage_repeats(request):

	if request.method == 'POST':
		
		sample_id = request.POST.get('s_pk')
		barcode = request.POST.get('barcode')
		worksheet_id = request.POST.get('worksheet_id')
		index_val = int(request.POST.get('index_val'))
		max_samples = int(request.POST.get('max_samples'))
		worksheet_type = request.POST.get('worksheet_type')
		index_val = index_val +1

		sample_run = (WorksheetSample.objects.filter(sample_id = sample_id).count())+1
		
		#save the worksheet sample
		worksheet_id = request.POST.get('worksheet_id')
		s = Sample.objects.get(pk=sample_id)
		if worksheet_type == 'fell_off':
			#mark existing barcode as not used  - stage 8
			with connections['default'].cursor() as cursor:
				cursor.execute("UPDATE vl_worksheet_samples SET stage=%s WHERE sample_id=%s and (stage=1 or stage=2)",[8,s.id])
		#check that the barcode is not already used at this level
		ws = WorksheetSample.objects.filter(instrument_id = barcode).first()
		ret = {}
		if ws is None:
			ws = WorksheetSample.objects.create(worksheet_id=worksheet_id,sample_run=sample_run, instrument_id=barcode,stage=1,sample_id=s.id)
			#mark the sample identifier as waiting for results for repeats  - stage 6
			s.stage = 6 
			s.save()
			ret = {'message':'Saved','identifier_id':sample_id,'index_val':index_val,'max_samples':max_samples,'worksheet_id':worksheet_id}
		#add envelope to worksheet
		worksheet_utils.create_worksheet_envelope(ws.sample.envelope.id,worksheet_id,request.user.id)
		#push the worksheet sample to stage 3
		if index_val == max_samples:
			return redirect('/worksheets/show/%d' %int(worksheet_id))
		else:
			return HttpResponse(json.dumps(ret))
	else:
		worksheet = Worksheet()
		worksheet.generated_by=request.user
		worksheet.sample_type=request.GET.get('sample_type')		
		worksheet.stage = 12
		worksheet.is_repeat = 1
		worksheet.worksheet_medical_lab=utils.user_lab(request)
		worksheet.worksheet_reference_number =utils.timestamp()
		worksheet.save()
		worksheet.worksheet_reference_number = worksheet_utils.create_worksheet_ref_number(request.GET.get('sample_type'),worksheet.id)+'R'
		worksheet.save()
		#get the correspnding samples
		if request.GET.get('worksheet_type') == 'fell_off':
			time_threshold = timezone.now() - timedelta(days=7)
			samples = programs.filter_queryset_by_program(request, Sample.objects.filter(Q(stage=6) | Q(stage=1),sample_type='D',updated_at__lte=time_threshold), 'envelope__program_code').order_by('barcode')
		else:
			samples = programs.filter_queryset_by_program(request, Sample.objects.filter(stage=4,sample_type='D'), 'envelope__program_code').order_by('barcode')
		context = {'samples': samples,'worksheet_id':worksheet.id}
		return render(request, 'worksheets/create_repeats.html', context)

def manage_plasma_repeats(request):
	
	if request.method == 'POST':

		samples = request.POST.getlist('samples')
		if len(samples):
			worksheet = Worksheet()
			worksheet.generated_by=request.user
			worksheet.sample_type='P'		
			worksheet.stage = 12
			worksheet.is_repeat = 1
			worksheet.worksheet_medical_lab=utils.user_lab(request)
			worksheet.worksheet_reference_number =utils.timestamp()
			worksheet.save()
			worksheet.worksheet_reference_number = worksheet_utils.create_worksheet_ref_number('P',worksheet.id)+'R'
			worksheet.save()

			for s_pk in samples:
				s = Sample.objects.get(pk = s_pk)
				sample_run = (WorksheetSample.objects.filter(sample_id = s.id).count())+1
				
				#save the worksheet sample
				worksheet_id = request.POST.get('worksheet_id')
				inst_id = s.barcode
				if s.facility_reference is not None:
					inst_id = s.facility_reference
				ws = WorksheetSample.objects.create(worksheet_id=worksheet.id, sample_id = s.id,sample_run=sample_run, instrument_id=inst_id,stage=1)
				s.stage = 6
				s.save()
				worksheet_utils.create_worksheet_envelope(s.envelope.id,worksheet.id,request.user.id)	
			return redirect('/worksheets/show/%d' %worksheet.pk)
		else:
			return HttpResponse("Select atleast one sample")
	else:
		sis = programs.filter_queryset_by_program(request, Sample.objects.filter(stage=4,sample_type='P'), 'envelope__program_code').order_by('barcode')
		page = request.GET.get('page', 1)
		paginator = Paginator(sis, 100)
		try:
			samples = paginator.page(page)
		except PageNotAnInteger:
			samples = paginator.page(1)
		except EmptyPage:
			samples = paginator.page(paginator.num_pages)
		return render(request, 'worksheets/plasma_repeats.html', {'samples': samples})

def list_page(request):
	search_val = request.GET.get('search_val')
	if search_val:
		worksheets = Worksheet.objects.filter(worksheet_reference_number__contains=search_val).order_by('-pk')[:1]
		if worksheets:
			worksheet = worksheets[0]
			return redirect('/worksheets/show/%d' %worksheet.pk)

	return render(request,'worksheets/list.html', {
		'machine_type':request.GET.get('type'),
	})

def show(request, worksheet_id):
	if vl_services.is_hiv_program(request):
		worksheet, worksheet_samples = vl_services.worksheet_detail(worksheet_id)
		if worksheet is None:
			return HttpResponse("Worksheet not found", status=404)
		context = {'worksheet': worksheet, 'sample_pads': 0, "worksheet_samples":worksheet_samples}
		return render(request, 'worksheets/show.html', context)
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	worksheet_samples = WorksheetSample.objects.filter(worksheet_id = worksheet_id).order_by("sample__barcode")
	
	sample_pads = worksheet_utils.sample_pads(worksheet)
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
		sample_pads = worksheet_utils.sample_pads(worksheet)
		context = {'worksheet': worksheet, 'sample_pads': sample_pads, "worksheet_samples":worksheet_samples}
		return render(request, 'worksheets/edit.html', context)

def vlprint(request, worksheet_id):
	worksheet = Worksheet.objects.get(pk=worksheet_id)
	worksheet_samples = WorksheetSample.objects.filter(worksheet_id = worksheet_id).order_by("instrument_id")
	
	sample_pads = worksheet_utils.sample_pads(worksheet)
	context = {'worksheet': worksheet, 'sample_pads': sample_pads, "worksheet_samples":worksheet_samples}
	WorksheetPrinting.objects.update_or_create(worksheet=worksheet, defaults={'worksheet_printed_by': request.user})
	return render(request, 'worksheets/vlprint.html', context)

@permission_required('results.add_result', login_url='/login/')
def authorize_list(request, machine_type):

	tab = request.GET.get('tab')
	if tab=='authorised':
		filters = Q(stage=3, worksheet_medical_lab=utils.user_lab(request))
	else:
		filters = Q(stage=2, worksheet_medical_lab=utils.user_lab(request))

	worksheets = Worksheet.objects.filter(filters)
	return render(request,'worksheets/authorize_list.html',{'worksheets':worksheets, 'machine_type':dict(MACHINE_TYPES).get(machine_type)})

@permission_required('results.add_result', login_url='/login/')
@transaction.atomic
def authorize_results(request):
	if vl_services.is_hiv_program(request):
		rs_id = request.GET.get('run_id')
		facilities = Facility.objects.all()
		if request.method == 'POST':
			if 'run_id' in request.POST and request.POST.get('is_multi_approval') == 'No':
				run_id = request.POST.get('run_id')
				for ws in vl_services.release_result_rows(run_id=run_id):
					vl_services.authorize_worksheet_sample(ws.pk, request.POST.get('choice_type') or 'release', request.user)
				return redirect("/worksheets/authorize_runs/")
			if 'ws_pk' in request.POST:
				vl_services.authorize_worksheet_sample(request.POST.get('ws_pk'), request.POST.get('choice'), request.user)
				return HttpResponse("saved")
			worksheet_samples = request.POST.getlist('worksheet_samples')
			for ws_id in worksheet_samples:
				vl_services.authorize_worksheet_sample(ws_id, request.POST.get('choice_type'), request.user)
			return redirect('/worksheets/authorize_results/?run_id=%d&stage=1&tab=received' % int(request.POST.get('run_id')))
		context = {'result_run_details': vl_services.authorize_result_rows(rs_id), 'run_id':rs_id,'facilities':facilities}
		return render(request, 'worksheets/authorize_and_release_results.html', context)
	
	envelope_id = request.GET.get('envelope_id')
	rs_id = request.GET.get('run_id')
	facilities = Facility.objects.all()
	if request.method == 'POST':
		if 'run_id' in request.POST and request.POST.get('is_multi_approval') == 'No':
			run_id = request.POST.get('run_id')
			WorksheetSample.objects.filter(result_run_id=run_id).update(stage=2)
			run = ResultRun.objects.filter(pk=run_id).first()
			run.stage = 2;
			run.save()
			return redirect("/worksheets/authorize_runs/")

		if 'ws_pk' in request.POST:
			manage_results(request.POST.get('ws_pk'),request.POST.get('choice'),request.user)
			return HttpResponse("saved")
		else:
			#save the multiple authorize, reschedule or invalid
			worksheet_samples = request.POST.getlist('worksheet_samples')
			for ws_id in worksheet_samples:
				manage_results(ws_id, request.POST.get('choice_type'),request.user)
			return redirect('/worksheets/authorize_results/?run_id=%d&stage=1&tab=received' %int(request.POST.get('run_id')))
	else:
		
		result_run_details = ResultRunDetail.objects.filter(the_result_run_id = rs_id).order_by('result_run_position')
		
		context = {'result_run_details': result_run_details,'run_id':rs_id,'facilities':facilities}
		return render(request, 'worksheets/authorize_and_release_results.html', context)

# authorize, reschedule or invalidate
def manage_results(ws_pk,choice,user):
	ws = WorksheetSample.objects.filter(pk=ws_pk).first()
	#sample_id = request.POST.get('sample_pk')
	if ws.result_alphanumeric == '':
		#ignore this 
		ws_ignored = ws
		ws = WorksheetSample.objects.filter(instrument_id=ws_ignored.instrument_id, stage=4).last()
		ws_ignored.delete()
	ws.stage = ws.sample.stage = 4 if choice == 'reschedule' else 3
	ws.authorised_at = timezone.now()
	ws.authoriser = user
	if choice == 'reschedule' and ws.sample.sample_type == 'D':
		ws.repeat_test = 1
	ws.sample.save();
	ws.save()
	update_sample(ws)

def update_sample(ws):
	if ws.sample.sample is None:
		sample = Sample.objects.filter(barcode = ws.sample.barcode).first()
		if sample:
			ws.sample.sample = sample
			ws.sample.save()
			ws.sample = sample
			ws.save()

def attach_results(request):
	worksheet_samples = WorksheetSample.objects.filter(result_run_id=request.GET.get('run_id'))
	for ws in worksheet_samples:
		sample =  Sample.objects.filter(barcode=ws.instrument_id).first()
		if sample:

			#check if sample has result
			result = Result.objects.filter(sample=sample).first()
			if not result:
				#create the result
				result = Result()

			ws.sample =sample
			ws.save()

			result.repeat_test = ws.repeat_test
			result.suppressed = ws.suppressed
			result.method = ws.method
			result.result_numeric = ws.result_numeric
			result.result_alphanumeric = ws.result_alphanumeric
			result.test_date = ws.test_date
			result.result1 =ws.result_alphanumeric
			result.sample =sample
			result.test_by =ws.tester
			result.save()

	context = {'worksheet_samples': worksheet_samples,'run_id':request.GET.get('run_id')}
	return render(request, 'worksheets/all_authorize_results.html', context)

@permission_required('results.add_result', login_url='/login/')
def authorize_runs(request):
	if vl_services.is_hiv_program(request) and request.GET.get('auth_by') == 'runs':
		if request.method == 'POST':
			pass
		else:
			stage = int(request.GET.get('stage'))
			context = {'runs': vl_services.authorize_runs(stage=stage),'stage':stage}
			return render(request, 'worksheets/authorize_runs.html', context)
	
	if request.GET.get('auth_by') == 'runs':		
		if request.method == 'POST':
			push_worksheet = request.POST.get('push_worksheet')
		else:			
			stage = int(request.GET.get('stage'))
			if stage == 1:
				runs = ResultRun.objects.annotate(no_results=models.Count('the_run'),invalid_results=models.Count('the_run',filter=Q(the_run__result_alphanumeric='Invalid'))).filter(stage=1)
			else:
				runs = ResultRun.objects.annotate(no_results=models.Count('the_run'),invalid_results=models.Count('the_run',filter=Q(the_run__result_alphanumeric='Invalid'))).filter(stage__lte=4)
			
			context = {'runs': runs,'stage':stage}
			return render(request, 'worksheets/authorize_runs.html', context)
	else:

		if request.method == 'POST':
			push_worksheet = request.POST.get('push_worksheet')
		else:
			stage = request.GET.get('stage')
			sample_type = request.GET.get('sample_type')
			if not stage or stage == 1:
				envelopes = Envelope.objects.annotate(accepted_sample_count=models.Count('sample',filter=Q(sample__stage=2))).filter(id__gte=settings.ENVELOPE_SAMPLES_CUT_OFF,stage=stage,sample_type=sample_type)
			else:
				envelopes = Envelope.objects.annotate(accepted_sample_count=models.Count('sample',filter=Q(sample__stage=3))).filter(id__gte=settings.ENVELOPE_SAMPLES_CUT_OFF,stage=stage,sample_type=sample_type)

			context = {'envelopes': envelopes,'stage':stage,'sample_type':sample_type}
			return render(request, 'worksheets/authorize_envelopes.html', context)


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
				'hep_number': '',
				'sample_type': s.sample_type,
				'in_worksheet': s.in_worksheet,
				'barcode': s.barcode,
			})
	return HttpResponse(json.dumps(ret))

def pending_envelopes(request):

	ret = []
	sample_type = request.GET.get('sample_type', '')
	filter_params = Q(stage=10, sample_type=request.GET.get('sample_type', ''), sample_medical_lab=utils.user_lab(request))
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
	r_file = os.path.join(settings.MEDIA_ROOT, "regimen_info_%s.json"%machine_type)
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


def dilute_sample(request):
	ws = WorksheetSample.objects.get(pk=request.POST.get('ws_pk'))
	ws.is_diluted = 1
	ws.save()
	ws.sample.is_diluted = 1
	ws.sample.save()
	return HttpResponse('saved')


class ListJson(BaseDatatableView):
	model = Worksheet
	columns = ['worksheet_reference_number', 'envelopes', 'sample_type', 'program', 'Timestamp', 'created_at','eluted?','eluted_pippeted_at','loaded?','loaded_at','stage','pk']
	order_columns = ['worksheet_reference_number', '', 'sample_type', '', 'created_at', 'created_at','stage','','','','stage','']
	max_display_length = 500

	def render_column(self, row, column):
		if vl_services.is_hiv_program(self.request):
			if column == 'pk':
				return utils.dropdown_links([
					{"label":"view", "url":"/worksheets/show/{0}".format(row.pk)},
				])
			elif column == 'envelopes':
				return vl_services.worksheet_envelope_links(row.pk)
			elif column == 'program':
				return 'HIV Viral Load'
			elif column == 'created_at':
				return utils.set_page_dates_format(row.created_at)
			elif column == 'Timestamp':
				return utils.set_date_time_stamp(row.created_at)
			elif column == 'eluted?':
				return 'Repeat' if row.stage == 11 else 'Normal'
			elif column == 'loaded?':
				return 'No' if row.stage == 12 else 'Yes'
		machine_type = self.request.GET.get('machine_type')
		if column == 'pk':
			url0 = "/worksheets/show/{0}".format(row.pk)
			url1 = "javascript:windPop(\"/worksheets/vlprint/{0}\")".format(row.pk)
			url2 = "/worksheets/edit/{0}".format(row.pk)
			url3 = "/results/cobas_upload/?type=C" if row.machine_type=='C' else "/results/upload/{0}".format(row.pk)
			url4 = "javascript:deleteWorksheet(\"{0}\", \"{1}\")".format(row.pk, row.worksheet_reference_number)
			url5 = "/samples/range_envelopes/?type=2&wksht_id={0}".format(row.pk)
			url6 = "/worksheets/show/{0}/?preview=1".format(row.pk)

			if machine_type:
				links = "<a href='%s'>upload</a>" %url3
			else:
				links = utils.dropdown_links([
					{"label":"view", "url":url0},
					{"label":"Print", "url":url1},
					{"label":"Edit", "url":url2},
					{"label":"Reassign envelopes", "url":url5},
				])

			return links
		elif column == 'eluted?':
			if row.stage==11:				
				return 'Repeat'
			else:
				return 'Normal'

		elif column == 'loaded?':
			if row.stage==12:
				load_link = "/worksheets/update_status/{0}".format(row.pk)+"?stage=1"
				return 'No <a href="'+load_link+'">Mark loaded</a>'
			else:
				return 'Yes'

		elif column == 'envelopes':
			return worksheet_utils.get_worksheet_envelopes(row.pk)
		elif column == 'program':
			programs = row.worksheetenvelope_set.values_list('envelope__program_code', flat=True).distinct()
			labels = [dict(Envelope.PROGRAM_CODES).get(program_code) for program_code in programs if program_code]
			return ', '.join(labels)
		elif column == 'created_at':
			return utils.set_page_dates_format(row.created_at)
		elif column == 'Timestamp':
			return utils.set_date_time_stamp(row.created_at)
			
		else:
			return super(ListJson, self).render_column(row, column)

	def filter_queryset(self, qs):
		if vl_services.is_hiv_program(self.request):
			tab = self.request.GET.get('tab')
			sample_type = self.request.GET.get('sample_type')
			search = self.request.GET.get(u'search[value]', None)
			qs = qs.using('vl_lims').filter(worksheet_medical_lab_id=utils.user_lab(self.request).id)
			if sample_type:
				qs = qs.filter(sample_type=sample_type)
			if tab=='pending_e':
				qs = qs.filter(stage=11)
			elif tab=='pending_l':
				qs = qs.filter(stage=12)
			elif tab=='pending_r':
				qs = qs.filter(stage=1)
			if search:
				qs = qs.filter(worksheet_reference_number__icontains=search)
			return qs
		tab = self.request.GET.get('tab')
		sample_type = self.request.GET.get('sample_type')
		search = self.request.GET.get(u'search[value]', None)
		machine_type = self.request.GET.get('machine_type')
		qs = qs.filter(worksheet_medical_lab=utils.user_lab(self.request))

		if sample_type:
			qs = qs.filter(sample_type=sample_type)

		if tab=='pending_e':
			qs = qs.filter(stage=11)
		elif tab=='pending_l':
			qs = qs.filter(stage=12)
		elif tab=='pending_r':
			qs = qs.filter(stage=1)
		
		if search:
			#search = search.replace('-','')
			#qs = qs.filter(worksheetenvelope__envelope__envelope_number__icontains=search).distinct()
			qs = qs.filter(worksheetenvelope__envelope__envelope_number__icontains=search).distinct()
		qs = programs.filter_queryset_by_program(self.request, qs, 'worksheetenvelope__envelope__program_code').distinct()
		if machine_type:
			qs = qs.filter(machine_type=machine_type, stage=1)
		return qs

	def get_initial_queryset(self):
		if vl_services.is_hiv_program(self.request):
			from vl.models import VLWorksheet
			return VLWorksheet.objects.using('vl_lims').all()
		return super(ListJson, self).get_initial_queryset()

def lab_samples(request):
	search_val = request.GET.get('search_val')
	stage = request.GET.get('stage')
	return render(request, 'worksheets/lab_samples.html', {'global_search':search_val })

class LabSamplesJson(BaseDatatableView):
	model = WorksheetSample
	columns = ['instrument_id','barcode','sample_type','envelope_number','worksheet_number','date_added_to_lab']
	order_columns = ['barcode','sample__envelope__envelope_number']
	max_display_length = 500
					
	def render_column(self, row, column):
		
		if column == 'barcode':
			return row.sample.barcode
		elif column == 'sample_type':
			return 'Plasma' if row.sample.sample_type == 'P' else'DBS'
		elif column == 'envelope_number':
			env_no = row.sample.envelope.envelope_number
			env_str = '<a href="/samples/search/?search_val=%s&search_env=1" style="margin-left:5px;">%s</a>'%(env_no,env_no)
			return env_str 

		elif column == 'worksheet_number':
			wst_no = row.worksheet.worksheet_reference_number
			wst_str = '<a href="/worksheets/show/%d" style="margin-left:5px;">%s</a>'%(row.worksheet.id,wst_no)
			return wst_str 
				
		elif column == 'date_added_to_lab':
			return utils.set_page_date_only_format(row.worksheet.created_at)					
		else:
			return super(LabSamplesJson, self).render_column(row, column)


	def filter_queryset(self, qs):
		search = self.request.GET.get(u'search[value]', None)
		stage = int(self.request.GET.get('stage'))
		global_search = self.request.GET.get('global_search', None)
		
		qs_params = Q()
		stage_query = Q(sample__stage=stage)
		if stage == 1:
			stage_query = Q(sample__stage=1) | Q(sample__stage = 6)
		
		if search:
			qs_params = qs_params & Q(sample__barcode=search) | Q(sample__envelope__envelope_number=search) | Q(instrument_id=search)
		
		qs = programs.filter_queryset_by_program(self.request, qs, 'sample__envelope__program_code')
		return qs.filter(qs_params,stage_query).order_by('instrument_id')	

def get_pending_samples(request):
	stage = int(request.GET.get('stage'))
	env_id = request.GET.get('env_id')
	query = Q(stage=stage,envelope_id=env_id)

	sis = programs.filter_queryset_by_program(request, Sample.objects.filter(query), 'envelope__program_code').order_by('barcode')
	ret = []
	for i,s in enumerate(sis):
		ret.append({'pk':s.pk,'barcode':s.barcode,'form_number':s.form_number,'facility_reference':s.facility_reference,'stage':s.stage})
	return HttpResponse(json.dumps(ret))

def lab_env_list(request):
	search_val = request.GET.get('search')
	is_lab_completed = request.GET.get('is_lab_completed')
	sample_type = request.GET.get('sample_type')
	is_lab_completed = request.GET.get('is_lab_completed')
	return render(request, 'worksheets/lab_env_list.html', {
		'global_search':search_val,
		'is_lab_completed':is_lab_completed,
		'sample_type':sample_type,
	})

def lab_env_list_json(request):
	r = request.GET
	envelopes = __get_envelopes(r,request)
	envelopes_data = envelopes.get('envelopes_data')

	data = []
	for e in envelopes_data:
		data.append([
			"<a href='/samples/search/?search_val=%s&approvals=1&search_env=1'>%s</a>"%(e.envelope_number,e.envelope_number),
			utils.local_datetime(e.created_at),
			e.s_count,
			"<a id=%s href='#'  class='never_had_result' stage='1'>%s</a>"%(e.pk,e.never_had_result),
			"<a id=%s href='#' class='repeats_pending_wksht' stage='4'>%s</a>"%(e.pk,e.repeats_pending_wksht),	
			"<a id=%s href='#' class='repeats_pending_results' stage='6'>%s</a>"%(e.pk,e.repeats_pending_results),					
			"<a id=%s href='#' class='pending_authorization' stage='2'>%s</a>"%(e.pk,e.pending_authorization),					
			
			])

	return HttpResponse(json.dumps({
			"draw":r.get('draw'),
			"recordsTotal": envelopes.get('recordsTotal'),
			"recordsFiltered":envelopes.get('recordsFiltered'),
			"data":data,
			}))

def __get_envelopes(r,request):
	start = int(r.get('start'))
	length = int(r.get('length'))
	sample_type = request.GET.get('sample_type')
	search = r.get(u'search[value]')
	global_search = r.get(u'global_search[value]')
	if global_search:
		search = global_search
	is_lab_completed = int(request.GET.get('is_lab_completed'))
	
	f_query = Q(sample_medical_lab=utils.user_lab(request), sample_type=sample_type, is_lab_completed=is_lab_completed)
	active_program_code = programs.get_active_program_code(request)
	if active_program_code:
		f_query = f_query & Q(program_code=int(active_program_code))
	if search:
		f_query = f_query & Q(envelope_number__contains=search)

	s_count = models.Count('sample')
	never_had_result = models.Count(models.Case(models.When(Q(sample__stage=1) , then=1)))
	repeats_pending_results = models.Count(models.Case(models.When(Q(sample__stage=6) , then=1)))
	repeats_pending_wksht = models.Count(models.Case(models.When(Q(sample__stage=4) , then=1)))
	pending_authorization = models.Count(models.Case(models.When(Q(sample__stage=2) , then=1)))

	data = Envelope.objects.annotate(s_count=s_count, repeats_pending_results=repeats_pending_results, never_had_result=never_had_result,repeats_pending_wksht=repeats_pending_wksht,pending_authorization=pending_authorization).filter(f_query).order_by('created_at')[start:start+length]

	recordsTotal =  Envelope.objects.count()
	recordsFiltered = recordsTotal if not f_query else Envelope.objects.filter(f_query).count()
	return {'envelopes_data':data, 'recordsTotal':recordsTotal, 'recordsFiltered': recordsFiltered}



@transaction.atomic
def create(request,sample_type):
	if vl_services.is_hiv_program(request):
		if request.method == 'POST':
			worksheet = vl_services.create_worksheet(request.POST, request.user, sample_type)
			return redirect('worksheets:show', worksheet_id=worksheet.id)
		if 'users' not in request.session:
			users = User.objects.filter(is_active=1)
			request.session['users'] = users
		else:
			users = request.session['users']
		search_val = request.GET.get('search')
		is_lab_completed = request.GET.get('is_lab_completed')
		sample_type = request.GET.get('sample_type')
		return render(request, 'worksheets/create.html', {'global_search':search_val,'is_lab_completed':is_lab_completed ,'sample_type':sample_type,'users':users})
	
	if request.method == 'POST':
		db_alias = get_program_db_alias(request)
		generator_id = int(request.POST.get('generated_by_id'))
		worksheet = Worksheet()
		worksheet.sample_type = sample_type
		worksheet.generated_by_id = int(request.POST.get('generated_by_id'))
		worksheet.worksheet_medical_lab = utils.user_lab(request)
		worksheet.worksheet_reference_number =utils.timestamp()
		worksheet.stage = 12 
		worksheet.save()
		
		worksheet.worksheet_reference_number = worksheet_utils.create_worksheet_ref_number(sample_type,worksheet.id)
		worksheet.save()
		envelope_ids = request.POST.getlist('envelope_ids')
		worksheet_samples = []
		for envelope_id in envelope_ids:
			envelope_samples = Sample.objects.using(db_alias).filter(envelope_id =envelope_id,stage=0)
			env = Envelope.objects.using(db_alias).get(pk=envelope_id)
			env.processed_at = dtime.now()
			env.save()

			env_assignment = EnvelopeAssignment()
			env_assignment.the_envelope = env
			env_assignment.assigned_to_id= generator_id
			env_assignment.type = 2
			env_assignment.assigned_by_id = request.user.id
			env_assignment.save()	

			
			worksheet_utils.create_worksheet_envelope(envelope_id,worksheet.id,request.user.id)
		
			for sample in envelope_samples:
				inst_id = sample.barcode
				# if is HIE sample, use facility ref as instrument_id for ws
				if sample.facility_reference is not None and sample.sample_type == 'P':
					inst_id = sample.facility_reference
				ws = WorksheetSample()
				ws.worksheet_id=worksheet.id
				ws.instrument_id=inst_id.strip()
				ws.sample_id = sample.id
				ws.other_instrument_id = sample.barcode
				ws.sample_run=1
				ws.stage=1
				try:
					ws.save()
				except Exception as e:
					return HttpResponse(inst_id)
				#set sample stage to 1
				sample.stage = 1
				sample.save()

			#now save the worksheet samples
		return redirect('worksheets:show', worksheet_id=worksheet.id)
	else:		
		
		#return redirect('worksheets:attach_samples',sample_type='D',stage=1)
		if 'users' not in request.session:
			users = User.objects.filter(is_active=1)
			request.session['users'] = users
		else:
			users = request.session['users']
		s_count = models.Count('sample')
		#not_on_worksheet = models.Count(models.Case(models.When(Q(sample__stage__isnull=Tru) , then=1)))
		#envelopes = Envelope.objects.annotate(s_count=s_count).filter(sample_type =sample_type,is_lab_completed =0,sample__stage__isnull=True,assignment_by_id__isnull=True).order_by('created_at')

		#context = {'sample_type':sample_type,'users':users,'envelopes':envelopes}
		#return render(request, 'worksheets/create.html',context)
		search_val = request.GET.get('search')
		is_lab_completed = request.GET.get('is_lab_completed')
		sample_type = request.GET.get('sample_type')
		is_lab_completed = request.GET.get('is_lab_completed')
		return render(request, 'worksheets/create.html', {'global_search':search_val,'is_lab_completed':is_lab_completed ,'sample_type':sample_type,'is_lab_completed':is_lab_completed,'users':users})

def create_worksheet_list_json(request):
	if vl_services.is_hiv_program(request):
		r = request.GET
		rows = vl_services.worksheet_create_envelope_rows(request.GET.get('sample_type'), request.user, r.get('search[value]') or r.get('global_search[value]') or '')
		data = []
		for e in rows:
			data.append([
				'<input type="checkbox" onclick="addEnvelope(\'%s\',\'%s\')" class="envs" name="env_ids" value="%s">'%(e['id'],e['envelope_number'],e['id']),
				"<a  href='/samples/search/?search_val=%s&approvals=1&search_env=1'>%s</a> (%s)"%(e['envelope_number'],e['envelope_number'],e['s_count']),
				e['program'],
			])
		return HttpResponse(json.dumps({
			"draw":r.get('draw'),
			"recordsTotal": len(rows),
			"recordsFiltered": len(rows),
			"data":data,
		}))
	r = request.GET
	envelopes = __get_worksheet_envelope_samples(r,request)
	envelopes_data = envelopes.get('envelopes_data')

	data = []
	for e in envelopes_data:
		data.append([
			'<input type="checkbox" onclick="addEnvelope(\'%s\',\'%s\')" class="envs" name="env_ids" value="%s">'%(e.pk,e.envelope_number,e.pk),
			"<a  href='/samples/search/?search_val=%s&approvals=1&search_env=1'>%s</a> (%s)"%(e.envelope_number,e.envelope_number,e.s_count),
			e.get_program_code_display(),

			])

	return HttpResponse(json.dumps({
			"draw":r.get('draw'),
			"recordsTotal": envelopes.get('recordsTotal'),
			"recordsFiltered":envelopes.get('recordsFiltered'),
			"data":data,
			}))

def __get_worksheet_envelope_samples(r,request):
	start = int(r.get('start'))
	length = int(r.get('length'))
	sample_type = request.GET.get('sample_type')
	db_alias = get_program_db_alias(request)
	search = r.get(u'search[value]')
	global_search = r.get(u'global_search[value]')
	if global_search:
			search = global_search
	is_lab_completed = 0

	f_query = Q(sample_medical_lab=utils.user_lab(request), sample_type=sample_type, processed_by_id__isnull=True)
	active_program_code = programs.get_active_program_code(request)
	if active_program_code:
		f_query = f_query & Q(program_code=int(active_program_code))
	if search:
		f_query = f_query & Q(envelope_number__contains=search)

	s_count = models.Count(Case(When(Q(sample__locator_category='V') & Q(sample__stage=0), then=1),output_field=IntegerField()))

	data = Envelope.objects.using(db_alias).annotate(s_count=s_count).filter(f_query).exclude(s_count=0).order_by('created_at')[start:start+length]

	recordsTotal =  data.count()
	recordsFiltered = recordsTotal if not f_query else Envelope.objects.using(db_alias).filter(f_query).count()
	return {'envelopes_data':data, 'recordsTotal':recordsTotal, 'recordsFiltered': recordsFiltered}
