import datetime
import csv, pandas, io, json, math, os as SI
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.db.models import Q, Count

from home import utils
from home import programs
from home import db_aliases
from samples.models import Sample, Verification, Patient, FacilityPatient
from worksheets.models import WorksheetSample
from results.models import Result
from backend.models import DataEntryStats,Facility
from backend.models import SampleApprovalStats
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

# Create your views here.
@login_required
def home(request):	
	return render(request, 'home/index.html')


def _shift_month_start(dt, months_back):
	year = dt.year
	month = dt.month - months_back
	while month <= 0:
		month += 12
		year -= 1
	return datetime.datetime(year, month, 1)


def _next_month_start(dt):
	if dt.month == 12:
		return datetime.datetime(dt.year + 1, 1, 1)
	return datetime.datetime(dt.year, dt.month + 1, 1)


def _month_count(qs, field_name, start, end):
	filters = {
		'%s__gte' % field_name: start,
		'%s__lt' % field_name: end,
	}
	return qs.filter(**filters).count()


def _percent_change(current, previous):
	if not previous:
		return 0 if not current else 100
	return int(round(((current - previous) * 100.0) / previous))


def _program_scoped_queryset(model, request, field_name='program_code'):
	program_code = programs.get_active_program_code(request)
	db_alias = db_aliases.get_program_db_alias(program_code)
	qs = model.objects.using(db_alias).all()
	if program_code:
		qs = qs.filter(**{field_name: int(program_code)})
	return qs


def quick_stats(request):
	today = datetime.datetime.today()
	last_month = utils.last_month()
	month_start = datetime.datetime(today.year, today.month, 1)
	last_month_start = _shift_month_start(month_start, 1)
	two_months_ago_start = _shift_month_start(month_start, 2)
	next_month_start = _next_month_start(month_start)
	ninety_days_ago = today - datetime.timedelta(days=90)

	last_month_filter = Q(created_at__year=last_month.get('year'), created_at__month=last_month.get('month'))
	this_month_filter = Q(created_at__year=today.year, created_at__month=today.month)
	today_filter =  Q(created_at__range=utils.today_range())
	you_filter = Q(created_by_id=request.user.id)

	you_filter2 = Q(verified_by_id=request.user.id)

	program_code = programs.get_active_program_code(request)
	db_alias = db_aliases.get_program_db_alias(program_code)
	sample_qs = _program_scoped_queryset(Sample, request, 'program_code')
	verification_qs = _program_scoped_queryset(Verification, request, 'sample__program_code')
	worksheet_sample_qs = _program_scoped_queryset(WorksheetSample, request, 'sample__program_code').filter(sample__isnull=False)
	result_qs = _program_scoped_queryset(Result, request, 'sample__program_code')

	tested_exactly_two = worksheet_sample_qs.values('sample_id').annotate(total=Count('id')).filter(total=2).count()
	tested_more_than_two = worksheet_sample_qs.values('sample_id').annotate(total=Count('id')).filter(total__gt=2).count()
	samples_pending_testing = sample_qs.filter(stage__in=[0, 1], created_at__lt=ninety_days_ago).count()
	samples_without_results = sample_qs.filter(stage__in=[0, 1, 2, 3, 4, 6]).count()

	tested_current_month = result_qs.filter(
		Q(test_date__gte=month_start, test_date__lt=next_month_start) |
		Q(test_date__isnull=True, created_at__gte=month_start, created_at__lt=next_month_start)
	).count()
	tested_last_month = result_qs.filter(
		Q(test_date__gte=last_month_start, test_date__lt=month_start) |
		Q(test_date__isnull=True, created_at__gte=last_month_start, created_at__lt=month_start)
	).count()
	tested_two_months_ago = result_qs.filter(
		Q(test_date__gte=two_months_ago_start, test_date__lt=last_month_start) |
		Q(test_date__isnull=True, created_at__gte=two_months_ago_start, created_at__lt=last_month_start)
	).count()

	tested_trend = [
		{
			'label': two_months_ago_start.strftime('%b %Y'),
			'count': tested_two_months_ago,
		},
		{
			'label': last_month_start.strftime('%b %Y'),
			'count': tested_last_month,
		},
		{
			'label': month_start.strftime('%b %Y'),
			'count': tested_current_month,
		},
	]
	max_tested_trend = max([row['count'] for row in tested_trend] or [0])
	for row in tested_trend:
		row['width_pct'] = 0 if max_tested_trend == 0 else int(round((row['count'] * 100.0) / max_tested_trend))

	stats = {
		'program': {
			'code': program_code,
			'db_alias': db_alias,
			'label': programs.template_context(request).get('active_program_label', ''),
		},
		'samples_everyone':{
			'all':sample_qs.count(),
			'last_month':sample_qs.filter(last_month_filter).count(),
			'this_month':sample_qs.filter(this_month_filter).count(),
			'today':sample_qs.filter(today_filter).count()
			},
		'samples_you':{
			'all':sample_qs.filter(you_filter).count(),
			'last_month':sample_qs.filter(you_filter&last_month_filter).count(),
			'this_month':sample_qs.filter(you_filter&this_month_filter).count(),
			'today':sample_qs.filter(you_filter&today_filter).count()
			},
		'approvals_everyone':{
			'all':verification_qs.count(),
			'last_month':verification_qs.filter(last_month_filter).count(),
			'this_month':verification_qs.filter(this_month_filter).count(),
			'today':verification_qs.filter(today_filter).count()
			},
		'approvals_you':{
			'all':verification_qs.filter(you_filter2).count(),
			'last_month':verification_qs.filter(you_filter2&last_month_filter).count(),
			'this_month':verification_qs.filter(you_filter2&this_month_filter).count(),
			'today':verification_qs.filter(you_filter2&today_filter).count()
			},
		'operations': {
			'tested_exactly_two': {
				'label': 'Samples tested two times',
				'value': tested_exactly_two,
			},
			'tested_more_than_two': {
				'label': 'Samples tested more than two times',
				'value': tested_more_than_two,
			},
			'pending_testing_90_days': {
				'label': 'Pending testing more than 90 days',
				'value': samples_pending_testing,
			},
			'without_results': {
				'label': 'Samples without results',
				'value': samples_without_results,
			},
			'tested_trend': tested_trend,
			'tested_trend_summary': {
				'current_label': month_start.strftime('%b %Y'),
				'current_value': tested_current_month,
				'previous_label': last_month_start.strftime('%b %Y'),
				'previous_value': tested_last_month,
				'two_months_ago_label': two_months_ago_start.strftime('%b %Y'),
				'two_months_ago_value': tested_two_months_ago,
				'change_vs_previous': tested_current_month - tested_last_month,
				'change_vs_previous_pct': _percent_change(tested_current_month, tested_last_month),
			},
		}
		}
	return HttpResponse(json.dumps(stats))

