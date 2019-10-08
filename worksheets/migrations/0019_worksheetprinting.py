# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2018-02-05 16:44
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('worksheets', '0018_worksheetsample_rack_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorksheetPrinting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('printed_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('worksheet', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='worksheets.Worksheet')),
                ('worksheet_printed_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='worksheet_printed_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'vl_worksheet_printing',
            },
        ),
    ]
