import datetime as dt,json
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.db.models import Q

from home import utils
from samples.models import Sample, Verification
from backend.models import Appendix, Facility

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