def data_entry_stats(request):
	stats = DataEntryStats.objects.all()
	if request.GET.get('csv'):
		response = HttpResponse(content_type='text/csv')
		response['Content-Disposition'] = 'attachment; filename="data_entry_stats.csv"'
		writer = csv.writer(response)
		writer.writerow(['User', 'Today', 'Yesterday', 'This Week', 'Last Week', 'This Month', 'Last Month'])
		tab = request.GET.get('tab')
		for s in stats:
			user ="%s %s (%s)" %(s.user.first_name, s.user.last_name, s.user.username)
			if tab=='error_rates':
				writer.writerow([user, s.acc_today, s.acc_yesterday, s.acc_this_week, s.acc_last_week, s.acc_this_month, s.acc_last_month])
			else:
				writer.writerow([user, s.today, s.yesterday, s.this_week, s.last_week, s.this_month, s.last_month])

		return response

	return render(request, 'home/data_entry_stats.html', {'stats':stats})

def sample_approval_stats(request):
	stats = SampleApprovalStats.objects.all()
	if request.GET.get('csv'):
		response = HttpResponse(content_type='text/csv')
		response['Content-Disposition'] = 'attachment; filename="data_entry_stats.csv"'
		writer = csv.writer(response)
		writer.writerow(['User', 'Today', 'Yesterday', 'This Week', 'Last Week', 'This Month', 'Last Month'])
		tab = request.GET.get('tab')
		for s in stats:
			user ="%s %s (%s)" %(s.user.first_name, s.user.last_name, s.user.username)
			if tab=='error_rates':
				writer.writerow([user, s.acc_today, s.acc_yesterday, s.acc_this_week, s.acc_last_week, s.acc_this_month, s.acc_last_month])
			else:
				writer.writerow([user, s.today, s.yesterday, s.this_week, s.last_week, s.this_month, s.last_month])

		return response

	return render(request, 'home/sample_approval_stats.html', {'stats':stats})


