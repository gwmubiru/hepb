from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('samples', '0053_merge_20230518_2029'),
	]

	operations = [
		migrations.AddField(
			model_name='envelope',
			name='program_code',
			field=models.PositiveSmallIntegerField(choices=[(1, 'HepB'), (2, 'HepC')], default=0),
		),
	]
