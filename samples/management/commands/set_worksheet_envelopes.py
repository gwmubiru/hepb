import datetime as dt
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Envelope
from worksheets.models import Worksheet,WorksheetEnvelope

class Command(BaseCommand):
	help = "set envelopes for worksheet"


	def handle(self, *args, **options):
		self.__set_envelope()

	def __set_envelope(self):
		envelopes = Envelope.objects.raw('select envelope_number, e.id, e.id as env_id,worksheet_id from vl_worksheet_samples ws INNER JOIN vl_samples s ON s.id = ws.sample_id INNER JOIN vl_envelopes e ON e.id = s.envelope_id GROUP BY worksheet_id, e.id')
		for envelope in envelopes:
			worksheet, created = WorksheetEnvelope.objects.update_or_create(
				envelope_id = envelope.env_id,
				worksheet_id = envelope.worksheet_id,
				the_creator_id = 1,
				defaults={'envelope_id': envelope.env_id,'worksheet_id':envelope.worksheet_id}
			)
		print('kiwedde')


#490 - has no art number for id 175390
#1647 - invalid dob for 175539