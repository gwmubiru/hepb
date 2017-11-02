from django.contrib.auth.models import User
from rest_framework import serializers
from results.models import Result,ResultsQC
from samples.models import Patient,Envelope,Sample,PatientPhone
from backend.models import District, Hub, Facility
class UserSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ('username',)

class PatientPhoneSerializer(serializers.ModelSerializer):
	class Meta:
		model = PatientPhone
		fields = ('phone',)

class PatientSerializer(serializers.ModelSerializer):
	patientphone = PatientPhoneSerializer(many=True, read_only=True)
	class Meta:
		model = Patient
		fields = ('art_number', 'other_id', 'gender', 'dob', 'patientphone', )

class EnvelopeSerializer(serializers.ModelSerializer):
	class Meta:
		model = Envelope
		fields = ('envelope_number',)

class ResultsQCSerializer(serializers.ModelSerializer):

	class Meta:
		model = ResultsQC
		fields = ('released','released_at',)

class ResultSerializer(serializers.ModelSerializer):
	test_by = UserSerializer(read_only=True)
	resultsqc =  ResultsQCSerializer(read_only=True)

	class Meta:
		model = Result
		fields = ('result_numeric','result_alphanumeric','method', 'test_by', 'test_date','resultsqc',)

class SampleSerializer(serializers.ModelSerializer):
	patient = PatientSerializer(read_only=True)
	envelope = EnvelopeSerializer(read_only=True)
	result = ResultSerializer(read_only=True)

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
			'sample_type',
			'result',)

class DistrictSerializer(serializers.ModelSerializer):

	class Meta:
		model = District
		fields = ('pk','district',)

class HubSerializer(serializers.ModelSerializer):

	class Meta:
		model = Hub
		fields = ('pk','hub',)

class FacilitySerializer(serializers.ModelSerializer):
	
	class Meta:
		model = Facility
		fields = ('pk','district', 'hub','facility', 'coordinator_name', 'coordinator_contact', 'coordinator_email', )