# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2017-06-25 18:47
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0005_auto_20170614_1646'),
        ('samples', '0021_sample_other_regimen'),
    ]

    operations = [
        migrations.CreateModel(
            name='Clinician',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('phone', models.CharField(max_length=128, null=True)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.Facility')),
            ],
            options={
                'db_table': 'vl_clinicians',
            },
        ),
        migrations.CreateModel(
            name='LabTech',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('phone', models.CharField(max_length=128, null=True)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.Facility')),
            ],
            options={
                'db_table': 'vl_lab_techs',
            },
        ),
        migrations.AddField(
            model_name='sample',
            name='clinician',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='samples.Clinician'),
        ),
        migrations.AddField(
            model_name='sample',
            name='lab_tech',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='samples.LabTech'),
        ),
    ]
