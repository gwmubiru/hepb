import calendar, pandas as pd, zipfile
from datetime import date, datetime, time
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from home import utils
from samples.models import Sample, Patient
from worksheets.models import Worksheet,WorksheetSample
from dateutil import parser
#import logging
from dateutil.relativedelta import relativedelta, MO
from django.db import connections

class Command(BaseCommand):
	help = "Reconcile VL sample IDs to begin from 1 for month"
	#l = logging.getLogger('django.db.backends')
	#l.setLevel(logging.DEBUG)
	#l.addHandler(logging.StreamHandler())
	def handle(self, *args, **options):
		date_today = datetime.now()
		cur_year = date_today.year
		cur_month = date_today.month
		cur_day = date_today.day

		#datetime(2012, 2, 5) + relativedelta(months=+1, seconds=-1)
		for n in range(5):
			#print(n)
			month = cur_month - n
			year = cur_year
			if month == 0:
				month = 12
				year = cur_year - 1

			if month == -1:
				month = 11
				year = cur_year - 1
				
			if month == -2:
				month = 10
				year = cur_year - 1
			
			start_date_str = str(year) + '-' + str(month).zfill(2) + '-01'
			end_date = datetime(year, month, cur_day) + relativedelta(day=31)
			print(end_date)
			end_date_str = end_date.strftime('%Y-%m-%d')

			self.__generate_report(year,month,start_date_str,end_date_str)

	
	
	def __generate_report(self,year, month, start_date_str, end_date_str):
		report_connection = connections['vl_lims']
		file_name = "%s%s.csv"%(year,format(month,'02'))
		file_name2 = "%s%s_DR.csv"%(year,format(month,'02'))
		file_name3 = "%s%s_Detectables.csv"%(year,format(month,'02'))

		file_path = "media/reports/%s"%file_name
		dr_file_path = "media/reports/drug_resistance/%s"%file_name2
		detectable_file_path = "media/reports/detectables/%s"%file_name3

		df = pd.DataFrame([], columns=self.__get_headers())
		df.to_csv(file_path, index=False, header=self.__get_headers(), mode='w')

		dr_df = pd.DataFrame([], columns=self.__get_headers())
		dr_df.to_csv(dr_file_path, index=False, header=self.__get_headers, mode='w')

		dtctbls_df = pd.DataFrame([], columns=self.__get_headers())
		dtctbls_df.to_csv(detectable_file_path, index=False, header=self.__get_headers(), mode='w')
		sql = """ SELECT s.form_number,s.facility_reference, tc.code as tracking_code,f.facility,d.district,region.region,h.hub,date(s.date_collected) as date_collected,date(date_received) as date_received,date(s.created_at) as date_created, data_entered_at,s.sample_type,s.barcode,s.barcode2,s.barcode3,COALESCE(p.art_number, s.data_art_number, s.reception_art_number) as hep_number,p.other_id,p.unique_id,p.gender as sex,p.dob as date_of_birth,TIMESTAMPDIFF(YEAR, p.dob, qc.released_at) as age, p.treatment_initiation_date, CASE WHEN p.treatment_duration=1 THEN "< 6 months" WHEN p.treatment_duration=2 THEN "6 months -< 1yr" WHEN p.treatment_duration=3 THEN "1 -< 2yrs" WHEN p.treatment_duration=4 THEN "2 -< 5yrs" WHEN p.treatment_duration=5 THEN "5yrs and above" ELSE "Left Blank"
		 END as treatment_duration,ba.appendix as current_regimen,s.other_regimen,   txt_r.appendix as indication_for_VL_Testing, fr.appendix as failure_reason, s.pregnant,s.anc_number,s.breast_feeding,s.active_tb_status,    tb_txt_phase.appendix as tb_treatment_phase, arv_adh.appendix as arv_adherence, s.treatment_line_id,  v.accepted as status,date(v.created_at) as approval_date, v.rejection_reason_id,br.appendix as rejection_reason, tl.appendix as treatment_line,  r.result_alphanumeric,r.suppressed,date(r.result_upload_date) as result_upload_date,    date(qc.released_at) as released_at,qc.qc_date,qc.is_reviewed_for_dr,s.current_who_stage, f.dhis2_name,f.dhis2_uid,DATE(r.test_date) as test_date,DATE(sr.released_at) as data_qc_date_for_rejects, DATE(rd.dispatch_date) as date_downloaded, s.consented_sample_keeping as brod_consent, ws.method as test_machine,p.current_regimen_initiation_date as current_regimen_initiation_date,s.current_regimen_initiation_date as s_current_regimen_initiation_date,tc.delivered_at, tc.picked_at as picked_from_facility_on,s.viral_load_testing_id,r.suppressed, r.result_numeric,s.viral_load_testing_id, s.data_entered_by_id,s.hie_data_created_at,bs.appendix as source_system             
		      FROM vl_samples s
		      LEFT JOIN vl_patients p on s.patient_id = p.id              
		      LEFT JOIN vl_tracking_codes tc on s.tracking_code_id = tc.id              
		      LEFT JOIN hepb.backend_appendices tl on s.treatment_line_id = tl.id
		      LEFT JOIN hepb.backend_facilities f on f.id=p.facility_id              
		      LEFT JOIN hepb.backend_districts d on d.id = f.district_id             
		      LEFT JOIN hepb.backend_regions region on region.id = d.region_id              
		      LEFT JOIN hepb.backend_hubs h on h.id = f.hub_id               
		      LEFT JOIN vl_results r on r.sample_id = s.id    
		      LEFT JOIN vl_worksheet_samples ws on ws.id = r.worksheet_sample_id 
		      LEFT JOIN vl_results_qc qc on qc.result_id = r.id              
		      LEFT JOIN hepb.backend_appendices ba on ba.id = s.current_regimen_id              
		      LEFT JOIN vl_envelopes e on e.id = s.envelope_id              
		      LEFT JOIN vl_verifications v on v.sample_id = s.id              
		      LEFT JOIN hepb.backend_appendices br on v.rejection_reason_id = br.id              
		      left join vl_rejected_samples_release as sr ON sr.sample_id = s.id              
		      left join vl_results_dispatch rd on rd.sample_id = s.id 
		      left join hepb.backend_appendices bs on bs.id = s.source_system            
		      left join hepb.backend_appendices txt_r on txt_r.id = s.viral_load_testing_id            
		      left join hepb.backend_appendices fr on fr.id = s.failure_reason_id            
		      left join hepb.backend_appendices tb_txt_phase on tb_txt_phase.id = s.tb_treatment_phase_id            
		      left join hepb.backend_appendices arv_adh on arv_adh.id = s.arv_adherence_id            
		      where date(s.created_at) between '{}' and '{}'""".format(start_date_str,end_date_str)

		with report_connection.cursor() as cursor:
			cursor.execute(sql)
			samples = utils.dictfetchall(cursor)
			cursor.close()

		output = []
		dr_output = []
		dtctbls_output = []

		for s in samples:
		
			sample_arr = [
					s['form_number'],
					s['facility_reference'],
					s['tracking_code'],
					s['facility'],
					s['district'],
					s['region'],
					s['hub'],
					s['date_collected'],
					s['date_received'],
					s['date_created'],
					s['data_entered_at'],
					s['sample_type'],
					s['barcode'],
					s['barcode2'],
					s['barcode3'],
					s['hep_number'],
					s['other_id'],
					s['unique_id'],
					s['sex'],
					s['date_of_birth'],
					s['age'],
					s['treatment_initiation_date'],
					s['treatment_duration'],
					s['current_regimen'],
					s['other_regimen'],
					s['indication_for_VL_Testing'],
					s['failure_reason'],
					s['pregnant'],
					s['anc_number'],
					s['breast_feeding'],
					s['active_tb_status'],
					s['tb_treatment_phase'],
					s['arv_adherence'],
					s['status'],
					s['approval_date'],
					s['rejection_reason_id'],
					s['rejection_reason'],
					s['treatment_line'],
					s['treatment_line_id'],
					s['result_alphanumeric'],
					s['suppressed'],
					s['result_upload_date'],
					s['released_at'],
					s['current_who_stage'],
					s['dhis2_name'],
					s['dhis2_uid'], 
					s['test_date'],
					s['data_qc_date_for_rejects'],
					s['date_downloaded'],
					s['brod_consent'], 
					s['test_machine'],
					s['current_regimen_initiation_date'],
					s['delivered_at'], 
					s['picked_from_facility_on'],
					s['is_reviewed_for_dr'],
					s['data_entered_by_id'],
					s['hie_data_created_at'],
					s['source_system'],

					]
			output.append(sample_arr)
			if s['result_alphanumeric'] is not None:
				vl_testing = (s['viral_load_testing_id']==99 or s['viral_load_testing_id']==94 or s['viral_load_testing_id']==95)
				if (s['treatment_line_id']==90 and s['suppressed']==2 and vl_testing):
					#or dr_requested=='Y'
					dr_output.append(sample_arr)

				if ((s['result_numeric']>=100 and s['sample_type']=='P') or (s['result_numeric']>=840 and s['sample_type']=='D')):
					dtctbls_output.append(sample_arr)
		#connections.close()
		df = pd.DataFrame(output)			
		df.to_csv(file_path, index=False, header=False, mode='a', encoding='utf-8')

		if len(dr_output)>0:
			dr_df = pd.DataFrame(dr_output)
			dr_df.to_csv(dr_file_path, index=False, header=False, mode='a', encoding='utf-8')

		if len(dtctbls_output)>0:
			dtctbls_df = pd.DataFrame(dtctbls_output)
			dtctbls_df.to_csv(detectable_file_path, index=False, header=False, mode='a', encoding='utf-8')

		#print("generated for %s"%date)

		zf = zipfile.ZipFile('%s.zip'%file_path, mode='w', compression=zipfile.ZIP_DEFLATED)
		dr_zf = zipfile.ZipFile('%s.zip'%dr_file_path, mode='w', compression=zipfile.ZIP_DEFLATED)
		dtctbls_zf = zipfile.ZipFile('%s.zip'%detectable_file_path, mode='w', compression=zipfile.ZIP_DEFLATED)
		try:
			zf.write(file_path, arcname=file_name)
			dr_zf.write(dr_file_path, arcname=file_name2)
			dtctbls_zf.write(detectable_file_path, arcname=file_name3)
		finally:
			zf.close()
			dr_zf.close()
			dtctbls_zf.close()


	def __get_hub(self, facility):		
		if hasattr(facility, 'hub'):
			return utils.getattr_ornone(facility.hub, 'hub')
		else:
			return ""

	def __get_district(self, facility):		
		if hasattr(facility, 'district'):
			return utils.getattr_ornone(facility.district, 'district')
		else:
			return ""


	def __get_headers(self):
		return [
				'form_number',
				'facility_reference',
				'tracking_code',
				'facility',
				'district',
				'region',
				'hub',
				'date_collected',
				'date_received',
				'date_created',
				'data_entered_at',
				'sample_type',
				's.barcode',
				's.barcode2',
				's.barcode3',
				'hep_number',
				'other_id',
				'unique_id',
				'sex',
				'date_of_birth',
				'age',
				'treatment_initiation_date',
				'treatment_duration',
				'current_regimen',
				'other_regimen',
				'indication_for_VL_Testing',
				'failure_reason',
				'pregnant',
				'anc_number',
				'breast_feeding',
				'active_tb_status',
				'tb_treatment_phase',
				'arv_adherence',
				'status',
				'approval_date',
				'rejection_reason_id',
				'rejection_reason',
				'treatment_line',
				'treatment_line_id',
				'result_alphanumeric',
				'suppressed',
				'result_upload_date',
				'released_at',
				'current_who_stage',
				'dhis2_name',
				'dhis2_uid', 
				'test_date',
				'data_qc_date_for_rejects',
				'date_downloaded',
				'brod_consent', 
				'test_machine',
				'current_regimen_initiation_date',
				'delivered_at', 
				'picked_from_facility_on',
				'is_reviewed_for_dr',
				'data_entered_by_id',
				'hie_data_created_at',
				'source_system',
				]

	def __get_worksheets_info(self, s):
		worksheets = s.worksheet_set.all()
		ref_numbers = '/'.join([w.worksheet_reference_number for w in worksheets])
		first_added = self.__local_date(worksheets[0].created_at) if len(worksheets) > 0 else ''
		return {'ref_numbers':ref_numbers, 'first_added':first_added}

	def __get_worksheet_barcode(self, s):
		#worksheet_sample = WorksheetSample.objects.get(sample_id=3870075)
		ws = WorksheetSample.objects.filter(sample=s).first()
		if ws:
			return ws.instrument_id
		else:
			return ''

	def __dr_requested(self, s):
		ret = 'N'
		dr = utils.getattr_ornone(s, 'drugresistancerequest')
		if dr:
			ret = 'Y' if (dr.patient_on_rifampicin or dr.body_weight) else 'N'
		return ret


	def __local_date(self, date_val):
		format = "%d-%b-%Y"
		ret = ''
		try:
			if hasattr(date_val, 'strftime'):
				ret = date_val.strftime(format)
			elif date_val:
				#date_obj = dt.datetime.strptime(date_val,"%Y-%m-%d")
				date_obj = parser.parse(date_val)
				ret = date_obj.strftime(format)
			else:
				ret = ""
		except:
			ret = ''

		return ret
