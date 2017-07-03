from django.shortcuts import render

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from results.models import ResultsQC
from api.serializers import ResultsQCSerializer


@api_view(['GET'])
def results(request):
	if request.method == 'GET':
		results = ResultsQC.objects.all()
		serializer = ResultsQCSerializer(results, many=True, read_only=True)
		return Response(serializer.data)

