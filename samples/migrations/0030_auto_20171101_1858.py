# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2017-11-01 18:58
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0005_auto_20170614_1646'),
        ('samples', '0029_patient_simple_art_number'),
    ]

    operations = [
        migrations.CreateModel(
            name='DrugResistanceTesting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body_weight', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('patient_on_rifampcin', models.NullBooleanField()),
            ],
            options={
                'db_table': 'vl_drug_resistance_testing',
            },
        ),
        migrations.CreateModel(
            name='PastRegimens',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(blank=True, null=True)),
                ('stop_date', models.DateField(blank=True, null=True)),
                ('dr', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='samples.DrugResistanceTesting')),
                ('regimen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.Appendix')),
            ],
        ),
        migrations.AddField(
            model_name='sample',
            name='treatment_care_approach',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'FBIM'), (2, 'FBG'), (3, 'FTDR'), (4, 'CDDP'), (5, 'CCLAD')], null=True),
        ),
        migrations.AddField(
            model_name='sample',
            name='who_stage',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'I'), (2, 'II'), (3, 'III'), (4, 'IV')], null=True),
        ),
        migrations.AddField(
            model_name='drugresistancetesting',
            name='sample',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='samples.Sample'),
        ),
    ]
