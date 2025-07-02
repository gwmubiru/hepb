from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import ClinicalRequestFormsDispatch, ClinicalRequestForm
from django.db import IntegrityError


class Command(BaseCommand):
	help = "Transfer forms from old database to the new database"

	def add_arguments(self, parser):
		parser.add_argument('period', nargs='+')

	def handle(self, *args, **options):
		self.create_year = options['period'][0]
		self.create_month = options['period'][1]
		self.old_forms = []	
		for x in xrange(0,20):
			self.__save_forms()

	def __get_forms(self):
		sql = """SELECT f.id AS fid, f.formNumber, d.id AS did, d.refNumber, d.facilityID,
						dispatchDate, f.created, f.createdby
				FROM vl_forms_clinicalrequest AS f
				LEFT JOIN vl_forms_clinicalrequest_dispatch AS d ON f.refNumber=d.refNumber
				WHERE YEAR(f.created)=%s AND MONTH(f.created)=%s AND migrated = 'NO' LIMIT 6000"""

		cursor = connections['old_db'].cursor()
		cursor.execute(sql, [self.create_year, self.create_month])
		self.old_forms = utils.dictfetchall(cursor)

	def __save_forms(self):
		self.__get_forms()
		for form in self.old_forms:
			#print "%s %s" %(facility_id, form.get('formNumber'))
			user = utils.get_or_create_user(form.get('createdby'))
			did = form.get('did')
			fid = form.get('fid')
			dispatch_date = form.get('dispatchDate') or form.get('created')
			try:
				if(did!=None):
					d = ClinicalRequestFormsDispatch.objects
					dispatch, d_created = d.get_or_create(
							id=did,
							defaults={'dispatched_by_id':user.id,
									  'facility_id':form.get('facilityID'),
									  'ref_number':form.get('refNumber'),
									   'created_at': form.get('created'),
									  'dispatched_at': dispatch_date,}
							
						)

				f_objs = ClinicalRequestForm.objects;
				f, f_created = f_objs.get_or_create(
							form_number=form.get('formNumber'), defaults={'dispatch_id':did})
				connections['old_db'].cursor().execute("UPDATE vl_forms_clinicalrequest SET migrated='YES' WHERE id=%s"%fid)
				print "saved %s" %f.id
			except:
				print "Failed %s" %fid