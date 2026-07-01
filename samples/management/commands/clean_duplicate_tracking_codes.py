from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from samples.models import Sample, TrackingCode


class Command(BaseCommand):
	help = "Clean duplicate tracking codes before enforcing unique vl_tracking_codes.code."

	def add_arguments(self, parser):
		parser.add_argument(
			'--commit',
			action='store_true',
			help='Apply changes. Without this option the command only reports planned changes.',
		)
		parser.add_argument(
			'--code',
			dest='code',
			help='Limit cleanup to one tracking code.',
		)
		parser.add_argument(
			'--limit',
			type=int,
			help='Limit the number of duplicate code groups processed.',
		)

	def handle(self, *args, **options):
		self.commit = options['commit']
		self.stats = {
			'code_groups': 0,
			'sample_updates': 0,
			'deleted_tracking_codes': 0,
			'renamed_tracking_codes': 0,
		}

		duplicate_codes = self._duplicate_codes(options.get('code'), options.get('limit'))
		if not duplicate_codes:
			self.stdout.write(self.style.SUCCESS('No duplicate tracking codes found.'))
			return

		if self.commit:
			with transaction.atomic():
				self._process_codes(duplicate_codes)
		else:
			self._process_codes(duplicate_codes)
			self.stdout.write(self.style.WARNING('Dry run only. Re-run with --commit to apply changes.'))

		self.stdout.write(
			'Processed {code_groups} code group(s), updated {sample_updates} sample(s), '
			'deleted {deleted_tracking_codes} duplicate tracking code row(s), renamed '
			'{renamed_tracking_codes} tracking code row(s).'.format(**self.stats)
		)

	def _duplicate_codes(self, code=None, limit=None):
		qs = (
			TrackingCode.objects
			.values('code')
			.annotate(row_count=Count('id'))
			.filter(row_count__gt=1)
			.order_by('code')
		)
		if code:
			qs = qs.filter(code=code)
		if limit:
			qs = qs[:limit]
		return [row['code'] for row in qs]

	def _process_codes(self, codes):
		for code in codes:
			self.stats['code_groups'] += 1
			self.stdout.write('')
			self.stdout.write('Tracking code: {0}'.format(code))
			canonical_rows = self._merge_same_facility_duplicates(code)
			self._rename_cross_facility_duplicates(code, canonical_rows)

	def _merge_same_facility_duplicates(self, code):
		canonical_rows = []
		facility_groups = {}
		rows = TrackingCode.objects.filter(code=code).order_by('facility_id', '-created_at', '-id')
		for row in rows:
			facility_groups.setdefault(row.facility_id, []).append(row)

		for facility_id, tracking_codes in sorted(facility_groups.items(), key=lambda item: (item[0] is None, item[0])):
			latest = tracking_codes[0]
			duplicates = tracking_codes[1:]
			canonical_rows.append(latest)
			if not duplicates:
				self.stdout.write(
					'  facility {0}: keep #{1} ({2})'.format(facility_id, latest.id, latest.created_at)
				)
				continue

			duplicate_ids = [tracking_code.id for tracking_code in duplicates]
			sample_count = Sample.objects.filter(tracking_code_id__in=duplicate_ids).count()
			self.stdout.write(
				'  facility {0}: keep #{1} ({2}); move {3} sample(s) from {4}; delete old rows'.format(
					facility_id,
					latest.id,
					latest.created_at,
					sample_count,
					duplicate_ids,
				)
			)
			self.stats['sample_updates'] += sample_count
			self.stats['deleted_tracking_codes'] += len(duplicate_ids)
			if self.commit:
				Sample.objects.filter(tracking_code_id__in=duplicate_ids).update(tracking_code_id=latest.id)
				TrackingCode.objects.filter(id__in=duplicate_ids).delete()

		return canonical_rows

	def _rename_cross_facility_duplicates(self, code, canonical_rows):
		if len(canonical_rows) <= 1:
			return

		rows = sorted(canonical_rows, key=lambda row: (row.created_at, row.id), reverse=True)
		latest = rows[0]
		self.stdout.write(
			'  cross-facility: keep latest #{0} facility {1} as {2}'.format(
				latest.id,
				latest.facility_id,
				code,
			)
		)
		reserved_codes = set()
		for repeat_index, tracking_code in enumerate(rows[1:], start=1):
			new_code = self._next_repeat_code(code, repeat_index, tracking_code.id, reserved_codes)
			reserved_codes.add(new_code)
			self.stdout.write(
				'  cross-facility: rename #{0} facility {1} from {2} to {3}'.format(
					tracking_code.id,
					tracking_code.facility_id,
					code,
					new_code,
				)
			)
			self.stats['renamed_tracking_codes'] += 1
			if self.commit:
				tracking_code.code = new_code
				tracking_code.save(update_fields=['code', 'updated_at'])

	def _next_repeat_code(self, code, repeat_index, current_id, reserved_codes):
		while True:
			candidate = code + ('R' * repeat_index)
			exists = candidate in reserved_codes or TrackingCode.objects.filter(code=candidate).exclude(id=current_id).exists()
			if not exists:
				return candidate
			repeat_index += 1
