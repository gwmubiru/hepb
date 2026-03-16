from . import programs


def active_program(request):
	return programs.template_context(request)
