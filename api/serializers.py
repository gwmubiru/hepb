from django.contrib.auth.models import User
from rest_framework import serializers
from results.models import Result, ResultsQC, ResultsDispatch
from samples.models import Patient, Envelope, Sample, PatientPhone, RejectedSamplesRelease, Verification
from backend.models import Appendix, District, Hub, Facility, UserProfile

class AppendixSerializer(serializers.ModelSerializer):
	class Meta:
		model = Appendix
		fields = ('code', 'appendix','tag',)


class UserProfileSerializer(serializers.ModelSerializer):
	class Meta:
		model = UserProfile
		fields = ('signature',)

class UserSerializer(serializers.ModelSerializer):
	userprofile = UserProfileSerializer(read_only=True)
	class Meta:
		model = User
		fields = ('username','userprofile',)

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

class FacilityMinSerializer(serializers.ModelSerializer):
	district = DistrictSerializer(read_only=True)
	hub = HubSerializer(read_only=True)
	
	class Meta:
		model = Facility
		fields = ('pk','district', 'hub','facility',)

class PatientPhoneSerializer(serializers.ModelSerializer):
	class Meta:
		model = PatientPhone
		fields = ('phone',)

class PatientSerializer(serializers.ModelSerializer):
	patientphone_set = PatientPhoneSerializer(many=True, read_only=True)
	class Meta:
		model = Patient
		fields = ('art_number', 'other_id', 'gender', 'dob', 'patientphone_set', )

class EnvelopeSerializer(serializers.ModelSerializer):
	class Meta:
		model = Envelope
		fields = ('envelope_number',)

class ResultsQCSerializer(serializers.ModelSerializer):

	class Meta:
		model = ResultsQC
		fields = ('released','released_at', )

class ResultSerializer(serializers.ModelSerializer):
	test_by = UserSerializer(read_only=True)
	resultsqc =  ResultsQCSerializer(read_only=True)

	class Meta:
		model = Result
		fields = ('result_numeric','result_alphanumeric','get_suppressed_display','method', 'test_by', 'test_date','resultsqc',)

class ResultsDispatchSerializer(serializers.ModelSerializer):
	
	class Meta:
		model = ResultsDispatch
		fields = ('dispatch_type','dispatch_date','dispatched_by',)

class RejectedSamplesReleaseSerializer(serializers.ModelSerializer):
	class Meta:
		model = RejectedSamplesRelease
		fields = ('released','released_at',)

class VerificationSerializer(serializers.ModelSerializer):
	rejection_reason = AppendixSerializer(read_only=True)
	class Meta:
		model = Verification
		fields = ('accepted','rejection_reason')

class SampleSerializer(serializers.ModelSerializer):
	patient = PatientSerializer(read_only=True)
	envelope = EnvelopeSerializer(read_only=True)
	verification =  VerificationSerializer(read_only=True)
	result = ResultSerializer(read_only=True)
	resultsdispatch = ResultsDispatchSerializer(read_only=True)
	rejectedsamplesrelease = RejectedSamplesReleaseSerializer(read_only=True)
	facility = FacilityMinSerializer(read_only=True)
	current_regimen = AppendixSerializer(read_only=True)
	treatment_line = AppendixSerializer(read_only=True)
	treatment_indication = AppendixSerializer(read_only=True)

	class Meta:
		model = Sample
		fields = (
			'pk',
			'patient',
			'patient_unique_id',
			'envelope',
			'locator_category',
			'locator_position',
			'form_number',
			'vl_sample_id',
			'facility',
			'current_regimen',
			'other_regimen',
			'treatment_line',
			'treatment_initiation_date',
			'treatment_indication',
			'get_pregnant_display',
			'anc_number',
			'get_breast_feeding_display',
			'get_active_tb_status_display',
			'date_collected',
			'date_received',
			'sample_type',
			'verification',
			'result',
			'rejectedsamplesrelease',
			'resultsdispatch',
			'created_at',
			)