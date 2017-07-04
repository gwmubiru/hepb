from django.contrib.auth.models import User
from rest_framework import serializers
from results.models import Result,ResultsQC
from samples.models import Patient,Envelope,Sample
from backend.models import District, Hub, Facility
class UserSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ('username',)

class PatientSerializer(serializers.ModelSerializer):
	class Meta:
		model = Patient
		fields = ('art_number', 'other_id', 'gender', 'dob',)

class EnvelopeSerializer(serializers.ModelSerializer):
	class Meta:
		model = Envelope
		fields = ('envelope_number',)

class SampleSerializer(serializers.ModelSerializer):
	patient = PatientSerializer(read_only=True)
	envelope = EnvelopeSerializer(read_only=True)

	class Meta:
		model = Sample
		fields = (
			'patient',
			'envelope',
			'locator_category',
			'locator_position',
			'form_number',
			'vl_sample_id',
			'facility',
			'date_collected',
			'sample_type')

class ResultSerializer(serializers.ModelSerializer):
	sample = SampleSerializer(read_only=True)
	test_by = UserSerializer(read_only=True)

	class Meta:
		model = Result
		fields = ('sample','result_numeric','result_alphanumeric','method', 'test_by', 'test_date',)

class ResultsQCSerializer(serializers.ModelSerializer):
	result = ResultSerializer(read_only=True)

	class Meta:
		model = ResultsQC
		fields = ('result',)

class DistrictSerializer(serializers.ModelSerializer):

	class Meta:
		model = District
		fields = ('district',)

class HubSerializer(serializers.ModelSerializer):

	class Meta:
		model = Hub
		fields = ('hub',)

class FacilitySerializer(serializers.ModelSerializer):
	district = DistrictSerializer(read_only=True)
	hub = HubSerializer(read_only=True)

	class Meta:
		model = Facility
		fields = ('pk','district', 'hub','facility', 'coordinator_name', 'coordinator_contact',)