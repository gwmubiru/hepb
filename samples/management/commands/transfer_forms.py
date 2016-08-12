from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import ClinicalRequestFormsDispatch, ClinicalRequestForm


class Command(BaseCommand):
	help = "Transfer forms from old database to the new database"

	def handle(self, *args, **options):
		self.old_forms = []		
		self.__get_forms()
		self.__save_forms()

	def __get_forms(self):
		sql = """SELECT f.id AS fid, f.formNumber, d.id AS did, d.refNumber, d.facilityID,
						dispatchDate, f.created, f.createdby
				FROM vl_forms_clinicalrequest AS f
				LEFT JOIN vl_forms_clinicalrequest_dispatch AS d ON f.refNumber=d.refNumber
				LIMIT 10000 """

		cursor = connections['old_db'].cursor()
		cursor.execute(sql)
		self.old_forms = utils.dictfetchall(cursor)

	def __save_forms(self):
		for form in self.old_forms:
			#print "%s %s" %(facility_id, form.get('formNumber'))
			user = utils.get_or_create_user(r.get('createdby'))

			did = form.get('did')

			if(did!=None):
				d = ClinicalRequestFormsDispatch.objects
				dispatch, d_created = d.get_or_create(
						id=did,
						dispatched_by_id=user.id,
						facility_id=form.get('facilityID'),
						ref_number=form.get('refNumber'),
						defaults={'created_at': form.get('created'),
								  'dispatched_at': form.get('dispatchDate'),}
						
					)

			f_objs = ClinicalRequestForm.objects;
			f, f_created = f_objs.get_or_create(
						form_number=form.get('formNumber'), 
						dispatch_id=did)
			print "saved %s" %f.id