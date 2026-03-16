from samples.models import Envelope

PROGRAM_SESSION_KEY = 'active_program_code'

PROGRAM_THEMES = {
	'1': {
		'nav_bg': '#445dc4',
		'nav_border': '#3b52b0',
		'hover_bg': '#384da6',
		'soft_bg': 'rgba(68, 93, 196, 0.12)',
		'soft_border': 'rgba(68, 93, 196, 0.28)',
		'label': 'HepB',
	},
	'2': {
		'nav_bg': '#64b92a',
		'nav_border': '#59a425',
		'hover_bg': '#529822',
		'soft_bg': 'rgba(100, 185, 42, 0.12)',
		'soft_border': 'rgba(100, 185, 42, 0.28)',
		'label': 'HepC',
	},
}


def normalize_program_code(program_code):
	code = str(program_code or '').strip()
	return code if code in PROGRAM_THEMES else ''


def get_active_program_code(request):
	return normalize_program_code(request.session.get(PROGRAM_SESSION_KEY))


def set_active_program_code(request, program_code):
	code = normalize_program_code(program_code)
	if code:
		request.session[PROGRAM_SESSION_KEY] = code
	elif PROGRAM_SESSION_KEY in request.session:
		del request.session[PROGRAM_SESSION_KEY]
	return code


def filter_queryset_by_program(request, qs, field_name):
	code = get_active_program_code(request)
	if code:
		return qs.filter(**{field_name: int(code)})
	return qs


def template_context(request):
	code = get_active_program_code(request)
	theme = PROGRAM_THEMES.get(code, PROGRAM_THEMES['1'])
	return {
		'program_choices': Envelope.PROGRAM_CODES,
		'active_program_code': code,
		'active_program_label': theme.get('label', ''),
		'active_program_theme': theme,
	}
