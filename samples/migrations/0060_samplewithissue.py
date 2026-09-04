from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		migrations.swappable_dependency(settings.AUTH_USER_MODEL),
		('backend', '0017_sampleapprovalstats'),
		('samples', '0059_sample_tracking_code_nullable'),
	]

	operations = [
		migrations.CreateModel(
			name='SampleWithIssue',
			fields=[
				('id', models.AutoField(primary_key=True, serialize=False)),
				('source_sheet', models.CharField(blank=True, max_length=64, null=True)),
				('source_row', models.PositiveIntegerField(blank=True, null=True)),
				('reception_date', models.DateField(blank=True, null=True)),
				('pack_number', models.CharField(blank=True, max_length=64, null=True)),
				('barcode', models.CharField(blank=True, max_length=128, null=True)),
				('facility_name', models.CharField(blank=True, max_length=255, null=True)),
				('art_number', models.CharField(blank=True, max_length=128, null=True)),
				('form_number', models.CharField(blank=True, max_length=128, null=True)),
				('sample_type', models.CharField(blank=True, choices=[('P', 'Plasma'), ('D', 'DBS')], max_length=1, null=True)),
				('test_type', models.CharField(blank=True, choices=[('VL', 'VL'), ('EID', 'EID'), ('HEP', 'HEP')], max_length=8, null=True)),
				('collection_date', models.DateField(blank=True, null=True)),
				('infant_name', models.CharField(blank=True, max_length=255, null=True)),
				('batch_number', models.CharField(blank=True, max_length=128, null=True)),
				('exp_number', models.CharField(blank=True, max_length=128, null=True)),
				('contact', models.CharField(blank=True, max_length=128, null=True)),
				('retrieval_status', models.BooleanField(default=False)),
				('retrieval_date', models.DateTimeField(blank=True, null=True)),
				('initials', models.CharField(blank=True, max_length=32, null=True)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('updated_at', models.DateTimeField(auto_now=True)),
				('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='samples_with_issues_created', to=settings.AUTH_USER_MODEL)),
				('facility', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='backend.facility')),
			],
			options={
				'db_table': 'vl_samples_with_issues',
				'unique_together': {('source_sheet', 'source_row')},
			},
		),
		migrations.AddIndex(
			model_name='samplewithissue',
			index=models.Index(fields=['reception_date'], name='swi_reception_date_idx'),
		),
		migrations.AddIndex(
			model_name='samplewithissue',
			index=models.Index(fields=['test_type'], name='swi_test_type_idx'),
		),
		migrations.AddIndex(
			model_name='samplewithissue',
			index=models.Index(fields=['sample_type'], name='swi_sample_type_idx'),
		),
		migrations.AddIndex(
			model_name='samplewithissue',
			index=models.Index(fields=['retrieval_status'], name='swi_retrieval_status_idx'),
		),
	]
