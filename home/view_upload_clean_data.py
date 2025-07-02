import datetime as dt,json, csv
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.db.models import Q

from home import utils
from samples.models import Sample, Verification, Patient, FacilityPatient
from backend.models import DataEntryStats,Facility
from backend.models import SampleApprovalStats
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

# Create your views here.
@login_required
def home(request):	
	return render(request, 'home/index.html')

def quick_stats(request):
	today = dt.datetime.today()
	last_month = utils.last_month()

	last_month_filter = Q(created_at__year=last_month.get('year'), created_at__month=last_month.get('month'))
	this_month_filter = Q(created_at__year=today.year, created_at__month=today.month)
	today_filter =  Q(created_at__range=utils.today_range())
	you_filter = Q(created_by=request.user)

	you_filter2 = Q(verified_by=request.user)

	stats = {
		'samples_everyone':{
			'all':Sample.objects.all().count(),
			'last_month':Sample.objects.filter(last_month_filter).count(),
			'this_month':Sample.objects.filter(this_month_filter).count(),
			'today':Sample.objects.filter(today_filter).count()
			},
		'samples_you':{
			'all':Sample.objects.filter(you_filter).count(),
			'last_month':Sample.objects.filter(you_filter&last_month_filter).count(),
			'this_month':Sample.objects.filter(you_filter&this_month_filter).count(),
			'today':Sample.objects.filter(you_filter&today_filter).count()
			},
		'approvals_everyone':{
			'all':Verification.objects.all().count(),
			'last_month':Verification.objects.filter(last_month_filter).count(),
			'this_month':Verification.objects.filter(this_month_filter).count(),
			'today':Verification.objects.filter(today_filter).count()
			},
		'approvals_you':{
			'all':Verification.objects.filter(you_filter2).count(),
			'last_month':Verification.objects.filter(you_filter2&last_month_filter).count(),
			'this_month':Verification.objects.filter(you_filter2&this_month_filter).count(),
			'today':Verification.objects.filter(you_filter2&today_filter).count()
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
			return redirect('/')
		else:
			return render(request, 'home/login.html', {'error_message': error_message, })
	else:
		return render(request, 'home/login.html', {'error_message': error_message, })
		# Return an 'invalid login' error message.

def logout(request):
	auth_logout(request)
	next = request.GET.get('next')
	return redirect(next if next else '/')

def clean_data(request):
	facilities = Facility.objects.all()
	#facilities_dropdown = utils.select('facility_id',facilities)
	if request.method == 'POST':
		try:
			received_clean_data_file = request.FILES["clean_data_file"]
			if not received_clean_data_file.name.endswith('.csv'):
				messages.error(request,'File is not CSV type')
				return HttpResponse('uploada a csv file please');
	        #if file is too large, return
			if received_clean_data_file.multiple_chunks():
				messages.error(request,"Uploaded file is too big (%.2f MB)." % (received_clean_data_file.size/(1000*1000),))
				#return HttpResponseRedirect(reverse("myapp:upload_csv"))
				return HttpResponse('file too big');

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
				#get the facility_id and art_number and pick then from the DB
				facility_id = columns[1]
				art_number = columns[2]
				
				unique_id = "%s-A-%s" %(facility_id, art_number.replace(' ','').replace('-','').replace('/',''))
				#return HttpResponse(facility_id + ' and ' + unique_id)
				sql = """ SELECT * FROM vl_patients	WHERE is_the_clean_patient=1 AND facility_id = %s AND unique_id = %s """				
				cursor.execute(sql, [facility_id, unique_id])
				patients = utils.dictfetchall(cursor)
				#return HttpResponse(parent_patient['patient_id'])
				if(len(patients) > 0):
					parent_patient = max(patients)
					for patient in patients:
						matching_patients.append(patient['id'])						
						#connections['default'].cursor().execute("UPDATE vl_samples SET patient_id=%s WHERE id=%s",[parent_patient['patient_id'],sample['id']])
						#connections['default'].cursor().execute("UPDATE vl_patients SET parent_id=%s, facility_id=%s WHERE id=%s",[parent_patient['patient_id'],facility_id,sample['patient_id']])
				else:
					facilty_only_arts.append(art_number)
			#first clean-up in case any uploads were made be4
			connections['default'].cursor().execute("DELETE FROM facility_patients WHERE facility_id=%s" %facility_id)
			connections['default'].cursor().execute("INSERT INTO facility_patients (`facility_patients_not_in_vl`,`facility_patients_matched_in_vl`,facility_id) VALUES(%s, %s,%s)",[json.dumps(facilty_only_arts), json.dumps(matching_patients),facility_id])
			return redirect('/clean_data_list?facility_id=%s' %facility_id)
			return HttpResponse('updated successfully')
		except Exception as e:
			#logging.getLogger("error_logger").error("Unable to upload file. "+repr(e))
			#messages.error(request,"Unable to upload file. "+repr(e))
			return HttpResponse(repr(e))
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
				sql = """ SELECT  s.patient_unique_id,p.art_number,s.facility_id,s.patient_id FROM vl_samples s INNER JOIN vl_patients p ON(s.patient_id = p.id) WHERE s.facility_id = %s GROUP BY s.patient_unique_id,p.art_number,s.facility_id,s.patient_id ORDER BY p.art_number ASC"""				
				cursor.execute(sql, [facility_id])
				patients = utils.dictfetchall(cursor)
				if len(patients) > 0:
					context['patients_in_vl_not_in_facility'] = patients
				
				#get patients both in VL and in Facility - together with their VLs
				sql = """ SELECT  s.patient_unique_id,s.patient_id,p.art_number, p.gender, p.dob, s.treatment_initiation_date, ba.appendix, s.facility_id, r.test_date, r.result_numeric, r.result_alphanumeric FROM vl_samples s 
				INNER JOIN vl_patients p ON(s.patient_id = p.parent_id)
				LEFT JOIN vl_results r ON(s.id = r.sample_id)
				LEFT JOIN backend_appendices ba ON(s.current_regimen_id = ba.id and ba.appendix_category_id = 3)	
				WHERE s.patient_id IN  %s AND s.facility_id = %s 
				GROUP BY r.id,s.patient_unique_id,s.patient_id,p.art_number,s.facility_id, r.test_date, r.result_numeric, r.result_alphanumeric, p.gender, p.dob, s.treatment_initiation_date, s.treatment_line_id,ba.appendix ORDER BY p.art_number ASC"""				
				
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
			#get the facility_id and art_number and pick then from the DB
			return HttpResponse(columns)
			
			unique_id = "%s-A-%s" %(facility_id, art_number.replace(' ','').replace('-','').replace('/',''))
			sql = """ SELECT  s.patient_unique_id,p.art_number,s.facility_id,s.patient_id FROM vl_samples s INNER JOIN vl_patients p ON(s.patient_id = p.id)	WHERE s.facility_id = %s GROUP BY s.patient_unique_id,p.art_number,s.facility_id,s.patient_id ORDER BY p.art_number ASC"""				
			cursor.execute(sql, [facility_id])
			patients = utils.dictfetchall(cursor)
			if len(patients) > 0:
				context['patients_in_vl_not_in_facility'] = patients
	else:
		facility_id = request.GET['facility_id']
		return render(request, 'home/facility_data.html')
