from django.db import models


class VLEnvelope(models.Model):
	id = models.AutoField(primary_key=True)
	envelope_number = models.CharField(max_length=10)
	stage = models.PositiveSmallIntegerField(default=2)
	is_received = models.BooleanField(null=True, blank=True)
	is_data_entered = models.BooleanField(default=False)
	is_lab_completed = models.PositiveSmallIntegerField(default=0)
	has_result = models.BooleanField(null=True, blank=True)
	sample_type = models.CharField(max_length=1)
	sample_medical_lab_id = models.IntegerField(null=True, blank=True)
	accessioner_id = models.IntegerField(null=True, blank=True)
	accessioned_at = models.DateTimeField(null=True, blank=True)
	processed_by_id = models.IntegerField(null=True, blank=True)
	processed_at = models.DateTimeField(null=True, blank=True)
	envelope_range_id = models.IntegerField(null=True, blank=True)
	assignment_by_id = models.IntegerField(null=True, blank=True)
	lab_assignment_by_id = models.IntegerField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_envelopes'
		managed = False


class VLEnvelopeRange(models.Model):
	id = models.AutoField(primary_key=True)
	year_month = models.CharField(max_length=10)
	lower_limit = models.CharField(max_length=10)
	upper_limit = models.CharField(max_length=10)
	sample_type = models.CharField(max_length=1)
	accessioned_by_id = models.IntegerField(null=True, blank=True)
	accessioned_at = models.DateTimeField(null=True, blank=True)
	entered_by_id = models.IntegerField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_envelope_ranges'
		managed = False


class VLEnvelopeAssignment(models.Model):
	id = models.AutoField(primary_key=True)
	the_envelope_id = models.IntegerField()
	assigned_to_id = models.IntegerField()
	assigned_by_id = models.IntegerField()
	type = models.IntegerField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_envelope_assignments'
		managed = False


