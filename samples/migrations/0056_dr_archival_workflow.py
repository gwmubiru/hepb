from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		('samples', '0055_convert_vl_envelopes_to_innodb'),
	]

	operations = [
		migrations.AddField(
			model_name='envelope',
			name='type',
			field=models.PositiveSmallIntegerField(choices=[(1, 'Routine'), (2, 'Drug Resistance')], default=1),
		),
		migrations.CreateModel(
			name='ArchivalEnvelope',
			fields=[
				('box_number', models.CharField(max_length=64, unique=True)),
				('id', models.AutoField(primary_key=True, serialize=False)),
				('sample_type', models.CharField(choices=[('P', 'Plasma'), ('D', 'DBS')], max_length=1)),
				('date_archived', models.DateField()),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('updated_at', models.DateTimeField(auto_now=True)),
			],
			options={
				'db_table': 'vl_archival_envelopes',
			},
		),
		migrations.AlterField(
			model_name='drugresistancerequest',
			name='sample',
			field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='samples.Sample'),
		),
		migrations.AddField(
			model_name='drugresistancerequest',
			name='archival_envelope',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='samples.ArchivalEnvelope'),
		),
		migrations.AddField(
			model_name='drugresistancerequest',
			name='barcode',
			field=models.TextField(blank=True, null=True),
		),
		migrations.AddField(
			model_name='drugresistancerequest',
			name='box_position',
			field=models.CharField(blank=True, max_length=16, null=True),
		),
		migrations.AddField(
			model_name='drugresistancerequest',
			name='decision',
			field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Archived'), (2, 'Destroyed')], null=True),
		),
		migrations.AddField(
			model_name='drugresistancerequest',
			name='hep_number',
			field=models.CharField(blank=True, max_length=64, null=True),
		),
		migrations.AddField(
			model_name='drugresistancerequest',
			name='level_identified_at',
			field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Reception'), (2, 'Lab')], null=True),
		),
	]
