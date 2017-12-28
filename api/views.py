import datetime as dt
from django.shortcuts import render

from rest_framework import status
# from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.decorators import api_view
from rest_framework.response import Response
# from rest_framework.authentication import SessionAuthentication, BasicAuthentication
# from rest_framework.permissions import IsAuthenticated

from samples.models import Sample
from results.models import ResultsQC
from backend.models import Facility
from api.serializers import ResultsQCSerializer, FacilitySerializer, SampleSerializer

from django.db.models import Q

@api_view(['GET'])
def samples(request):
	if request.method == 'GET':
		date_from = request.GET.get('date_from')
		date_to = request.GET.get('date_to')
		year = request.GET.get('year')
		month = request.GET.get('month')
		changes_today = request.GET.get('changes_today')
		if changes_today:
			date_today = dt.date.today()
			latest_filter = Q(created_at__date=date_today)|\
							Q(verification__created_at__date=date_today)|\
							Q(result__created_at__date=date_today)|\
							Q(result__resultsqc__released_at__date=date_today)
			samples = Sample.objects.filter(latest_filter)
		elif date_from and date_to:
			samples = Sample.objects.filter(created_at__gte=date_from, created_at__lte=date_to)
		elif year and month:
			samples = Sample.objects.filter(created_at__year=year, created_at__month=month)
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

