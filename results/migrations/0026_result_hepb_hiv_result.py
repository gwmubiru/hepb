# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('results', '0025_auto_result_type_multiplex_suppressed_na'),
	]

	operations = [
		migrations.AddField(
			model_name='result',
			name='hepb_result',
			field=models.CharField(blank=True, max_length=50, null=True),
		),
		migrations.AddField(
			model_name='result',
			name='hiv_result',
			field=models.CharField(blank=True, max_length=50, null=True),
		),
		migrations.RunSQL(
			"""
			UPDATE vl_results
			SET hepb_result = result2,
			    hiv_result = result3
			WHERE result_type = 2
			AND suppressed = 0
			AND COALESCE(result1, '') <> ''
			AND COALESCE(result2, '') <> ''
			AND COALESCE(result3, '') <> ''
			AND COALESCE(result_alphanumeric, '') = COALESCE(result1, '')
			AND COALESCE(hepb_result, '') = ''
			AND COALESCE(hiv_result, '') = ''
			""",
			reverse_sql=migrations.RunSQL.noop,
		),
	]
