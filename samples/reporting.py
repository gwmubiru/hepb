import calendar
import os
import zipfile
from datetime import datetime

import pandas as pd
from dateutil.relativedelta import relativedelta
from django.db import connections

from home import utils


def _month_windows(month_count=5):
	date_today = datetime.now()
	for n in range(month_count):
		target = date_today - relativedelta(months=n)
		start_date = target.replace(day=1)
		end_date = target + relativedelta(day=31)
		yield target.year, target.month, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


def _ensure_dir(path):
	if not os.path.exists(path):
		os.makedirs(path)


def _zip_file(file_path, archive_name):
	with zipfile.ZipFile('%s.zip' % file_path, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
		zf.write(file_path, arcname=archive_name)


HEP_HEADERS = [
	'Form Number',
	'Location ID',
	'Facility',
	'District',
	'Hub',
	'Date collected',
	'Date Received',
	'Sample Type',
	'Patient Name',
	'Hep Number',
	'Other ID',
	'Unique ID',
	'Sex',
	'Date of Birth',
	'Age (years)',
	'Treatment Initiation Date',
	'Current Regimen',
	'Indication for Viral Load Testing',
	'Pregnant',
	'Breast Feeding',
	'Approval Date',
	'Rejection Reason',
	'Result',
	'Test Date',
	'Lab QC date',
	'Data QC date',
	'Data QC date for Rejects',
	'Date dispatched',
	'Date Record Captured',
	'Date of Results Upload',
]


def _hep_query(program_code):
	return """
		SELECT
			s.form_number as `Form Number`,
			CONCAT(s.locator_category, e.envelope_number, s.locator_position) as `Location ID`,
			f.facility as `Facility`,
			d.district as `District`,
			h.hub as `Hub`,
			DATE(s.date_collected) as `Date collected`,
			DATE(s.date_received) as `Date Received`,
			s.sample_type as `Sample Type`,
			p.name as `Patient Name`,
			p.hep_number as `Hep Number`,
			p.other_id as `Other ID`,
			s.patient_unique_id as `Unique ID`,
			p.gender as `Sex`,
			p.dob as `Date of Birth`,
			TIMESTAMPDIFF(YEAR, p.dob, CURDATE()) - (DATE_FORMAT(CURDATE(), '%%m%%d') < DATE_FORMAT(p.dob, '%%m%%d')) as `Age (years)`,
			s.treatment_initiation_date as `Treatment Initiation Date`,
			ba.appendix as `Current Regimen`,
			txt_r.appendix as `Indication for Viral Load Testing`,
			s.pregnant as `Pregnant`,
			s.breast_feeding as `Breast Feeding`,
			v.created_at as `Approval Date`,
			br.appendix as `Rejection Reason`,
			r.result_alphanumeric as `Result`,
			r.test_date as `Test Date`,
			qc.released_at as `Lab QC date`,
			v.created_at as `Data QC date`,
			sr.released_at as `Data QC date for Rejects`,
			rd.dispatch_date as `Date dispatched`,
			s.created_at as `Date Record Captured`,
			r.result_upload_date as `Date of Results Upload`
		FROM vl_samples s
		LEFT JOIN vl_patients p on s.patient_id = p.id
		LEFT JOIN backend_facilities f on f.id = s.facility_id
		LEFT JOIN backend_districts d on d.id = f.district_id
		LEFT JOIN backend_hubs h on h.id = f.hub_id
		LEFT JOIN vl_results r on r.sample_id = s.id
		LEFT JOIN vl_results_qc qc on qc.result_id = r.id
		LEFT JOIN backend_appendices ba on ba.id = s.current_regimen_id
		LEFT JOIN vl_envelopes e on e.id = s.envelope_id
		LEFT JOIN vl_verifications v on v.sample_id = s.id
		LEFT JOIN backend_appendices br on v.rejection_reason_id = br.id
		LEFT JOIN vl_rejected_samples_release sr ON sr.sample_id = s.id
		LEFT JOIN vl_results_dispatch rd on rd.sample_id = s.id
		LEFT JOIN backend_appendices txt_r on txt_r.id = s.treatment_indication_id
		WHERE s.program_code = %s
		AND DATE(s.created_at) BETWEEN %s AND %s
	"""


def generate_program_report(program_code, output_dir):
	_ensure_dir(output_dir)
	for year, month, start_date_str, end_date_str in _month_windows():
		file_name = "%s%s.csv" % (year, format(month, '02'))
		file_path = os.path.join(output_dir, file_name)
		with connections['default'].cursor() as cursor:
			cursor.execute(_hep_query(program_code), [program_code, start_date_str, end_date_str])
			rows = utils.dictfetchall(cursor)
		df = pd.DataFrame(rows, columns=HEP_HEADERS)
		df.to_csv(file_path, index=False, encoding='utf-8')
		_zip_file(file_path, file_name)


VL_HEADERS = [
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


VL_QUERY = """ SELECT s.form_number,s.facility_reference, tc.code as tracking_code,f.facility,d.district,region.region,h.hub,date(s.date_collected) as date_collected,date(date_received) as date_received,date(s.created_at) as date_created, data_entered_at,s.sample_type,s.barcode,s.barcode2,s.barcode3,COALESCE(p.art_number, s.data_art_number, s.reception_art_number) as hep_number,p.other_id,p.unique_id,p.gender as sex,p.dob as date_of_birth,TIMESTAMPDIFF(YEAR, p.dob, qc.released_at) as age, p.treatment_initiation_date, CASE WHEN p.treatment_duration=1 THEN "< 6 months" WHEN p.treatment_duration=2 THEN "6 months -< 1yr" WHEN p.treatment_duration=3 THEN "1 -< 2yrs" WHEN p.treatment_duration=4 THEN "2 -< 5yrs" WHEN p.treatment_duration=5 THEN "5yrs and above" ELSE "Left Blank"
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
	      where date(s.created_at) between %s and %s"""


def generate_vl_report(output_dir):
	_ensure_dir(output_dir)
	for year, month, start_date_str, end_date_str in _month_windows():
		file_name = "%s%s.csv" % (year, format(month, '02'))
		file_path = os.path.join(output_dir, file_name)
		with connections['vl_lims'].cursor() as cursor:
			cursor.execute(VL_QUERY, [start_date_str, end_date_str])
			rows = utils.dictfetchall(cursor)
		df = pd.DataFrame(rows, columns=VL_HEADERS)
		df.to_csv(file_path, index=False, encoding='utf-8')
		_zip_file(file_path, file_name)

