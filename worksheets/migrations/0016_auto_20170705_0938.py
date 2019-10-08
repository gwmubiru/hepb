# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2017-07-05 09:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worksheets', '0015_auto_20170705_0840'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='worksheetsample',
            name='has_result',
        ),
        migrations.AddField(
            model_name='worksheetsample',
            name='stage',
            field=models.PositiveSmallIntegerField(choices=[(1, 'awaiting_results'), (2, 'has_results'), (3, 'passed_lab_qc'), (4, 'passed_data_qc')], default=1),
        ),
        migrations.AlterField(
            model_name='worksheet',
            name='stage',
            field=models.PositiveSmallIntegerField(choices=[(1, 'awaiting_results'), (2, 'has_results'), (3, 'passed_lab_qc'), (4, 'passed_data_qc')], default=1),
        ),
    ]
