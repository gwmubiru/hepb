# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2016-08-09 11:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('samples', '0007_auto_20160731_1928'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sample',
            name='active_tb_status',
            field=models.CharField(choices=[('Y', 'Yes'), ('N', 'No'), ('L', 'Left Blank')], max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='breast_feeding',
            field=models.CharField(choices=[('Y', 'Yes'), ('N', 'No'), ('L', 'Left Blank')], max_length=1),
        ),
        migrations.AlterField(
            model_name='sample',
            name='pregnant',
            field=models.CharField(choices=[('Y', 'Yes'), ('N', 'No'), ('L', 'Left Blank')], max_length=1),
        ),
        migrations.AlterField(
            model_name='sample',
            name='treatment_inlast_sixmonths',
            field=models.CharField(choices=[('Y', 'Yes'), ('N', 'No'), ('L', 'Left Blank')], max_length=1),
        ),
    ]
