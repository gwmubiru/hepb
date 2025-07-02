from django.db import transaction
from .models import Patient, Sample, PastRegimens, DrugResistanceRequest
from .forms import PatientForm, SampleForm, DrugResistanceRequestForm
from home import utils
from datetime import *
from . import utils as sample_utils

class SampleService:
    @staticmethod
    def create_patient(patient_form, pst, user):
        patient = patient_form.save(commit=False)
        sanitized_art_number = utils.removeSpecialCharactersFromString(pst.get('art_number'))
        patient.unique_id = f"{pst.get('facility')}-A-{sanitized_art_number}"
        patient.parent_id = patient.id
        patient.created_by = user
        patient.facility_id = pst.get('facility')
        patient.treatment_duration = pst.get('treatment_duration')
        patient.sanitized_art_number = sanitized_art_number
        patient.facility_patient_id = pst.get('patient_id')
        patient.gender = pst.get('gender')
        patient.save()
        return patient

    @staticmethod
    def update_sample(sample_form, pst, patient, user):
        sample_id = sample_form.cleaned_data.get('id')
        if sample_id:
            # Fetch the existing sample
            sample = Sample.objects.filter(pk=sample_id).first()
            if sample:
                original_facility_id = sample.facility_id
                # Update the sample using the form's save method
                sample = sample_form.save(commit=False)
                if pst.get('gender') == 'M':
                    sample.pregnant = None
                    sample.anc_number = None
                    sample.breast_feeding = None

                #if pst.get('page_type') == '1' or pst.get('page_type') == 1:
                if pst.get('page_type') == '1' or sample.data_entered_by is None or (sample.data_entered_by == user):
                    sample.data_facility_id = pst.get('facility')
                    sample.data_art_number = pst.get('data_art_number')
                    sample.is_data_entered = 1
                    sample.data_entered_by = user
                    sample.data_entered_at = datetime.now()
                    needs_verification = sample_utils.is_rec_and_entery_data_mataching(sample,pst.get('art_number'),pst.get('facility'))
                    sample.required_verification = needs_verification
                    if needs_verification == 1:
                        sample.verified = 0
                        sample.required_verification = 1
                    else:
                        sample.verified = 1
                        sample.required_verification = 0

                sample.facility_id = original_facility_id
                sample.patient = patient

                if pst.get('from_page') == 'verify' or pst.get('from_page') == 'approvals':
                    sample.verified = 1
                    sample.verified_at = datetime.now().date()
                    sample.verifier = user
                
                rc_id = pst.get('results_qc_id')
                if rc_id:
                    resultsqc = ResultsQC.objects.get(pk=rc_id)
                    resultsqc.is_reviewed_for_dr = True
                    resultsqc.dr_reviewed_by_id = request.user
                    resultsqc.dr_reviewed_at = datetime.now()
                    resultsqc.save()
                    sample.verified = 1

                sample.patient_unique_id = patient.unique_id
                sample.sample_medical_lab = utils.user_lab(user)
                sample.save()
                return sample
        return None

    @staticmethod
    def create_drug_resistance(drug_resistance_form, pst,past_regimens_formset,sample):
        if 'has_dr' in pst:
            drug_resistance = drug_resistance_form.save(commit=False)
            drug_resistance.sample = sample
            drug_resistance.save()

            past_regimens = past_regimens_formset.save(commit=False)
            for past_regimen in past_regimens:
                past_regimen.drug_resistance_request = drug_resistance
                past_regimen.save()

    @staticmethod
    def validate_forms(patient_form, envelope_form, sample_form, drug_resistance_form, past_regimens_formset, pst):
        if not all([
            patient_form.is_valid(),
            envelope_form.is_valid(),
            sample_form.is_valid(),
            drug_resistance_form.is_valid(),
            past_regimens_formset.is_valid(),
        ]):
            return False

        if not pst.get('dob') and not pst.get('null_dob'):
            patient_form.add_error('dob', 'Date of birth is required')
            return False

        if pst.get('gender') == 'F' and not sample_form.cleaned_data.get('pregnant'):
            patient_form.add_error('pregnant', 'Specify if patient is pregnant')
            return False

        if not sample_utils.initiation_date_valid(pst):
            patient_form.add_error('treatment_initiation_date', 'Initiation date cannot be before date of birth')
            return False

        if not sample_utils.collection_date_valid(pst):
            sample_form.add_error('date_collected', 'Sample collection date cannot be before date of birth')
            return False

        return True