from __future__ import unicode_literals

import csv
import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction


class Command(BaseCommand):
	help = "Backfill missing samples and related result records from a source DB into a destination DB using form_number matching."

	SAMPLE_TABLE = 'vl_samples'
	PATIENT_TABLE = 'vl_patients'
	ENVELOPE_TABLE = 'vl_envelopes'
	ENVELOPE_RANGE_TABLE = 'vl_envelope_ranges'
	TRACKING_CODE_TABLE = 'vl_tracking_codes'
	SAMPLE_RECEPTION_TABLE = 'vl_sample_reception'
	VERIFICATION_TABLE = 'vl_verifications'
	RESULT_TABLE = 'vl_results'
	RESULT_QC_TABLE = 'vl_results_qc'
	RESULT_DISPATCH_TABLE = 'vl_results_dispatch'
	WORKSHEET_SAMPLE_TABLE = 'vl_worksheet_samples'
	USER_TABLE = 'auth_user'
	APPENDIX_TABLE = 'backend_appendices'
	FACILITY_TABLE = 'backend_facilities'
	MEDICAL_LAB_TABLE = 'backend_medical_labs'

	def add_arguments(self, parser):
		parser.add_argument('--since', required=True, help='Cutoff datetime/date, e.g. 2026-03-15 or 2026-03-15 00:00:00')
		parser.add_argument('--source', default='old_db', help='Source DB alias. Default: old_db')
		parser.add_argument('--dest', default='default', help='Destination DB alias. Default: default')
		parser.add_argument('--limit', type=int, default=0, help='Optional maximum number of source samples to inspect')
		parser.add_argument('--fallback-user-id', type=int, default=1, help='Destination user ID to use when a source user cannot be matched. Default: 1')
		parser.add_argument('--show-skipped', action='store_true', help='Print skipped form numbers grouped by reason at the end')
		parser.add_argument('--csv-dir', default='tmp/backfill_reports', help='Directory for skipped/changed CSV reports. Default: tmp/backfill_reports')
		parser.add_argument('--dry-run', action='store_true', help='Report actions without writing to destination')

	def handle(self, *args, **options):
		self.source_alias = options['source']
		self.dest_alias = options['dest']
		self.dry_run = options['dry_run']
		self.since = self._parse_since(options['since'])
		self.fallback_user_id = options['fallback_user_id']
		self.show_skipped = options['show_skipped']
		self.csv_dir = options['csv_dir']
		self.user_map = {}
		self.appendix_map = {}
		self.skipped_samples = {
			'missing_dependencies': [],
			'unchanged': [],
		}
		self.changed_samples = []
		self.counts = {
			'samples_scanned': 0,
			'samples_created': 0,
			'dest_sample_missing': 0,
			'samples_unchanged': 0,
			'verifications_created': 0,
			'results_created': 0,
			'results_qc_created': 0,
			'results_dispatch_created': 0,
			'skipped_existing': 0,
			'errors': 0,
		}

		self._validate_alias(self.source_alias)
		self._validate_alias(self.dest_alias)

		source_samples = self._get_source_samples(limit=options['limit'])
		self.stdout.write('Found %d source samples updated on/after %s' % (len(source_samples), self.since))

		for source_sample in source_samples:
			self.counts['samples_scanned'] += 1
			try:
				self._process_sample(source_sample)
			except Exception as exc:
				self.counts['errors'] += 1
				self.stderr.write('Failed source sample id=%s form_number=%s: %s' % (
					source_sample.get('id'),
					source_sample.get('form_number'),
					exc,
				))

		self.stdout.write(self._summary())
		self._write_csv_reports()
		if self.show_skipped:
			self.stdout.write(self._skipped_summary())

	def _validate_alias(self, alias):
		if alias not in connections.databases:
			raise CommandError('Database alias not configured: %s' % alias)

	def _parse_since(self, raw):
		for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
			try:
				return datetime.strptime(raw, fmt)
			except ValueError:
				pass
		raise CommandError('Invalid --since value: %s' % raw)

	def _get_source_samples(self, limit=0):
		sql = "SELECT `id`, `form_number`, `updated_at` FROM %s WHERE `updated_at` >= %%s AND `form_number` IS NOT NULL AND `form_number` != '' ORDER BY `updated_at` ASC, `id` ASC" % self._qi(self.SAMPLE_TABLE)
		params = [self.since]
		if limit:
			sql += " LIMIT %s"
			params.append(limit)
		with connections[self.source_alias].cursor() as cursor:
			cursor.execute(sql, params)
			return self._dictfetchall(cursor)

	def _process_sample(self, source_sample_ref):
		form_number = source_sample_ref.get('form_number')
		source_sample_id = source_sample_ref.get('id')
		sample_changed = False
		dest_sample = self._fetch_one(self.SAMPLE_TABLE, 'form_number', form_number, self.dest_alias)
		if not dest_sample:
			dest_sample = self._create_dest_sample(source_sample_id, form_number)
			if not dest_sample:
				self.counts['dest_sample_missing'] += 1
				self.skipped_samples['missing_dependencies'].append(form_number)
				return
			sample_changed = True

		dest_sample_id = dest_sample['id']
		verification_created = self._sync_verification(source_sample_id, dest_sample_id)
		dest_result, result_created = self._sync_result(source_sample_id, dest_sample_id)
		dispatch_created = self._sync_dispatch(source_sample_id, dest_sample_id)
		if dest_result:
			qc_created = self._sync_result_qc(source_sample_id, dest_result['id'])
		else:
			qc_created = False

		if sample_changed or verification_created or result_created or dispatch_created or qc_created:
			self.changed_samples.append({
				'form_number': form_number,
				'sample_created': self._as_flag(sample_changed),
				'verification_created': self._as_flag(verification_created),
				'result_created': self._as_flag(result_created),
				'result_qc_created': self._as_flag(qc_created),
				'result_dispatch_created': self._as_flag(dispatch_created),
			})
			return

		self.counts['samples_unchanged'] += 1
		self.skipped_samples['unchanged'].append(form_number)

	def _create_dest_sample(self, source_sample_id, form_number):
		source_row = self._fetch_one(self.SAMPLE_TABLE, 'id', source_sample_id, self.source_alias)
		if not source_row:
			return None

		payload = dict(source_row)
		payload.pop('id', None)
		payload['patient_id'] = self._ensure_patient(source_row.get('patient_id'))
		payload['envelope_id'] = self._ensure_envelope(source_row.get('envelope_id'))
		payload['tracking_code_id'] = self._ensure_tracking_code(source_row.get('tracking_code_id'))
		payload['sample_reception_id'] = self._ensure_sample_reception(source_row.get('sample_reception_id'))
		payload['facility_id'] = self._map_facility_id(source_row.get('facility_id'))
		payload['data_facility_id'] = self._map_facility_id(source_row.get('data_facility_id'))
		payload['facility_patient_id'] = None
		payload['current_regimen_id'] = self._map_appendix_id(source_row.get('current_regimen_id'))
		payload['source_system_id'] = self._map_appendix_id(source_row.get('source_system_id'))
		payload['viral_load_testing_id'] = self._map_appendix_id(source_row.get('viral_load_testing_id'))
		payload['treatment_indication_id'] = self._map_appendix_id(source_row.get('treatment_indication_id'))
		payload['treatment_line_id'] = self._map_appendix_id(source_row.get('treatment_line_id'))
		payload['failure_reason_id'] = self._map_appendix_id(source_row.get('failure_reason_id'))
		payload['tb_treatment_phase_id'] = self._map_appendix_id(source_row.get('tb_treatment_phase_id'))
		payload['arv_adherence_id'] = self._map_appendix_id(source_row.get('arv_adherence_id'))
		payload['created_by_id'] = self._required_user_id(source_row.get('created_by_id'))
		payload['updated_by_id'] = self._required_user_id(source_row.get('updated_by_id'))
		payload['verifier_id'] = self._required_user_id(source_row.get('verifier_id'))
		payload['data_entered_by_id'] = self._required_user_id(source_row.get('data_entered_by_id'))
		payload['received_by_id'] = self._required_user_id(source_row.get('received_by_id'))

		if not payload.get('facility_id') or not payload.get('envelope_id') or not payload.get('tracking_code_id'):
			return None

		self._insert_row(self.SAMPLE_TABLE, payload)
		dest_sample = self._fetch_one(self.SAMPLE_TABLE, 'form_number', form_number, self.dest_alias)
		if dest_sample:
			self.counts['samples_created'] += 1
		return dest_sample

	def _sync_verification(self, source_sample_id, dest_sample_id):
		source_row = self._fetch_one(self.VERIFICATION_TABLE, 'sample_id', source_sample_id, self.source_alias)
		if not source_row:
			return False
		if self._exists(self.VERIFICATION_TABLE, 'sample_id', dest_sample_id, self.dest_alias):
			self.counts['skipped_existing'] += 1
			return False
		payload = dict(source_row)
		payload.pop('id', None)
		payload['sample_id'] = dest_sample_id
		payload['verified_by_id'] = self._required_user_id(source_row.get('verified_by_id'))
		payload['rejection_reason_id'] = self._map_appendix_id(source_row.get('rejection_reason_id'))
		self._insert_row(self.VERIFICATION_TABLE, payload)
		self.counts['verifications_created'] += 1
		return True

	def _sync_result(self, source_sample_id, dest_sample_id):
		source_row = self._fetch_one(self.RESULT_TABLE, 'sample_id', source_sample_id, self.source_alias)
		if not source_row:
			return self._fetch_one(self.RESULT_TABLE, 'sample_id', dest_sample_id, self.dest_alias), False

		existing = self._fetch_one(self.RESULT_TABLE, 'sample_id', dest_sample_id, self.dest_alias)
		if existing:
			self.counts['skipped_existing'] += 1
			return existing, False

		payload = dict(source_row)
		payload.pop('id', None)
		payload['sample_id'] = dest_sample_id
		dest_ws = self._get_dest_worksheet_sample(dest_sample_id)
		payload['worksheet_sample_id'] = dest_ws['id'] if dest_ws else None
		payload['test_by_id'] = self._required_user_id(source_row.get('test_by_id'))
		payload['authorised_by_id'] = self._required_user_id(source_row.get('authorised_by_id'))
		payload['supression_cut_off_id'] = self._map_appendix_id(source_row.get('supression_cut_off_id'))
		self._insert_row(self.RESULT_TABLE, payload)
		self.counts['results_created'] += 1
		return self._fetch_one(self.RESULT_TABLE, 'sample_id', dest_sample_id, self.dest_alias), True

	def _sync_result_qc(self, source_sample_id, dest_result_id):
		source_result = self._fetch_one(self.RESULT_TABLE, 'sample_id', source_sample_id, self.source_alias)
		if not source_result:
			return False
		source_row = self._fetch_one(self.RESULT_QC_TABLE, 'result_id', source_result['id'], self.source_alias)
		if not source_row:
			return False
		if self._exists(self.RESULT_QC_TABLE, 'result_id', dest_result_id, self.dest_alias):
			self.counts['skipped_existing'] += 1
			return False
		payload = dict(source_row)
		payload.pop('id', None)
		payload['result_id'] = dest_result_id
		payload['released_by_id'] = self._required_user_id(source_row.get('released_by_id'))
		payload['dr_reviewed_by_id'] = self._required_user_id(source_row.get('dr_reviewed_by_id'))
		self._insert_row(self.RESULT_QC_TABLE, payload)
		self.counts['results_qc_created'] += 1
		return True

	def _sync_dispatch(self, source_sample_id, dest_sample_id):
		source_row = self._fetch_one(self.RESULT_DISPATCH_TABLE, 'sample_id', source_sample_id, self.source_alias)
		if not source_row:
			return False
		if self._exists(self.RESULT_DISPATCH_TABLE, 'sample_id', dest_sample_id, self.dest_alias):
			self.counts['skipped_existing'] += 1
			return False
		payload = dict(source_row)
		payload.pop('id', None)
		payload['sample_id'] = dest_sample_id
		self._insert_row(self.RESULT_DISPATCH_TABLE, payload)
		self.counts['results_dispatch_created'] += 1
		return True

	def _ensure_patient(self, source_patient_id):
		if source_patient_id in (None, '', 0, '0'):
			return None
		source_row = self._fetch_one(self.PATIENT_TABLE, 'id', source_patient_id, self.source_alias)
		if not source_row:
			return None

		dest_row = None
		if source_row.get('unique_id'):
			dest_row = self._fetch_one(self.PATIENT_TABLE, 'unique_id', source_row.get('unique_id'), self.dest_alias)
		if not dest_row and source_row.get('hep_number') and source_row.get('facility_id'):
			facility_id = self._map_facility_id(source_row.get('facility_id'))
			if facility_id:
				sql = "SELECT * FROM %s WHERE `hep_number` = %%s AND `facility_id` = %%s ORDER BY `id` DESC LIMIT 1" % self._qi(self.PATIENT_TABLE)
				with connections[self.dest_alias].cursor() as cursor:
					cursor.execute(sql, [source_row.get('hep_number'), facility_id])
					rows = self._dictfetchall(cursor)
					dest_row = rows[0] if rows else None
		if dest_row:
			return dest_row['id']

		payload = dict(source_row)
		payload.pop('id', None)
		payload['facility_id'] = self._map_facility_id(source_row.get('facility_id'))
		payload['created_by_id'] = self._required_user_id(source_row.get('created_by_id'))
		self._insert_row(self.PATIENT_TABLE, payload)
		if source_row.get('unique_id'):
			dest_row = self._fetch_one(self.PATIENT_TABLE, 'unique_id', source_row.get('unique_id'), self.dest_alias)
		return dest_row['id'] if dest_row else None

	def _ensure_envelope(self, source_envelope_id):
		if source_envelope_id in (None, '', 0, '0'):
			return None
		source_row = self._fetch_one(self.ENVELOPE_TABLE, 'id', source_envelope_id, self.source_alias)
		if not source_row:
			return None
		dest_row = self._fetch_one(self.ENVELOPE_TABLE, 'envelope_number', source_row.get('envelope_number'), self.dest_alias)
		if dest_row:
			return dest_row['id']

		payload = dict(source_row)
		payload.pop('id', None)
		payload['sample_medical_lab_id'] = self._map_medical_lab_id(source_row.get('sample_medical_lab_id'))
		payload['accessioner_id'] = self._required_user_id(source_row.get('accessioner_id'))
		payload['processed_by_id'] = self._required_user_id(source_row.get('processed_by_id'))
		payload['assignment_by_id'] = self._required_user_id(source_row.get('assignment_by_id'))
		payload['lab_assignment_by_id'] = self._required_user_id(source_row.get('lab_assignment_by_id'))
		payload['envelope_range_id'] = self._ensure_envelope_range(source_row.get('envelope_range_id'))
		self._insert_row(self.ENVELOPE_TABLE, payload)
		dest_row = self._fetch_one(self.ENVELOPE_TABLE, 'envelope_number', source_row.get('envelope_number'), self.dest_alias)
		return dest_row['id'] if dest_row else None

	def _ensure_envelope_range(self, source_range_id):
		if source_range_id in (None, '', 0, '0'):
			return None
		source_row = self._fetch_one(self.ENVELOPE_RANGE_TABLE, 'id', source_range_id, self.source_alias)
		if not source_row:
			return None

		sql = "SELECT * FROM %s WHERE `year_month` = %%s AND `lower_limit` = %%s AND `upper_limit` = %%s LIMIT 1" % self._qi(self.ENVELOPE_RANGE_TABLE)
		with connections[self.dest_alias].cursor() as cursor:
			cursor.execute(sql, [source_row.get('year_month'), source_row.get('lower_limit'), source_row.get('upper_limit')])
			rows = self._dictfetchall(cursor)
			if rows:
				return rows[0]['id']

		payload = dict(source_row)
		payload.pop('id', None)
		payload['accessioned_by_id'] = self._required_user_id(source_row.get('accessioned_by_id'))
		payload['entered_by_id'] = self._required_user_id(source_row.get('entered_by_id'))
		self._insert_row(self.ENVELOPE_RANGE_TABLE, payload)

		with connections[self.dest_alias].cursor() as cursor:
			cursor.execute(sql, [source_row.get('year_month'), source_row.get('lower_limit'), source_row.get('upper_limit')])
			rows = self._dictfetchall(cursor)
			return rows[0]['id'] if rows else None

	def _ensure_tracking_code(self, source_tracking_code_id):
		if source_tracking_code_id in (None, '', 0, '0'):
			return None
		source_row = self._fetch_one(self.TRACKING_CODE_TABLE, 'id', source_tracking_code_id, self.source_alias)
		if not source_row:
			return None
		dest_row = self._fetch_one(self.TRACKING_CODE_TABLE, 'code', source_row.get('code'), self.dest_alias)
		if dest_row:
			return dest_row['id']

		payload = dict(source_row)
		payload.pop('id', None)
		payload['facility_id'] = self._map_facility_id(source_row.get('facility_id'))
		payload['creation_by_id'] = self._required_user_id(source_row.get('creation_by_id'))
		if not payload.get('facility_id'):
			return None
		self._insert_row(self.TRACKING_CODE_TABLE, payload)
		dest_row = self._fetch_one(self.TRACKING_CODE_TABLE, 'code', source_row.get('code'), self.dest_alias)
		return dest_row['id'] if dest_row else None

	def _ensure_sample_reception(self, source_sample_reception_id):
		if source_sample_reception_id in (None, '', 0, '0'):
			return None
		source_row = self._fetch_one(self.SAMPLE_RECEPTION_TABLE, 'id', source_sample_reception_id, self.source_alias)
		if not source_row:
			return None
		dest_row = self._fetch_one(self.SAMPLE_RECEPTION_TABLE, 'barcode', source_row.get('barcode'), self.dest_alias)
		if dest_row:
			return dest_row['id']

		payload = dict(source_row)
		payload.pop('id', None)
		payload['facility_id'] = self._map_facility_id(source_row.get('facility_id'))
		payload['creator_id'] = self._required_user_id(source_row.get('creator_id'))
		if not payload.get('facility_id'):
			return None
		self._insert_row(self.SAMPLE_RECEPTION_TABLE, payload)
		dest_row = self._fetch_one(self.SAMPLE_RECEPTION_TABLE, 'barcode', source_row.get('barcode'), self.dest_alias)
		return dest_row['id'] if dest_row else None

	def _get_dest_worksheet_sample(self, dest_sample_id):
		sql = "SELECT * FROM %s WHERE `sample_id` = %%s ORDER BY `id` DESC LIMIT 1" % self._qi(self.WORKSHEET_SAMPLE_TABLE)
		with connections[self.dest_alias].cursor() as cursor:
			cursor.execute(sql, [dest_sample_id])
			rows = self._dictfetchall(cursor)
			return rows[0] if rows else None

	def _map_user_id(self, source_user_id):
		if source_user_id in (None, '', 0, '0'):
			return None
		if source_user_id in self.user_map:
			return self.user_map[source_user_id]

		source_user = self._fetch_one(self.USER_TABLE, 'id', source_user_id, self.source_alias)
		if not source_user:
			self.user_map[source_user_id] = None
			return None

		dest_user = None
		if source_user.get('username'):
			dest_user = self._fetch_one(self.USER_TABLE, 'username', source_user.get('username'), self.dest_alias)
		if not dest_user and source_user.get('email'):
			dest_user = self._fetch_one(self.USER_TABLE, 'email', source_user.get('email'), self.dest_alias)

		self.user_map[source_user_id] = dest_user.get('id') if dest_user else None
		return self.user_map[source_user_id]

	def _required_user_id(self, source_user_id):
		dest_user_id = self._map_user_id(source_user_id)
		return dest_user_id or self.fallback_user_id

	def _map_appendix_id(self, source_appendix_id):
		if source_appendix_id in (None, '', 0, '0'):
			return None
		if source_appendix_id in self.appendix_map:
			return self.appendix_map[source_appendix_id]

		source_appendix = self._fetch_one(self.APPENDIX_TABLE, 'id', source_appendix_id, self.source_alias)
		if not source_appendix:
			self.appendix_map[source_appendix_id] = None
			return None

		sql = "SELECT `id` FROM %s WHERE `appendix_category_id` = %%s AND ((`code` = %%s) OR (`appendix` = %%s)) ORDER BY `id` ASC LIMIT 1" % self._qi(self.APPENDIX_TABLE)
		with connections[self.dest_alias].cursor() as cursor:
			cursor.execute(sql, [
				source_appendix.get('appendix_category_id'),
				source_appendix.get('code'),
				source_appendix.get('appendix'),
			])
			row = cursor.fetchone()
			self.appendix_map[source_appendix_id] = row[0] if row else None
			return self.appendix_map[source_appendix_id]

	def _map_facility_id(self, source_facility_id):
		if source_facility_id in (None, '', 0, '0'):
			return None
		source_row = self._fetch_one(self.FACILITY_TABLE, 'id', source_facility_id, self.source_alias)
		if not source_row:
			return None
		dest_row = self._fetch_one(self.FACILITY_TABLE, 'facility', source_row.get('facility'), self.dest_alias)
		return dest_row.get('id') if dest_row else None

	def _map_medical_lab_id(self, source_medical_lab_id):
		if source_medical_lab_id in (None, '', 0, '0'):
			return None
		source_row = self._fetch_one(self.MEDICAL_LAB_TABLE, 'id', source_medical_lab_id, self.source_alias)
		if not source_row:
			return None
		dest_row = self._fetch_one(self.MEDICAL_LAB_TABLE, 'lab_name', source_row.get('lab_name'), self.dest_alias)
		return dest_row.get('id') if dest_row else None

	def _exists(self, table, key_col, key_val, alias):
		if key_val in (None, ''):
			return False
		sql = "SELECT 1 FROM %s WHERE %s = %%s LIMIT 1" % (self._qi(table), self._qi(key_col))
		with connections[alias].cursor() as cursor:
			cursor.execute(sql, [key_val])
			return cursor.fetchone() is not None

	def _fetch_one(self, table, key_col, key_val, alias):
		if key_val in (None, ''):
			return None
		sql = "SELECT * FROM %s WHERE %s = %%s LIMIT 1" % (self._qi(table), self._qi(key_col))
		with connections[alias].cursor() as cursor:
			cursor.execute(sql, [key_val])
			rows = self._dictfetchall(cursor)
			return rows[0] if rows else None

	def _insert_row(self, table, row):
		columns = sorted([col for col in row.keys() if col != 'id'])
		sql = "INSERT INTO %s (%s) VALUES (%s)" % (
			self._qi(table),
			', '.join([self._qi(column) for column in columns]),
			', '.join(['%s'] * len(columns)),
		)
		values = [row[col] for col in columns]
		if self.dry_run:
			self.stdout.write('DRY RUN insert into %s' % table)
			return
		with transaction.atomic(using=self.dest_alias):
			with connections[self.dest_alias].cursor() as cursor:
				cursor.execute(sql, values)

	def _dictfetchall(self, cursor):
		columns = [col[0] for col in cursor.description]
		return [dict(zip(columns, row)) for row in cursor.fetchall()]

	def _qi(self, identifier):
		return '`%s`' % identifier.replace('`', '``')

	def _summary(self):
		parts = ['Backfill complete']
		for key in sorted(self.counts.keys()):
			parts.append('%s=%s' % (key, self.counts[key]))
		return ', '.join(parts)

	def _skipped_summary(self):
		parts = []
		for reason in sorted(self.skipped_samples.keys()):
			form_numbers = self.skipped_samples[reason]
			parts.append('%s (%s): %s' % (
				reason,
				len(form_numbers),
				', '.join([str(form_number) for form_number in form_numbers]) if form_numbers else 'none',
			))
		return '\n'.join(parts)

	def _write_csv_reports(self):
		if not os.path.isabs(self.csv_dir):
			self.csv_dir = os.path.join(os.getcwd(), self.csv_dir)
		if not os.path.isdir(self.csv_dir):
			os.makedirs(self.csv_dir)

		safe_since = self.since.strftime('%Y%m%d_%H%M%S')
		skipped_path = os.path.join(self.csv_dir, 'backfill_skipped_%s.csv' % safe_since)
		changed_path = os.path.join(self.csv_dir, 'backfill_changed_%s.csv' % safe_since)

		with open(skipped_path, 'w') as handle:
			writer = csv.writer(handle)
			writer.writerow(['form_number', 'reason'])
			for reason in sorted(self.skipped_samples.keys()):
				for form_number in self.skipped_samples[reason]:
					writer.writerow([form_number, reason])

		with open(changed_path, 'w') as handle:
			writer = csv.writer(handle)
			writer.writerow([
				'form_number',
				'sample_created',
				'verification_created',
				'result_created',
				'result_qc_created',
				'result_dispatch_created',
			])
			for row in self.changed_samples:
				writer.writerow([
					row['form_number'],
					row['sample_created'],
					row['verification_created'],
					row['result_created'],
					row['result_qc_created'],
					row['result_dispatch_created'],
				])

		self.stdout.write('Skipped CSV: %s' % skipped_path)
		self.stdout.write('Changed CSV: %s' % changed_path)

	def _as_flag(self, value):
		return 'Y' if value else 'N'
