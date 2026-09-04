from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		('samples', '0057_unique_tracking_code_index'),
	]

	operations = [
		migrations.AlterField(
			model_name='sample',
			name='envelope',
			field=models.ForeignKey(
				blank=True,
				null=True,
				on_delete=django.db.models.deletion.CASCADE,
				to='samples.envelope',
			),
		),
		migrations.AlterField(
			model_name='sample',
			name='locator_position',
			field=models.CharField(blank=True, max_length=4, null=True),
		),
		migrations.AlterField(
			model_name='sample',
			name='stage',
			field=models.PositiveSmallIntegerField(
				blank=True,
				choices=[
					(1, 'Created'),
					(2, 'Pending_result_auth'),
					(3, 'panding_result_release'),
					(4, 'completed'),
					(20, 'Pending sample collection'),
					(25, 'Pending packaging'),
					(30, 'Pending pickup'),
					(40, 'In transit'),
				],
				null=True,
			),
		),
	]
