# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2017-06-16 12:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('samples', '0017_auto_20170523_2025'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sample',
            name='form_number',
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
