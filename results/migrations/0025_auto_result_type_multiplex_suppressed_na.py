# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('results', '0024_result_result_type'),
	]

	operations = [
		migrations.AlterField(
			model_name='result',
			name='suppressed',
			field=models.PositiveSmallIntegerField(choices=[(0, 'N/A'), (1, 'YES'), (2, 'NO'), (3, 'UNKNOWN')], default=3),
		),
	]
