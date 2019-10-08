# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2016-09-06 09:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('samples', '0012_auto_20160906_0020'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patient',
            name='dob',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='patient',
            name='other_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='patientphone',
            name='phone',
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='active_tb_status',
            field=models.CharField(blank=True, choices=[('Y', 'Yes'), ('N', 'No'), ('L', 'Left Blank')], max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='anc_number',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='arv_adherence',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='arv_adherence', to='backend.Appendix'),
        ),
        migrations.AlterField(
            model_name='sample',
            name='date_collected',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='failure_reason',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='failure_reason', to='backend.Appendix'),
        ),
        migrations.AlterField(
            model_name='sample',
            name='repeat_testing_last_sample_type',
            field=models.CharField(blank=True, choices=[('P', 'Plasma'), ('D', 'DBS')], max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='repeat_testing_last_test_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='repeat_testing_last_value',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='routine_monitoring_last_sample_type',
            field=models.CharField(blank=True, choices=[('P', 'Plasma'), ('D', 'DBS')], max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='routine_monitoring_last_test_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='routine_monitoring_last_value',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='suspected_treatment_failure_last_sample_type',
            field=models.CharField(blank=True, choices=[('P', 'Plasma'), ('D', 'DBS')], max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='suspected_treatment_failure_last_test_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='suspected_treatment_failure_last_value',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='tb_treatment_phase',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tb_treatment_phase', to='backend.Appendix'),
        ),
        migrations.AlterField(
            model_name='sample',
            name='treatment_indication',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='treatment_indication', to='backend.Appendix'),
        ),
        migrations.AlterField(
            model_name='sample',
            name='treatment_indication_other',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='treatment_initiation_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='verification',
            name='comments',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='verification',
            name='rejection_reason',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='backend.Appendix'),
        ),
    ]
