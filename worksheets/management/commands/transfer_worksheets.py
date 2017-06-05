from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from worksheets.models import Worksheet, WorksheetSample

class Command(BaseCommand):	
	help = "Transfer lab worksheets data from old database to the new database"
	sample_types = {1:'D', 2:'P', 3:'P'}
	machine_types = {'abbott': 'A', 'roche': 'R'}
	def add_arguments(self, parser):
		parser.add_argument('period', nargs='+')

	def handle(self, *args, **options):
		self.create_year = options['period'][0]
		self.create_month = options['period'][1]
		self.old_samples = []		
		self.__get_samples()
		self.__save_samples()

	def __get_samples(self):
		sql = """SELECT sw.*, sw.id AS swid, sw.created AS swcreated, sw.createdby AS swcreatedby,
				w.*, w.id AS wid, w.created AS wcreated, w.createdby AS wcreatedby
				FROM vl_samples_worksheet AS sw
				LEFT JOIN vl_samples_worksheetcredentials AS w ON sw.worksheetID=w.id
				WHERE YEAR(sw.created)=%s AND MONTH(sw.created)=%s"""

		cursor = connections['old_db'].cursor()
		cursor.execute(sql, [self.create_year, self.create_month])
		self.old_samples = utils.dictfetchall(cursor)

	def __save_samples(self):

		for r in self.old_samples:
			self.__save_worksheet(r)
			self.__save_sample(r)
			print "saved xxxxx"

			

	def __save_worksheet(self, r):
		user = utils.get_or_create_user(r.get('wcreatedby'))
		w, w_created = Worksheet.objects.get_or_create(
				id=r.get('wid'),
				worksheet_reference_number=r.get('worksheetReferenceNumber'),
				machine_type=self.machine_types.get(r.get('machineType')),
				sample_type=self.sample_types.get(r.get('worksheetType')),
				sample_prep=r.get('samplePrep'),
				sample_prep_expiry_date=r.get('samplePrepExpiryDate'),
				bulk_lysis_buffer=r.get('bulkLysisBuffer'),
				bulk_lysis_buffer_expiry_date=r.get('bulkLysisBufferExpiryDate'),
				control=r.get('control'),
				control_expiry_date=r.get('controlExpiryDate'),
				calibrator=r.get('calibrator'),
				calibrator_expiry_date=r.get('calibratorExpiryDate'),
				include_calibrators=r.get('includeCalibrators'),
				amplication_kit=r.get('amplicationKit'),
				amplication_kit_expiry_date=r.get('amplicationKitExpiryDate'),
				assay_date=r.get('assayDate'),
				generated_by=user.id,
				created_at=r.get('wcreated'),
			)

	def __save_sample(self, r):
		user = utils.get_or_create_user(r.get('swcreatedby'))
		s = WorksheetSample()
		s.id = r.get('swid')
		s.worksheet_id = r.get('wid')
		s.attached_by_id = user.id
		s.created_at = r.get('swcreated')
		s.save()			