class VLTrackingCode(models.Model):
	id = models.BigAutoField(primary_key=True)
	code = models.CharField(max_length=100)
	status = models.IntegerField(default=0)
	creation_by_id = models.IntegerField(null=True, blank=True)
	facility_id = models.IntegerField(null=True, blank=True)
	received_by = models.IntegerField(null=True, blank=True)
	no_samples = models.IntegerField(null=True, blank=True)
	delivered_by_name = models.CharField(max_length=250, null=True, blank=True)
	picked_by_name = models.CharField(max_length=250, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	delivered_at = models.DateTimeField(null=True, blank=True)
	received_at = models.DateTimeField(null=True, blank=True)
	picked_at = models.DateTimeField(null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_tracking_codes'
		managed = False


class VLPatient(models.Model):
	id = models.AutoField(primary_key=True)
	unique_id = models.CharField(max_length=128, null=True, blank=True)
	art_number = models.CharField(max_length=64, null=True, blank=True)
	sanitized_art_number = models.CharField(max_length=64, null=True, blank=True)
	other_id = models.CharField(max_length=64, null=True, blank=True)
	gender = models.CharField(max_length=1, null=True, blank=True)
	dob = models.DateField(null=True, blank=True)
	facility_id = models.IntegerField()
	facility_patient_id = models.IntegerField(null=True, blank=True)
	parent_id = models.IntegerField(null=True, blank=True, default=0)
	treatment_initiation_date = models.DateField(null=True, blank=True)
	current_regimen_initiation_date = models.DateField(null=True, blank=True)
	treatment_duration = models.PositiveSmallIntegerField(null=True, blank=True)
	created_by_id = models.IntegerField()
	is_verified = models.BooleanField(default=True)
	is_the_clean_patient = models.PositiveSmallIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_patients'
		managed = False


class VLSample(models.Model):
	id = models.AutoField(primary_key=True)
	patient_id = models.IntegerField(null=True, blank=True)
	patient_unique_id = models.CharField(max_length=128, null=True, blank=True)
	locator_category = models.CharField(max_length=1, null=True, blank=True)
	locator_position = models.CharField(max_length=4, null=True, blank=True)
	barcode = models.CharField(max_length=250, unique=True, null=True, blank=True)
	form_number = models.CharField(max_length=64, null=True, blank=True)
	facility_id = models.IntegerField(null=True, blank=True)
	data_facility_id = models.IntegerField(null=True, blank=True)
	facility_patient_id = models.IntegerField(null=True, blank=True)
	envelope_id = models.IntegerField(null=True, blank=True)
	tracking_code_id = models.IntegerField(null=True, blank=True)
	sample_type = models.CharField(max_length=1, null=True, blank=True)
	date_collected = models.DateField(null=True, blank=True)
	date_received = models.DateTimeField(null=True, blank=True)
	treatment_initiation_date = models.DateField(null=True, blank=True)
	current_regimen_initiation_date = models.DateField(null=True, blank=True)
	treatment_duration = models.PositiveSmallIntegerField(null=True, blank=True)
	current_regimen_id = models.IntegerField(null=True, blank=True)
	other_regimen = models.CharField(max_length=128, null=True, blank=True)
	pregnant = models.CharField(max_length=1, null=True, blank=True)
	anc_number = models.CharField(max_length=64, null=True, blank=True)
	breast_feeding = models.CharField(max_length=1, null=True, blank=True)
	consented_sample_keeping = models.CharField(max_length=1, null=True, blank=True)
	active_tb_status = models.CharField(max_length=1, null=True, blank=True)
	current_who_stage = models.PositiveSmallIntegerField(null=True, blank=True)
	treatment_indication_id = models.IntegerField(null=True, blank=True)
	treatment_indication_other = models.CharField(max_length=64, null=True, blank=True)
	treatment_line_id = models.IntegerField(null=True, blank=True)
	failure_reason_id = models.IntegerField(null=True, blank=True)
	tb_treatment_phase_id = models.IntegerField(null=True, blank=True)
	arv_adherence_id = models.IntegerField(null=True, blank=True)
	treatment_care_approach = models.PositiveSmallIntegerField(null=True, blank=True)
	last_test_date = models.DateField(null=True, blank=True)
	last_value = models.CharField(max_length=64, null=True, blank=True)
	last_sample_type = models.CharField(max_length=1, null=True, blank=True)
	viral_load_testing_id = models.IntegerField(null=True, blank=True)
	created_by_id = models.IntegerField(null=True, blank=True)
	updated_by_id = models.IntegerField(null=True, blank=True)
	data_entered_by_id = models.IntegerField(null=True, blank=True)
	data_entered_at = models.DateTimeField(null=True, blank=True)
	verifier_id = models.IntegerField(null=True, blank=True)
	verified_at = models.DateTimeField(null=True, blank=True)
	received_by_id = models.IntegerField(null=True, blank=True)
	reception_art_number = models.CharField(max_length=40, null=True, blank=True)
	data_art_number = models.CharField(max_length=40, null=True, blank=True)
	stage = models.PositiveSmallIntegerField(null=True, blank=True)
	required_verification = models.BooleanField(default=False)
	verified = models.BooleanField(default=True)
	is_data_entered = models.BooleanField(default=True)
	is_study_sample = models.BooleanField(default=False)
	medical_lab_id = models.IntegerField(null=True, blank=True)
	facility_reference = models.CharField(max_length=128, unique=True, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_samples'
		managed = False


class VLVerification(models.Model):
	id = models.AutoField(primary_key=True)
	sample_id = models.IntegerField(unique=True)
	accepted = models.BooleanField(default=True)
	rejection_reason_id = models.IntegerField(null=True, blank=True)
	comments = models.CharField(max_length=128, null=True, blank=True)
	verified_by_id = models.IntegerField()
	pat_edits = models.PositiveSmallIntegerField(default=0)
	sample_edits = models.PositiveSmallIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_verifications'
		managed = False


class VLWorksheet(models.Model):
	id = models.AutoField(primary_key=True)
	worksheet_reference_number = models.CharField(max_length=128)
	machine_type = models.CharField(max_length=1, null=True, blank=True)
	sample_type = models.CharField(max_length=1, null=True, blank=True)
	assay_date = models.DateTimeField(null=True, blank=True)
	generated_by_id = models.IntegerField()
	eluted_by_id = models.IntegerField(null=True, blank=True)
	loaded_by_id = models.IntegerField(null=True, blank=True)
	worksheet_updated_by_id = models.IntegerField(null=True, blank=True)
	stage = models.PositiveSmallIntegerField()
	is_repeat = models.PositiveSmallIntegerField(default=0)
	worksheet_medical_lab_id = models.IntegerField()
	starting_locator_id = models.CharField(max_length=64, null=True, blank=True)
	ending_locator_id = models.CharField(max_length=64, null=True, blank=True)
	include_calibrators = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_worksheets'
		managed = False


class VLWorksheetSample(models.Model):
	id = models.AutoField(primary_key=True)
	instrument_id = models.CharField(max_length=64, null=True, blank=True)
	other_instrument_id = models.CharField(max_length=64, null=True, blank=True)
	sample_identifier_id = models.IntegerField(null=True, blank=True)
	sample_id = models.IntegerField(null=True, blank=True)
	worksheet_id = models.IntegerField(null=True, blank=True)
	sample_run = models.PositiveSmallIntegerField(null=True, blank=True)
	stage = models.PositiveSmallIntegerField(null=True, blank=True)
	is_diluted = models.BooleanField(default=False)
	sample_type = models.CharField(max_length=1, null=True, blank=True)
	repeat_test = models.PositiveSmallIntegerField(null=True, blank=True)
	suppressed = models.PositiveSmallIntegerField(null=True, blank=True)
	method = models.CharField(max_length=1, null=True, blank=True)
	rack_id = models.CharField(max_length=64, null=True, blank=True)
	result_run_id = models.IntegerField(null=True, blank=True)
	result_run_detail_id = models.IntegerField(null=True, blank=True)
	result_run_position = models.IntegerField(null=True, blank=True)
	tester_id = models.IntegerField(null=True, blank=True)
	result_numeric = models.IntegerField(null=True, blank=True)
	authorised = models.BooleanField(default=False)
	authoriser_id = models.IntegerField(null=True, blank=True)
	authorised_at = models.DateTimeField(null=True, blank=True)
	result_alphanumeric = models.CharField(max_length=100, null=True, blank=True)
	failure_reason = models.CharField(max_length=100, null=True, blank=True)
	test_date = models.DateTimeField(null=True, blank=True)
	supression_cut_off_id = models.IntegerField(null=True, blank=True)
	has_low_level_viramia = models.IntegerField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_worksheet_samples'
		managed = False


class VLResultRun(models.Model):
	id = models.AutoField(primary_key=True)
	reference_number = models.CharField(max_length=128, null=True, blank=True)
	file_name = models.CharField(max_length=100)
	disc_file_name = models.CharField(max_length=100, null=True, blank=True)
	samples_with_more_than_thou_copies = models.IntegerField(default=0)
	has_squential_samples_with_more_than_thou_copies = models.IntegerField(default=0)
	low_positive_ctrl = models.CharField(max_length=50, null=True, blank=True)
	high_positive_ctrl = models.CharField(max_length=50, null=True, blank=True)
	negative_ctrl = models.CharField(max_length=50, null=True, blank=True)
	upload_date = models.DateTimeField(auto_now_add=True)
	stage = models.PositiveSmallIntegerField(default=1)
	run_uploaded_by_id = models.IntegerField()
	reagent_lot = models.CharField(max_length=50, null=True, blank=True)
	reagent_expiry_date = models.DateTimeField(null=True, blank=True)
	serial_number = models.CharField(max_length=50, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_result_runs'
		managed = False


class VLResultRunDetail(models.Model):
	id = models.AutoField(primary_key=True)
	instrument_id = models.CharField(max_length=64)
	flag = models.CharField(max_length=64, null=True, blank=True)
	assay_name = models.CharField(max_length=200, null=True, blank=True)
	status_code = models.CharField(max_length=200, null=True, blank=True)
	status = models.PositiveSmallIntegerField(null=True, blank=True)
	suppressed = models.PositiveSmallIntegerField(null=True, blank=True)
	the_result_run_id = models.IntegerField(null=True, blank=True)
	result_run_position = models.IntegerField(null=True, blank=True)
	testing_by_id = models.IntegerField(null=True, blank=True)
	result_numeric = models.IntegerField(null=True, blank=True)
	result_alphanumeric = models.CharField(max_length=100, null=True, blank=True)
	test_date = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_result_run_details'
		managed = False


class VLResult(models.Model):
	id = models.AutoField(primary_key=True)
	repeat_test = models.PositiveSmallIntegerField()
	result1 = models.TextField()
	result2 = models.TextField(null=True, blank=True)
	result3 = models.TextField(null=True, blank=True)
	result4 = models.TextField(null=True, blank=True)
	result5 = models.TextField(null=True, blank=True)
	result_numeric = models.IntegerField(null=True, blank=True)
	result_alphanumeric = models.TextField()
	failure_reason = models.CharField(max_length=100, null=True, blank=True)
	method = models.CharField(max_length=1, null=True, blank=True)
	test_date = models.DateTimeField(null=True, blank=True)
	authorised_at = models.DateTimeField(null=True, blank=True)
	authorised_by_id = models.IntegerField(null=True, blank=True)
	sample_id = models.IntegerField(unique=True, null=True, blank=True)
	test_by_id = models.IntegerField(null=True, blank=True)
	suppressed = models.PositiveSmallIntegerField()
	authorised = models.BooleanField(default=False)
	result_upload_date = models.DateTimeField(null=True, blank=True)
	worksheet_sample_id = models.IntegerField(null=True, blank=True)
	supression_cut_off_id = models.IntegerField(null=True, blank=True)
	has_low_level_viramia = models.IntegerField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_results'
		managed = False


class VLResultsQC(models.Model):
	id = models.AutoField(primary_key=True)
	released = models.BooleanField(default=False)
	released_at = models.DateTimeField(null=True, blank=True)
	qc_date = models.DateTimeField(null=True, blank=True)
	comments = models.TextField(null=True, blank=True)
	released_by_id = models.IntegerField(null=True, blank=True)
	dr_reviewed_by_id = models.IntegerField(null=True, blank=True)
	is_reviewed_for_dr = models.BooleanField(default=False)
	dr_reviewed_at = models.DateTimeField(null=True, blank=True)
	result_id = models.IntegerField(unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = 'vl'
		db_table = 'vl_results_qc'
		managed = False
