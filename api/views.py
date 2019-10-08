import datetime as dt, json
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from rest_framework import status
# from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.decorators import api_view
from rest_framework.response import Response
# from rest_framework.authentication import SessionAuthentication, BasicAuthentication
# from rest_framework.permissions import IsAuthenticated

from samples.models import Sample
from results.models import ResultsQC, ResultsDispatch
from backend.models import Facility
from api.serializers import ResultsQCSerializer, FacilitySerializer, SampleSerializer

from django.db.models import Q

@api_view(['GET'])
def samples(request):
	if request.method == 'GET':
		pk = request.GET.get('pk')
		some_date = request.GET.get('date')
		date_from = request.GET.get('date_from')
		date_to = request.GET.get('date_to')
		year = request.GET.get('year')
		month = request.GET.get('month')
		changes_today = request.GET.get('changes_today')
		latest_minutes = request.GET.get('latest_minutes')
		updated_date = request.GET.get('updated_date')
		start = request.GET.get('start')
		length = request.GET.get('length')
		if updated_date: 
			start = int(start)
			length = int(length)
			samples = Sample.objects.filter(updated_at__date=updated_date)[start:start+length]
		elif latest_minutes:
			time_to = dt.datetime.today()
			#time_fro = time_to-dt.timedelta(hours=int(latest_hours))
			time_fro = time_to-dt.timedelta(minutes=int(latest_minutes))
			latest_filter = Q(created_at__gte=time_fro, created_at__lte=time_to)|\
							Q(verification__created_at__gte=time_fro, verification__created_at__lte=time_to)|\
							Q(result__test_date__gte=time_fro, result__test_date__lte=time_to)|\
							Q(result__resultsqc__released_at__gte=time_fro, result__resultsqc__released_at__lte=time_to)
			samples = Sample.objects.filter(latest_filter)
		elif changes_today:
			date_today = dt.date.today()
			latest_filter = Q(created_at__=date_today)|\
							Q(verification__created_at__date=date_today)|\
							Q(result__test_date__date=date_today)|\
							Q(result__resultsqc__released_at__date=date_today)
			samples = Sample.objects.filter(latest_filter)
		elif some_date:
			samples = Sample.objects.filter(created_at__date=some_date)
		elif date_from and date_to:
			samples = Sample.objects.filter(created_at__gte=date_from, created_at__lte=date_to)
		elif year and month:
			samples = Sample.objects.filter(created_at__year=year, created_at__month=month)
		elif pk:
			samples = Sample.objects.filter(form_number=pk)
		else:
			#samples = Sample.objects.filter(pk=329760)
			samples = Sample.objects.all().order_by("-pk")[:100]
			
		serializer = SampleSerializer(samples, many=True, read_only=True)
		ret = serializer.data		
		return Response(ret)

@api_view(['GET'])
def results(request):
	if request.method == 'GET':
		results = ResultsQC.objects.all()
		serializer = ResultsQCSerializer(results, many=True, read_only=True)
		return Response(serializer.data)

@api_view(['GET'])
def facilities(request):
	if request.method == 'GET':
		facilities = Facility.objects.all()
		serializer = FacilitySerializer(facilities, many=True, read_only=True)
		return Response(serializer.data)

@api_view(['POST'])
@csrf_exempt
def update_dispatch_details(request):
	if request.method == 'POST':
		#return HttpResponse(request.POST.get('a'))
		samples_str = request.POST.get('samples')
		samples = json.loads(samples_str) if samples_str else []
		for s in samples:
			pk = s.get('pk')
			if pk:
				defaults = {
					"dispatch_type":s.get('dispatch_type'), 
					"dispatch_date":s.get('dispatch_date'),
					"dispatched_by":s.get('dispatched_by'),
					}
				ResultsDispatch.objects.get_or_create(sample_id=int(pk), defaults=defaults)
		return HttpResponse("update complete")



# class ResultsDispatch(models.Model):
# 	sample = models.OneToOneField(samples.Sample, on_delete=models.CASCADE)
# 	dispatch_type = models.CharField(max_length=1, null=True, choices=( ('P', 'Printed'),('D', 'Downloaded') ))
# 	dispatch_date = models.DateTimeField(null=True)
# 	dispatched_by = models.CharField(max_length=128, null=True)
			
