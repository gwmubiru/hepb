from django.db import connections


HEPC_DB_ALIAS = 'hepc'
HEPB_DB_ALIAS = 'hepb'
VL_DB_ALIAS = 'vl_lims'


def configured(alias):
	return alias in connections.databases


def get_hepb_db_alias():
	if configured(HEPC_DB_ALIAS):
		return HEPC_DB_ALIAS
	if configured(HEPB_DB_ALIAS):
		return HEPB_DB_ALIAS
	return 'default'


def get_vl_db_alias():
	if configured(VL_DB_ALIAS):
		return VL_DB_ALIAS
	return 'default'


def get_program_db_alias(program_code):
	if str(program_code or '') == '3':
		return get_vl_db_alias()
	return get_hepb_db_alias()
