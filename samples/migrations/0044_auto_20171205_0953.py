# -*- coding: utf-8 -*-
# Generated by Django 1.9.dev20150901040355 on 2017-12-05 09:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('samples', '0043_auto_20171203_0917'),
    ]

    operations = [
        migrations.AddField(
            model_name='labtech',
            name='other_name',
            field=models.CharField(max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='treatment_duration',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, '6 months -< 1yr'), (2, '1 -< 2yrs'), (3, '2 -< 5yrs'), (4, '>=5 yrs'), (5, 'Left Blank')], null=True),
        ),
    ]
