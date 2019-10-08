# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2016-07-27 05:37
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('samples', '0002_auto_20160727_0819'),
    ]

    operations = [
        migrations.AlterField(
            model_name='envelope',
            name='dispatch_date',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='envelope',
            name='envelope_dispatched_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='envelope_dispatched_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='envelope',
            name='envelope_printed_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='envelope_printed_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='envelope',
            name='print_date',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='anc_number',
            field=models.CharField(max_length=64, null=True),
        ),
    ]
