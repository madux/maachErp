from odoo import fields, models, _
import requests
import json
import logging
# from odoo.addons.eha_auth.controllers.helpers import prepare_many
from datetime import datetime
from collections import OrderedDict

_logger = logging.getLogger(__name__)


class NCDCAetherSync(models.TransientModel):
    '''
        Aether Sync
    '''
    _name = "aether.sync.ncdc"
    _description = "Aether Sync NCDC"

    name = fields.Char()

    # def _get_symptoms_by_system(self, eval_id, system_name):
    #     return self.env['oeha.evaluation.symptom'].search([('evaluation_id', '=', eval_id), '|', ('system_id.name', '=', system_name), ('name', '=', system_name)])

    # def get_symptom_option_covid19_report(self, eval_id, symptom_code):
    #     try:
    #         # Code is unique and can only be used once, the first time you get a match, return
    #         general_symptoms = self._get_symptoms_by_system(eval_id, 'General')
    #         symptom = general_symptoms.filtered(
    #             lambda s: s.symptom_id.code == symptom_code) if general_symptoms else False
    #         if symptom:
    #             return symptom.option_id.option_id.name, symptom.others

    #         triage_symptoms = self._get_symptoms_by_system(
    #             eval_id, 'Patient Triage')
    #         symptom = triage_symptoms.filtered(
    #             lambda s: s.symptom_id.code == symptom_code) if triage_symptoms else False
    #         if symptom:
    #             return symptom.option_id.option_id.name, symptom.others

    #         risk_factors_symptoms = self._get_symptoms_by_system(
    #             eval_id, 'Risk Factors')
    #         symptom = risk_factors_symptoms.filtered(
    #             lambda s: s.symptom_id.code == symptom_code) if risk_factors_symptoms else False
    #         if symptom:
    #             return symptom.option_id.option_id.name, symptom.others

    #         ncdc_required_info_symptoms = self._get_symptoms_by_system(
    #             eval_id, 'NCDC Required Information')
    #         symptom = ncdc_required_info_symptoms.filtered(
    #             lambda s: s.symptom_id.code == symptom_code) if ncdc_required_info_symptoms else False
    #         if symptom:
    #             return symptom.option_id.option_id.name, symptom.others

    #         return False
    #     except Exception as ex:
    #         _logger.exception(ex)
    #         return False

    # def get_eval_records(self, mode="new"):
    #     ''' Syncing evaluation is neccessary. for instance, EPID NO is provided after the evaluation has been captured.
    #     When the EPID no is provided, the update should trigger a resync 
    #     '''
    #     new_checkpoint = self.env["aether.sync.checkpoint"].sudo().search(
    #         [('checkpoint_type', '=', 'New Eval')],
    #         order='id desc', limit=1)

    #     update_checkpoint = self.env["aether.sync.checkpoint"].sudo().search(
    #         [('checkpoint_type', '=', 'Updated Eval')],
    #         order='id desc', limit=1)
    #     if mode == 'new':
    #         domain = [
    #             ('template_id.name', '=', 'COVID-19 Triage'),
    #             ('create_date', '>', new_checkpoint.checkpoint),
    #         ] if new_checkpoint else []
    #     elif mode == 'update':
    #         if not update_checkpoint:
    #             self.env["aether.sync.checkpoint"].sudo(
    #             ).create_checkpoint("Updated Eval")

    #         domain = [
    #             ('template_id.name', '=', 'COVID-19 Triage'),
    #             ('write_date', '>', update_checkpoint.checkpoint),
    #         ] if update_checkpoint else [('write_date', '>', fields.Datetime.now())]
    #     else:  # both
    #         if update_checkpoint:
    #             domain = [('write_date', '>', update_checkpoint.checkpoint)]
    #         elif new_checkpoint:
    #             domain = [('create_date', '>', new_checkpoint.checkpoint)]
    #         else:
    #             domain = []

    #     evaluations = self.env['oeh.medical.evaluation'].search(domain)
    #     return self.extract_fields_for_aether(evaluations)

    # def get_labtest_records(self, mode="new"):
    #     ''' by default, syncing should be after COVID-19 lab test has been created.
    #     Also, when result status is updated by aether, resync should be triggered
    #      '''
    #     new_checkpoint = self.env["aether.sync.checkpoint"].sudo().search(
    #         [('checkpoint_type', '=', 'New Labtest')],
    #         order='id desc', limit=1)

    #     update_checkpoint = self.env["aether.sync.checkpoint"].sudo().search(
    #         [('checkpoint_type', '=', 'Updated Labtest')],
    #         order='id desc', limit=1)

    #     if mode == 'new':
    #         domain = [
    #             ('test_type.code', '=', 'COVID-19'),
    #             ('evaluation_id', '!=', False),
    #             ('create_date', '>', new_checkpoint.checkpoint),
    #         ] if new_checkpoint else []
    #     elif mode == 'update':
    #         if not update_checkpoint:
    #             self.env["aether.sync.checkpoint"].sudo().create_checkpoint(
    #                 "Updated Labtest"
    #             )

    #         domain = [
    #             ('test_type.code', '=', 'COVID-19'),
    #             ('evaluation_id', '!=', False),
    #             ('write_date', '>', update_checkpoint.checkpoint),
    #         ] if update_checkpoint else [('write_date', '>', fields.Datetime.now())]

    #     else:
    #         domain = ['|',
    #                   ('write_date', '>', update_checkpoint.checkpoint),
    #                   ('create_date', '>', new_checkpoint.checkpoint),
    #                   ]

    #     labtests = self.env['oeh.medical.lab.test'].search(domain)
    #     evaluations = labtests.mapped('evaluation_id')
    #     return self.extract_fields_for_aether(evaluations)

    # def get_evaluation_labtest(self, evaluation_id):
    #     return self.env['oeh.medical.lab.test'].search([('evaluation_id', '=', evaluation_id)], limit=1)

    # # def randomString(self, stringLength=8):
    # #     letters = string.ascii_lowercase
    # #     return ''.join(random.choice(letters) for i in range(stringLength))

    # def extract_fields_for_aether(self, eval_records):
    #     ''' extracts neccessary records into a structured list'''
    #     eval_list = []
    #     if eval_records:
    #         for evaluation in eval_records:
    #             epid_data = self.get_symptom_option_covid19_report(
    #                 evaluation.id, 'NCDC-RPT-026')
    #             _logger.info("EPID DATA " + str(epid_data))
    #             epid_no = epid_data[1] if epid_data else None
    #             labobject = self.get_evaluation_labtest(evaluation.id)
    #             ''' Prepare data for syncing only if labtest and EPID NO exists'''
    #             if labobject and epid_no is not None:
    #                 record = dict()
    #                 record['epid_no'] = epid_no
    #                 record['location'] = evaluation.branch_id.city or evaluation.branch_id.state_id.name or None
    #                 # lab details
    #                 record['lab'] = None
    #                 record['labtest_id'] = labobject.name
    #                 record['barcode'] = None
    #                 record['source'] = 'ehaclinics'
    #                 record['state'] = evaluation.patient.state_id.name if evaluation.patient.state_id else None
    #                 record['lga'] = evaluation.patient.lga or None
    #                 record['ward'] = evaluation.patient.ward or None
    #                 record['branch'] = evaluation.branch_id.name or None
    #                 record['current_status'] = 'alive'
    #                 record['data_collector'] = evaluation.create_uid.name
    #                 record['data_collector_institution'] = 'EHA Clinics Limited'
    #                 record['data_collector_phone'] = '0800 342 254 6427'
    #                 record['data_collector_email'] = 'info@eha.ng'
    #                 record['form_completion_date'] = fields.Datetime.context_timestamp(
    #                     evaluation, datetime.now()).strftime('%d/%m/%Y')
    #                 record['given_name'] = evaluation.patient.firstname or None
    #                 record['family_name'] = evaluation.patient.lastname or None
    #                 record['gender'] = evaluation.patient.sex or None
    #                 record['dob'] = evaluation.patient.dob.strftime('%d/%m/%Y')
    #                 record['phone'] = evaluation.patient.phone or evaluation.patient.mobile
    #                 record['age'] = evaluation.patient.age
    #                 record['email'] = evaluation.patient.email or None
    #                 street = evaluation.patient.street if evaluation.patient.street else ''
    #                 street2 = evaluation.patient.street2 if evaluation.patient.street2 else ''
    #                 record['residential_address'] = street + ' ' + street2
    #                 record['country_residence'] = 'Nigeria'
    #                 record['case_status'] = 'Suspected'
    #                 record['respondent_firstname'] = None
    #                 record['respondent_surname'] = None
    #                 record['respondent_gender'] = None
    #                 record['respondent_dob'] = None
    #                 record['respondent_address'] = None
    #                 record['respondent_phone'] = None
    #                 symp_onset_data = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-001')
    #                 record['date_first_symptom_onset'] = symp_onset_data[1] or None if symp_onset_data else None
    #                 history_fever_data = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-002')
    #                 record['history_fever'] = history_fever_data[0] if history_fever_data else None
    #                 sorethroat_data = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-0041')
    #                 record['sore_throat'] = sorethroat_data[0] if sorethroat_data else None
    #                 runnynose_data = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-0042')
    #                 record['runny_nose'] = runnynose_data[0] if runnynose_data else None
    #                 coughdata = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-003')
    #                 record['cough'] = coughdata[0] if coughdata else None
    #                 shortnessbreath_data = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-004')
    #                 record['shortness_breath'] = shortnessbreath_data[0] if shortnessbreath_data else None
    #                 vomitting_data = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-0029')
    #                 record['vomiting'] = vomitting_data[0] if vomitting_data else None
    #                 nausea_data = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-0030')
    #                 record['nausea'] = nausea_data[0] if nausea_data else None
    #                 diarrhoea_data = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-0031')
    #                 record['diarrhoea'] = diarrhoea_data[0] if diarrhoea_data else None
    #                 # initial
    #                 date_sample_collected_data = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-004')
    #                 record['initial_date_respiratory_sample_collected'] = date_sample_collected_data[1] or None if date_sample_collected_data else None
    #                 type_sample_collected = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-005')
    #                 record['initial_type_respiratory_sample_collected'] = type_sample_collected[
    #                     0] or type_sample_collected[1] if type_sample_collected else None
    #                 baseline_serum_taken = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-007')
    #                 record['initial_baseline_serum_taken'] = baseline_serum_taken[0] if baseline_serum_taken else None
    #                 record['initial_date_baseline_serum_taken'] = baseline_serum_taken[1] or None if baseline_serum_taken else None
    #                 other_samples_collected = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-009')
    #                 record['initial_other_samples_collected'] = other_samples_collected[0] if other_samples_collected else None
    #                 which_other_samples = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-0091')
    #                 record['initial_which_other_samples'] = which_other_samples[0] if which_other_samples else None
    #                 date_other_samples_taken = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-007')
    #                 record['initial_date_other_samples_collected'] = date_other_samples_taken[1] or None if date_other_samples_taken else None
    #                 # follow up
    #                 followup_date_sample_collected_data = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-0032')
    #                 record['followup_date_respiratory_sample_collected'] = followup_date_sample_collected_data[
    #                     1] or None if followup_date_sample_collected_data else None
    #                 followup_type_sample_collected = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-0033')
    #                 record['followup_type_respiratory_sample_collected'] = followup_type_sample_collected[
    #                     0] or followup_type_sample_collected[1] if followup_type_sample_collected else None
    #                 followup_baseline_serum_taken = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-0037')
    #                 record['followup_baseline_serum_taken'] = followup_baseline_serum_taken[0] if followup_baseline_serum_taken else None
    #                 record['followup_date_baseline_serum_taken'] = followup_baseline_serum_taken[1] or None if followup_baseline_serum_taken else None
    #                 followup_other_samples_collected = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-0034')
    #                 record['followup_other_samples_collected'] = followup_other_samples_collected[0] if followup_other_samples_collected else None
    #                 followup_which_other_samples = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-0035')
    #                 record['followup_which_other_samples'] = followup_which_other_samples[0] if followup_which_other_samples else None
    #                 followup_date_other_samples_taken = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-0036')
    #                 record['followup_date_other_samples_collected'] = followup_date_other_samples_taken[
    #                     1] or None if followup_date_other_samples_taken else None
    #                 # others
    #                 hospitalisation_required = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-010')
    #                 record['hospitalisation_required'] = hospitalisation_required[0] if hospitalisation_required else None
    #                 record['name_hospital'] = hospitalisation_required[1] or None if hospitalisation_required else None
    #                 icu_required = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-011')
    #                 record['icu_admission_required'] = icu_required[0] if icu_required else None
    #                 ards = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-012')
    #                 record['acute_respiratory_distress_syndrome'] = ards[0] if ards else None
    #                 pneumonia_chest_xray = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-013')
    #                 record['pneumonia_chest_xray'] = pneumonia_chest_xray[0] if pneumonia_chest_xray else None
    #                 record['pneumonia_chest_xray_date'] = pneumonia_chest_xray[1] or None if pneumonia_chest_xray else None
    #                 other_life_threatening_illness = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-014')
    #                 record['other_life_threatening_illness'] = other_life_threatening_illness[0] if other_life_threatening_illness else None
    #                 record['other_life_threatening_illness_specify'] = other_life_threatening_illness[1] or None if other_life_threatening_illness else None
    #                 mechanical_ventilation_required = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-015')
    #                 record['mechanical_ventilation_required'] = mechanical_ventilation_required[0] if mechanical_ventilation_required else None
    #                 extracorporeal_membrane_oxygenation = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-016')
    #                 record['extracorporeal_membrane_oxygenation'] = extracorporeal_membrane_oxygenation[0] if extracorporeal_membrane_oxygenation else None
    #                 # human exposures
    #                 dom_travel = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-005')
    #                 date_from_dom_travel = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-007')
    #                 date_to_dom_travel = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-006')
    #                 dom_cities = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-008')
    #                 dom_transport = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-009')
    #                 dom_airline = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-010')
    #                 dom_time = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-011')
    #                 record['domestic_travel_in_last_14days'] = dom_travel[0] if dom_travel else None
    #                 record['domestical_travel_date_from'] = date_from_dom_travel[1] or None if date_from_dom_travel else None
    #                 record['domestical_travel_date_to'] = date_to_dom_travel[1] or None if date_to_dom_travel else None
    #                 record['domestic_cities_visited'] = dom_cities[1] or None if dom_cities else None
    #                 record['domestic_means_of_transport'] = dom_transport[0] if dom_transport else None
    #                 record['domestic_airline'] = dom_airline[1] or None if dom_airline else None
    #                 record['domestic_time_of_flight'] = dom_time[1] or None if dom_time else None
    #                 # international travel
    #                 intl_travel = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-012')
    #                 date_from_intl_travel = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-013')
    #                 date_to_intl_travel = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-014')
    #                 intl_countries_visited = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-015')
    #                 intl_cities_visited = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-016')
    #                 intl_airline = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-017')
    #                 record['international_travel_in_last_14days'] = intl_travel[0] if intl_travel else None
    #                 record['international_travel_date_from'] = date_from_intl_travel[1] or None if date_from_intl_travel else None
    #                 record['international_travel_date_to'] = date_to_intl_travel[1] or None if date_to_intl_travel else None
    #                 record['international_countries_visited'] = intl_countries_visited[1] or None if intl_countries_visited else None
    #                 record['international_cities_visited'] = intl_cities_visited[1] or None if intl_cities_visited else None
    #                 record['international_airline'] = intl_airline[1] or None if intl_airline else None
    #                 # contact
    #                 contact_covid19 = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-TRI-018')
    #                 record['patient_contact_with_suspected_confirmed_covid_19_last_14days'] = contact_covid19[0] if contact_covid19 else None
    #                 record['patient_contact_with_suspected_confirmed_covid_19_last_14days_date'] = contact_covid19[1] or None if contact_covid19 else None
    #                 festival = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-017')
    #                 record['patient_attended_festival_or_mass_gathering'] = festival[0] if festival else None
    #                 record['patient_attended_festival_or_mass_gathering_specify'] = festival[1] or None if festival else None
    #                 exposed_to_similar_illness = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-018')
    #                 record['patient_exposed_to_person_with_similar_illness'] = exposed_to_similar_illness[0] if exposed_to_similar_illness else None
    #                 location_exposure = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-019')
    #                 record['patient_location_of_exposure'] = location_exposure[0] if location_exposure else None
    #                 record['patient_location_of_exposure_others_specify'] = location_exposure[1] or None if location_exposure else None
    #                 admitted_inpatient = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-020')
    #                 record['patient_visited_or_was_admitted_to_inpatient_health_facility'] = admitted_inpatient[0] if admitted_inpatient else None
    #                 record['patient_visited_or_was_admitted_to_inpatient_health_facility_specify'] = admitted_inpatient[1] or None if admitted_inpatient else None
    #                 admitted_outpatient = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-021')
    #                 record['patient_visited_outpatient_treatment_facility'] = admitted_outpatient[0] if admitted_outpatient else None
    #                 record['patient_visited_outpatient_treatment_facility_specify'] = admitted_outpatient[1] or None if admitted_outpatient else None
    #                 traditional_healer = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-022')
    #                 record['patient_visited_traditional_healer'] = traditional_healer[0] if traditional_healer else None
    #                 record['patient_visited_traditional_healer_specify'] = traditional_healer[1] or None if traditional_healer else None
    #                 patient_occupation = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-023')
    #                 record['patient_occupation'] = patient_occupation[0] if patient_occupation else None
    #                 record['patient_occupation_others_specify'] = patient_occupation[0] if patient_occupation else None
    #                 patient_occupation_location = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-028')
    #                 record['patient_occupation_location'] = patient_occupation_location[1] or None if patient_occupation_location else None
    #                 self_isolating = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-024')
    #                 record['patient_is_self_isolating'] = self_isolating[0] if self_isolating else None
    #                 record['patient_is_self_isolating_location'] = self_isolating[1] or None if self_isolating else None
    #                 completed = self.get_symptom_option_covid19_report(
    #                     evaluation.id, 'NCDC-RPT-025')
    #                 record['form_completed'] = completed[0] if completed else None
    #                 record['form_completed_reason'] = completed[1] or None if completed else None

    #                 # check for duplicate
    #                 if record not in eval_list:
    #                     sorted_record = OrderedDict(sorted(record.items()))
    #                     eval_list.append(sorted_record)
    #     return eval_list

    # def get_aether_create_url(self):
    #     aether_server = self.env["ir.config_parameter"].sudo(
    #     ).get_param("aether_server_ncdc", False)
    #     return "{}/kernel/entities/".format(aether_server)

    # def get_aether_update_url(self, id):
    #     aether_server = self.env["ir.config_parameter"].sudo(
    #     ).get_param("aether_server_ncdc", False)
    #     return "{0}/kernel/entities/{1}/".format(aether_server, id)

    # def post_to_aether(self, records, mode="new", operation="New Labtest"):
    #     aether_user = self.env["ir.config_parameter"].sudo(
    #     ).get_param("aether_username_ncdc", False)
    #     aether_pass = self.env["ir.config_parameter"].sudo(
    #     ).get_param("aether_password_ncdc", False)
    #     aether_referer = self.env["ir.config_parameter"].sudo(
    #     ).get_param("aether_referer_ncdc", False)
    #     schemadecorator_id = self.env["ir.config_parameter"].sudo(
    #     ).get_param("aether_schemadecorator_id_ncdc", False)
    #     id_field = 'labtest_id'
    #     headers = {
    #         "Content-Type": "application/json",
    #         "Referer": aether_referer
    #     }

    #     if len(records) > 0:
    #         result = prepare_many(
    #             records, id_field, schemadecorator_id)
    #         if mode == "new":
    #             json_records = json.dumps(result, indent=2)
    #             aether_url = self.get_aether_create_url()
    #             req = requests.post(
    #                 aether_url,
    #                 data=json_records,
    #                 headers=headers,
    #                 auth=(aether_user, aether_pass))
    #             if req is not None:
    #                 # create checkpoint if entity already exists
    #                 # to avoid repeat syncing for the item
    #                 if 'already exists' in str(req.text) or req.status_code == 201:
    #                     self.env["aether.sync.checkpoint"].sudo(
    #                     ).create_checkpoint(operation)
    #             response_dict = {
    #                 "operation": operation,
    #                 "status_code": req.status_code,
    #                 "message": "success" if req.status_code == 201 else req.text[:50],
    #                 "payload": json.dumps(records, indent=2)
    #             }
    #             self.env['aether.sync.log'].sudo().create(response_dict)
    #         else:  # mode is update
    #             for update_item in result:
    #                 json_record = json.dumps(update_item, indent=2)
    #                 aether_url = self.get_aether_update_url(
    #                     update_item.get("id"))
    #                 req = requests.put(
    #                     aether_url,
    #                     data=json_record,
    #                     headers=headers,
    #                     auth=(aether_user, aether_pass))
    #                 # create update checkpoint if response status code != 400.
    #                 # This is lame. Yes Yes, I know, but it works!
    #                 # TODO: Hey Critic!, kindly refactor to make it better
    #                 if req.status_code != 400:
    #                     self.env["aether.sync.checkpoint"].sudo(
    #                     ).create_checkpoint(operation)
    #                 # log the request response
    #                 response_dict = {
    #                     "operation": operation,
    #                     "status_code": req.status_code,
    #                     "message": "success" if req.status_code == 201 else req.text[:50],
    #                     "payload": json_record
    #                 }
    #                 self.env['aether.sync.log'].sudo().create(response_dict)
    #         return req

    # def sync_from_labtest(self, mode="new"):
    #     try:
    #         records = self.get_labtest_records(
    #             mode="new") if mode == "new" else self.get_labtest_records(mode="update")
    #         operation = "New Labtest" if mode == "new" else "Updated Labtest"
    #         return self.post_to_aether(records, mode=mode, operation=operation)
    #     except Exception as ex:
    #         _logger.exception(ex)

    # def sync_from_eval(self, mode="new"):
    #     try:
    #         records = self.get_eval_records(
    #             mode="new") if mode == "new" else self.get_eval_records(mode="update")
    #         operation = "New Eval" if mode == "new" else "Updated Eval"
    #         return self.post_to_aether(records, mode=mode, operation=operation)
    #     except Exception as ex:
    #         _logger.exception(ex)

    # def cron_sync_to_aether(self):
    #     try:
    #         conf_sync_new = self.env['ir.config_parameter'].sudo().get_param(
    #             'aether_connector.ncdc_sync_new', 'False')
    #         conf_sync_update = self.env['ir.config_parameter'].sudo().get_param(
    #             'aether_connector.ncdc_sync_update', 'False')

    #         if conf_sync_new is not None and conf_sync_new.lower() == 'true':
    #             self.sync_from_labtest(mode="new")
    #             self.sync_from_eval(mode="new")
    #             _logger.info("AETHER SYNC NEW")
    #         elif conf_sync_update is not None and conf_sync_update.lower() == 'true':
    #             self.sync_from_labtest(mode="update")
    #             self.sync_from_eval(mode="update")
    #             _logger.info("AETHER SYNC UPDATE")

    #         else:
    #             self.sync_from_labtest(mode="both")
    #             self.sync_from_eval(mode="both")
    #             _logger.info("AETHER SYNC BOTH")

    #     except Exception as ex:
    #         _logger.exception(ex)

    # def cron_purge_sync_log(self):
    #     ''' Schedule a Cron that runs every week to clear this log'''
    #     SQL = '''TRUNCATE TABLE aether_sync_log;'''
    #     self.env.cr.execute(SQL)
    #     self.env.cr.commit()
