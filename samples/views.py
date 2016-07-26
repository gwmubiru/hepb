from django.shortcuts import render
#from django.views.generic import TemplateView

from backend.models import Appendix,Facility
from home import utils

# Create your views here.

def create(request):
	facilities = Facility.objects.values('id', 'facility').order_by('facility')
	

	# utils.select(name="", data={}, selected_val="", more={})
	
	context = {
		"facility_dropdown": utils.select("facility_id",{'k_col':'id', 'v_col':'facility', 'items':facilities }),
		"regimens_dropdown": appendix_select("current_regimen_id", 3),
		"tx_indication_dropdown": appendix_select("treatment_indication_id", 6),
		"f_reason_dropdown": appendix_select("failure_reason_id", 2),
		"vl_testing_dropdown": appendix_select("viral_load_testing_id", 8),
		"tb_tx_phase_dropdown": appendix_select("tb_treatment_phase_id", 5),
		"adherence_dropdown": appendix_select("arv_adherence_id", 1),

	}
	return render(request, 'samples/create.html', context)

def appendix_select(name="",cat_id=0):
	apendices = Appendix.objects.values('id','appendix');
	return utils.select(name,{'k_col':'id', 'v_col':'appendix', 'items':apendices.filter(appendix_category_id=cat_id)},)

def save(request):
	pass