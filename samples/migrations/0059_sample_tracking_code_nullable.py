from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		('samples', '0058_sample_envelope_and_locator_nullable'),
	]

	operations = [
		migrations.AlterField(
			model_name='sample',
			name='tracking_code',
			field=models.ForeignKey(
				blank=True,
				null=True,
				on_delete=django.db.models.deletion.CASCADE,
				to='samples.trackingcode',
			),
		),
	]
