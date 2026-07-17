# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('results', '0023_auto_20190620_1903'),
	]

	operations = [
		migrations.AddField(
			model_name='result',
			name='result_type',
			field=models.PositiveSmallIntegerField(choices=[(1, 'Quantitative'), (2, 'Qualitative')], default=1),
		),
	]
