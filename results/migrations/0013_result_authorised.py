# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2017-05-30 15:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0012_auto_20170530_1425'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='authorised',
            field=models.BooleanField(default=False),
        ),
    ]
