from django.db import migrations


class Migration(migrations.Migration):

	dependencies = [
		('samples', '0054_envelope_program_code'),
	]

	operations = [
		migrations.RunSQL(
			sql="ALTER TABLE vl_envelopes ENGINE=InnoDB",
			reverse_sql="ALTER TABLE vl_envelopes ENGINE=MyISAM",
		),
	]
