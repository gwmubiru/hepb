# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2017-07-03 19:07
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0015_auto_20170604_1939'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ResultsPrinting',
            new_name='ResultsRelease',
        ),
        migrations.AlterModelTable(
            name='resultsrelease',
            table='vl_results_release',
        ),
    ]