def login_page(request):
	return render(request, 'home/login.html')

def login_attempt(request):
	error_message = "incorrect username or password"
	username = request.POST['username']
	password = request.POST['password']
	user = authenticate(username=username, password=password)
	if user is not None:
		if user.is_active:
			login(request, user)
			programs.set_active_program_code(request, '')
			return redirect('/select_program/')
		else:
			return render(request, 'home/login.html', {'error_message': error_message, })
	else:
		return render(request, 'home/login.html', {'error_message': error_message, })
		# Return an 'invalid login' error message.


@login_required
def select_program(request):
	return render(request, 'home/select_program.html', {'next': request.GET.get('next', '/')})


@login_required
def set_program(request):
	next_url = request.POST.get('next') or request.GET.get('next') or '/'
	program_code = programs.normalize_program_code(request.POST.get('program_code') or request.GET.get('program_code'))
	if program_code:
		programs.set_active_program_code(request, program_code)
		return redirect(next_url)
	return render(request, 'home/select_program.html', {
		'error_message': 'Select a program to continue',
		'next': next_url,
	})

def logout(request):
	auth_logout(request)
	next = request.GET.get('next')
	return redirect(next if next else '/')

def clean_data(request):
	facilities = Facility.objects.all()
	#facilities_dropdown = utils.select('facility_id',facilities)
	if request.method == 'POST':
		uploaded_file = request.FILES['clean_data_file']
		tmp_name = "/tmp/%s"%uploaded_file.name
		with open(tmp_name, 'wb+') as destination:
			for chunk in uploaded_file.chunks():
				destination.write(chunk)

		facility_id = request.POST.get('facility_id')
		connections['default'].cursor().execute("DELETE FROM facility_patients WHERE facility_id=%s" %facility_id)
		#connections.close()
		reader = pandas.read_csv(tmp_name, sep=',', escapechar='\\',encoding='ISO-8859-1')
		for row in reader.iterrows():
			index, data = row
			#if index == 1:
			#return HttpResponse(data["DATE OF BIRTH"])
			sanitized_art_no = utils.removeSpecialCharactersFromString(data[2])
			fp = FacilityPatient()

			if isinstance(data["DATE OF BIRTH"], str):
				fp.date_of_birth = datetime.datetime.strptime(data["DATE OF BIRTH"], '%d/%m/%Y')
			fp.unique_id = "%s-A-%s" %(facility_id, sanitized_art_no)
			fp.facility_id = facility_id
			fp.gender = data["SEX"]
			fp.hep_number = data[2] 
			#fp.current_regimen = data["CURRENT REGIMEN"]
			fp.current_regimen = data[7]
			fp.sanitized_hep_number = sanitized_art_no
			if isinstance(data["ART START DATE"], str):
				fp.treatment_initiation_date = datetime.datetime.strptime(data["ART START DATE"], '%d/%m/%Y') 
			fp.save()
		
		return HttpResponse('updated successfully')
			#except Exception as e:
			#logging.getLogger("error_logger").error("Unable to upload file. "+repr(e))
			#messages.error(request,"Unable to upload file. "+repr(e))
			#return HttpResponse(repr(e))
	else:
		return render(request, 'home/clean_data.html',{'facilities':facilities})

