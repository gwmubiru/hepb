# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2017-07-05 08:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worksheets', '0014_worksheetsample_sample_run'),
    ]

    operations = [
        migrations.AlterField(
            model_name='worksheetsample',
            name='sample_run',
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]
