from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from . import programs


class ProgramSelectionMiddleware(MiddlewareMixin):
	EXEMPT_PATH_PREFIXES = (
		'/login/',
		'/login_attempt/',
		'/logout/',
		'/select_program/',
		'/set_program/',
		'/oauth/',
		'/static/',
		'/media/',
		'/admin/',
	)

	def process_request(self, request):
		user = getattr(request, 'user', None)
		is_authenticated = user.is_authenticated() if callable(getattr(user, 'is_authenticated', None)) else getattr(user, 'is_authenticated', False)
		if not is_authenticated:
			return None
		if programs.get_active_program_code(request):
			return None
		if request.path.startswith(self.EXEMPT_PATH_PREFIXES):
			return None
		return redirect('/select_program/?next=%s' % request.get_full_path())
