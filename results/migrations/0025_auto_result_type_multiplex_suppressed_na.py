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
			name='result_type',
			field=models.PositiveSmallIntegerField(choices=[(1, 'Quantitative'), (2, 'Qualitative'), (3, 'Multiplex')], default=1),
		),
		migrations.AlterField(
			model_name='result',
			name='suppressed',
			field=models.PositiveSmallIntegerField(choices=[(0, 'N/A'), (1, 'YES'), (2, 'NO'), (3, 'UNKNOWN')], default=3),
		),
		migrations.RunSQL(
			"""
			UPDATE vl_results
			SET result_type = 3
			WHERE result_type = 2
			AND suppressed = 0
			AND COALESCE(result1, '') <> ''
			AND COALESCE(result2, '') <> ''
			AND COALESCE(result3, '') <> ''
			AND COALESCE(result_alphanumeric, '') = COALESCE(result1, '')
			""",
			reverse_sql=migrations.RunSQL.noop,
		),
	]