def clean_data_list(request):
	if request.method == 'GET':
		facility_id = request.GET['facility_id']
	else:
		facility_id = request.POST['facility_id']
	context = {
		'facility_id':facility_id
	}
	if(facility_id):
		cursor = connections['default'].cursor()
		#get generated matched and unmatched records of facility
		cursor.execute("SELECT * FROM facility_patients WHERE facility_id=%s" %facility_id)
		row = cursor.fetchone()
		#update context
		context = {
			'patients_in_facility_not_in_vl': '',
			'patients_in_vl_not_in_facility':'',
			'matching_patients': '',
			'matched_patient_ids':''
		}
		matching_patients = ''
		if row is not None:
			matched_patients = row[2];

			if matched_patients != '':
				patient_ids = json.loads(matched_patients)
				#return HttpResponse(matched_patients)
				#get patients in VL but not in facility
				sql = """ SELECT  s.patient_unique_id,p.hep_number,s.facility_id,s.patient_id FROM vl_samples s INNER JOIN vl_patients p ON(s.patient_id = p.id) WHERE s.facility_id = %s GROUP BY s.patient_unique_id,p.hep_number,s.facility_id,s.patient_id ORDER BY p.hep_number ASC"""				
				cursor.execute(sql, [facility_id])
				patients = utils.dictfetchall(cursor)
				if len(patients) > 0:
					context['patients_in_vl_not_in_facility'] = patients
				
				#get patients both in VL and in Facility - together with their VLs
				sql = """ SELECT  s.patient_unique_id,s.patient_id,p.hep_number, p.gender, p.dob, s.treatment_initiation_date, ba.appendix, s.facility_id, r.test_date, r.result_numeric, r.result_alphanumeric FROM vl_samples s 
				INNER JOIN vl_patients p ON(s.patient_id = p.parent_id)
				LEFT JOIN vl_results r ON(s.id = r.sample_id)
				LEFT JOIN backend_appendices ba ON(s.current_regimen_id = ba.id and ba.appendix_category_id = 3)	
				WHERE s.patient_id IN  %s AND s.facility_id = %s 
				GROUP BY r.id,s.patient_unique_id,s.patient_id,p.hep_number,s.facility_id, r.test_date, r.result_numeric, r.result_alphanumeric, p.gender, p.dob, s.treatment_initiation_date, s.treatment_line_id,ba.appendix ORDER BY p.hep_number ASC"""				
				
				if len(patient_ids):
					cursor.execute(sql, [patient_ids, facility_id])
					matching_patients = utils.dictfetchall(cursor)
					if len(matching_patients) > 0:
						context['matching_patients'] = matching_patients
			context['patients_in_facility_not_in_vl'] = row[1]
			context['matched_patient_ids'] = patient_ids

	
	#	return HttpResponse(record['facility_patients_not_in_vl'])
	return render(request, 'home/clean_data_list.html',context)
def receive_api(request):
	response = requests.get('http://freegeoip.net/json/')
	geodata = response.json()
	return HttpResponse(geodata['ip'])
def facility_data(request):
	if request.method == 'POST':
		#return 1;
		facility_id = request.POST['facility_id']
		received_clean_data_file = request.FILES["clean_data_file"]
		if not received_clean_data_file.name.endswith('.csv'):
			messages.error(request,'File is not CSV type')
			return HttpResponse('uploada a csv file please');

		file_data = received_clean_data_file.read().decode("utf-8")		

		rows = file_data.split("\n")
		#loop over the rows and save them in db. If error , store as string and then display
		cursor = connections['default'].cursor()
		matching_patients = [] 
		facilty_only_arts = []
		for row in rows:
			#since there is no effective way to know end of file, check for row emptiness
			if row == '':
				break						
			columns = row.split(",")
			#get the facility_id and hep_number and pick then from the DB
			return HttpResponse(columns)
			
			unique_id = "%s-A-%s" %(facility_id, hep_number.replace(' ','').replace('-','').replace('/',''))
			sql = """ SELECT  s.patient_unique_id,p.hep_number,s.facility_id,s.patient_id FROM vl_samples s INNER JOIN vl_patients p ON(s.patient_id = p.id)	WHERE s.facility_id = %s GROUP BY s.patient_unique_id,p.hep_number,s.facility_id,s.patient_id ORDER BY p.hep_number ASC"""				
			cursor.execute(sql, [facility_id])
			patients = utils.dictfetchall(cursor)
			if len(patients) > 0:
				context['patients_in_vl_not_in_facility'] = patients
	else:
		facility_id = request.GET['facility_id']
		return render(request, 'home/facility_data.html')
def get_months():
	return ['01','02','03','04','05','06','07','08','09','10','11','12']

def getSupressionCutOff(sample_type):
    appendix = Appendix.objects.filter(appendix_category_id=9,is_active=1, tag=sample_type).values('id','appendix').first()
    return appendix
