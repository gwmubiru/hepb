from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.contrib.auth.models import User, Group
from home import utils
from backend.models import UserProfile
from django.db import IntegrityError


class Command(BaseCommand):
	help = "Transfer users from old database to the new database"

	# def add_arguments(self, parser):
	# 	pass

	def handle(self, *args, **options):
		self.__get_users()
		self.__save_users()


	def __get_users(self):
		sql = """SELECT email, names, phone, signaturePATH, u.created, group_concat(permission) AS permissions
				 FROM `vl_users` AS u, `vl_users_permissions` AS p WHERE u.id=p.userID group by u.id"""

		cursor = connections['old_db'].cursor()
		cursor.execute(sql)
		self.old_users = utils.dictfetchall(cursor)

	def __save_users(self):
		for old_user in self.old_users:
			email = old_user.get('email', 'guest@guest.com')
			names = old_user.get('names')
			sep_index = names.find(' ')
			first_name = names[0:sep_index] if sep_index!=-1 else names
			last_name = names[sep_index+1:] if sep_index!=-1 else ""

			signature_split = old_user.get('signaturePATH').split('/')
			signature = "signatures/%s" %signature_split.pop() if len(signature_split)>0 else ""

			permissions = old_user.get('permissions')

			try:
				user = User.objects.create_user(
					username=email,
					email=email,
					password=email,
					first_name=first_name, 
					last_name=last_name,
					date_joined=old_user.get('created'),
					is_staff=1,
					is_active=1)
			except IntegrityError:
				user = User.objects.filter(email=email).first()

			usp = UserProfile.objects.filter(user=user)
			user_profile = usp.first() if usp.exists() else UserProfile()
			user_profile.user = user
			user_profile.phone = old_user.get('phone')
			user_profile.signature = signature
			user_profile.medical_lab_id = 1
			user_profile.save()

			self.__save_user_groups(user, permissions)
			print "saved %s" %names

	def __save_user_groups(self, user, permissions):
		# 1 	Data Entry
		# 2 	Approvals
		# 3 	Worksheets management
		# 4 	Results Authorisation
		# 5 	Results Release
		# 6 	Intervention
		# 7		Generate Forms
		# permission, generateForms, intervene,reports,reportsQC,
		# results,samples,unVerifySamples,verifySamples,worksheets
		perm_dict = {1:'samples', 2:'verifySamples', 3:'worksheets', 4:'worksheets', 5:'results', 6:'intervene', 7:'generateForms'}
		for pd, val in perm_dict.iteritems():
			if permissions.find(val) != -1:
				grp = Group.objects.filter(pk=pd).first()
				if grp:
					grp.user_set.add(user)
		

		













