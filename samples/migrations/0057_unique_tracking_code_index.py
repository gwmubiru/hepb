from django.db import migrations


UNIQUE_INDEX_NAME = 'uq_vl_tracking_codes_code'
LEGACY_INDEX_NAME = 't_code'
TABLE_NAME = 'vl_tracking_codes'


def _indexes(cursor):
	cursor.execute('SHOW INDEX FROM `{0}`'.format(TABLE_NAME))
	indexes = {}
	for row in cursor.fetchall():
		key_name = row[2]
		indexes.setdefault(key_name, {
			'non_unique': row[1],
			'columns': [],
		})
		indexes[key_name]['columns'].append(row[4])
	return indexes


def add_unique_tracking_code_index(apps, schema_editor):
	cursor = schema_editor.connection.cursor()
	indexes = _indexes(cursor)
	if UNIQUE_INDEX_NAME in indexes:
		return

	for index_name, index in indexes.items():
		if index_name == 'PRIMARY':
			continue
		if index['non_unique'] and index['columns'] == ['code']:
			cursor.execute('DROP INDEX `{0}` ON `{1}`'.format(index_name, TABLE_NAME))

	cursor.execute(
		'ALTER TABLE `{0}` ADD UNIQUE INDEX `{1}` (`code`)'.format(
			TABLE_NAME,
			UNIQUE_INDEX_NAME,
		)
	)


def remove_unique_tracking_code_index(apps, schema_editor):
	cursor = schema_editor.connection.cursor()
	indexes = _indexes(cursor)
	if UNIQUE_INDEX_NAME in indexes:
		cursor.execute('DROP INDEX `{0}` ON `{1}`'.format(UNIQUE_INDEX_NAME, TABLE_NAME))

	indexes = _indexes(cursor)
	if LEGACY_INDEX_NAME not in indexes:
		cursor.execute('CREATE INDEX `{0}` ON `{1}` (`code`)'.format(LEGACY_INDEX_NAME, TABLE_NAME))


class Migration(migrations.Migration):

	dependencies = [
		('samples', '0056_dr_archival_workflow'),
	]

	operations = [
		migrations.RunPython(add_unique_tracking_code_index, remove_unique_tracking_code_index),
	]
