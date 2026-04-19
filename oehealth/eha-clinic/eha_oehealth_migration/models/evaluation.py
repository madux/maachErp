from odoo import models, fields, api
from datetime import datetime
from urllib.parse import urlencode
from ..tools.splittor import splittor as sp
import logging
import pprint
import random
pp = pprint.PrettyPrinter(indent=4)
_logger = logging.getLogger(__name__)

################################################
# PROCESSES INVOLVED IN DEVELOPING THIS APP 
# create an action server to call a code item_function eg. /evaluation_views.xml
#     create a function that defines the code (item_function)
#     create a cron to run cron code _item_function in /data.xml which calls item_function
#     there is a process in the item function method 
#         On eha_emr_connector module / models / conn, see the _get_fhir_repr
#         create a _get_fhir_repr method on the target object and add the compositions from eha care 

#         1. _get_composition_url_template, returns the composition url for the specified object

class OehaEvaluation(models.Model):
    _inherit = 'oeh.medical.evaluation'

    migrated_anthropometry_to_emr = fields.Boolean(
        string='Migrated to EMR', copy=False)
    migrated_evaluation_to_emr = fields.Boolean(
        string='Migrated Evaluation to EMR', copy=False)
    migrated_hpi_to_emr = fields.Boolean(
        string='Migrated HPI to EMR', copy=False)
    migrated_prescription_to_emr = fields.Boolean(
        string='Migrated Prescription to EMR', copy=False)
    
    def migrate_evaluation_artifacts_to_emr(self):
        for evaluation in self:
            evaluation.migrate_evaluation_to_emr()
            evaluation.migrate_anthropometry_to_emr()
            evaluation.migrate_hpi_to_emr()
            evaluation.vitalsigns.migrate_to_emr()
            evaluation.medication_allergies_ids.migrate_to_emr()

    def _get_fhir_repr(self, operation=False):
        """Convert Evaluation anthrpometry, hpi, anthropometry, prescription record to a fhir resource
        {
            "ctx/language": "en",
            "ctx/territory": "US",
            "ctx/composer_name": "Silvia Blake",
            "ctx/id_namespace": "HOSPITAL-NS",
            "ctx/id_scheme": "HOSPITAL-NS",
            "ctx/participation_name": "Dr. Marcus Johnson",
            "ctx/participation_function": "requester",
            "ctx/participation_mode": "face-to-face communication",
            "ctx/participation_id": "199",
            "ctx/participation_name:1": "Lara Markham",
            "ctx/participation_function:1": "performer",
            "ctx/participation_id:1": "198",
            "ctx/health_care_facility|name": "Hospital",
            "ctx/health_care_facility|id": "9091",
            "anthropometry/context/encounter_context/encounter_id": "Encounter Id 71",
            "anthropometry/context/encounter_context/date_created": "2023-03-14T09:10:01.463Z",
            "anthropometry/context/encounter_context/created_by": "Created by 62",
            "anthropometry/context/encounter_context/patient_name": "Patient name 32",
            "anthropometry/context/encounter_context/patient_id": "Patient ID 45",
            "anthropometry/context/encounter_context/membership_plan": "Membership plan 47",
            "anthropometry/context/encounter_context/membership_status": "Membership status 85",
            "anthropometry/context/encounter_context/admission_id": "Admission Id 62",
            "anthropometry/context/encounter_context/branch_code": "Branch code 56",
            "anthropometry/context/encounter_context/branch_name": "Branch name 36",
            "anthropometry/body_weight/any_event:0/weight|magnitude": 18.39,
            "anthropometry/body_weight/any_event:0/weight|unit": "kg",
            "anthropometry/height_length/any_event:0/height_length|magnitude": 0.0,
            "anthropometry/height_length/any_event:0/height_length|unit": "cm",
            "anthropometry/body_mass_index/any_event:0/body_mass_index|magnitude": 0.0,
            "anthropometry/body_mass_index/any_event:0/body_mass_index|unit": "kg/m2",
            "anthropometry/body_mass_index/any_event:0/clinical_interpretation": "Clinical interpretation 69",
            "anthropometry/body_mass_index/any_event:0/comment": "Comment 66",
            "anthropometry/head_circumference/any_event:0/head_circumference|magnitude": 76.96,
            "anthropometry/head_circumference/any_event:0/head_circumference|unit": "cm",
            "anthropometry/head_circumference/any_event:0/comment": "Comment 44",
            "anthropometry/waist_circumference/any_event:0/waist_circumference|magnitude": 0.0,
            "anthropometry/waist_circumference/any_event:0/waist_circumference|unit": "cm",
            "anthropometry/waist_circumference/any_event:0/comment": "Comment 57",
            "anthropometry/body_segment_circumference/any_event:0/body_segment_name|code": "at0019",
            "anthropometry/body_segment_circumference/any_event:0/laterality|code": "at0007",
            "anthropometry/body_segment_circumference/any_event:0/circumference|magnitude": 40.2,
            "anthropometry/body_segment_circumference/any_event:0/circumference|unit": "cm",
            "anthropometry/body_segment_circumference/any_event:0/comment": "Comment 88",
            "anthropometry/body_segment_circumference/any_event:0/confounding_factors": "Confounding factors 30",
            "anthropometry/body_segment_circumference/any_event:0/body_position|code": "at0039"
        }
        """
        for eval in self:
            create_date = datetime.strftime(
                eval.create_date, "%Y-%m-%d") if eval.create_date else ""
            eval_as_a_fhir_resource = {
                "ctx/language": "en",
                "ctx/territory": "US",
                "ctx/composer_name": "{composer_name}".format(composer_name=eval.create_uid.name),
                "ctx/id_namespace": "HOSPITAL-NS",
                "ctx/id_scheme": "HOSPITAL-NS",
                "ctx/participation_name": "{nurse_name}".format(nurse_name=eval.nurse.name),
                "ctx/participation_function": "requester",
                "ctx/participation_mode": "face-to-face communication",
                "ctx/participation_id": "199",
                "ctx/participation_name:1": "{doctor_name}".format(doctor_name=eval.care_provider.name),
                "ctx/participation_function:1": "performer",
                "ctx/participation_id:1": "198",
                "ctx/health_care_facility|name": "Hospital",
                "ctx/health_care_facility|id": "9091",
                "anthropometry/context/encounter_context/encounter_id": "{evaluation_name}".format(evaluation_name=eval.name),
                "anthropometry/context/encounter_context/date_created": "{create_date}".format(create_date=create_date),
                "anthropometry/context/encounter_context/created_by": "Created by 62",
                "anthropometry/context/encounter_context/patient_name": "{}".format(eval.patient.name),
                "anthropometry/context/encounter_context/patient_id": "{}".format(eval.patient.identification_code),
                "anthropometry/context/encounter_context/membership_plan": "",
                "anthropometry/context/encounter_context/membership_status": "",
                "anthropometry/context/encounter_context/admission_id": "",
                "anthropometry/context/encounter_context/branch_code": "{}".format(eval.branch_id.name or ""),
                "anthropometry/context/encounter_context/branch_name": "{}".format(eval.branch_id.name or ""),
                
                "anthropometry/body_weight/any_event:0/weight|magnitude": "{weight}".format(weight=eval.weight),
                "anthropometry/body_weight/any_event:0/weight|unit": "kg",
                "anthropometry/height_length/any_event:0/height_length|magnitude": "{height}".format(height=eval.height),
                "anthropometry/height_length/any_event:0/height_length|unit": "cm",
                "anthropometry/body_mass_index/any_event:0/body_mass_index|magnitude": "{bmi}".format(bmi=eval.bmi),
                "anthropometry/body_mass_index/any_event:0/body_mass_index|unit": "kg/m2",
                
                
                "anthropometry/body_mass_index/any_event:0/clinical_interpretation": "Clinical interpretation 69",
                "anthropometry/body_mass_index/any_event:0/comment": "Comment 66",


                "anthropometry/head_circumference/any_event:0/head_circumference|magnitude": "{head_circumference}".format(head_circumference=eval.head_circumference),
                "anthropometry/head_circumference/any_event:0/head_circumference|unit": "cm",

                "anthropometry/head_circumference/any_event:0/comment": "Comment 44",

                "anthropometry/waist_circumference/any_event:0/waist_circumference|magnitude": "{abdominal_circumference}".format(abdominal_circumference=eval.abdominal_circ),
                "anthropometry/waist_circumference/any_event:0/waist_circumference|unit": "cm",
                "anthropometry/waist_circumference/any_event:0/comment": "Comment 55",

                "anthropometry/body_segment_circumference/any_event:0/body_segment_name|code": "at0019",
                "anthropometry/body_segment_circumference/any_event:0/laterality|code": "at0007",
                "anthropometry/body_segment_circumference/any_event:0/circumference|magnitude": 0.0,
                "anthropometry/body_segment_circumference/any_event:0/circumference|unit": "cm",
                "anthropometry/body_segment_circumference/any_event:0/comment": "Comment 88",
                "anthropometry/body_segment_circumference/any_event:0/confounding_factors": "Confounding factors 30",
                "anthropometry/body_segment_circumference/any_event:0/body_position|code": "at0039"
            }

            evaluation_date = datetime.strftime(
                eval.evaluation_start_date, "%Y-%m-%d") if eval.evaluation_start_date else ""
            
            # "": "" added empty key and value to ensure dict fetch doesnt break up
            eval_class_dicts = {
                "New Complaint": "New Complaint",
                "Follow up": "Follow up",
                "Checkup": "Check up",
                "Annual Health Checkup": "Annual Visit",
                "Inpatient Admission": "Inpatient",
                "Ambulatory": "Ambulatory",
                "Emergency": "Emergency",
                "Phone call": "Phone Call",
                "Telemedicine": "Telehealth",
                "": ""
            }  # what to be sent to fhir

            eval_templates_dicts = {
                "Acute": "Acute/Ambulatory",
                "COVID-19 Triage": "COVID-19",
                "Ocular": "Optometry",
                "Vision Spring Evaluation": "Optometry",
                "Eye Foundation - Optometrist Form": "Optometry",
                "Eye Foundation - Follow Up Form": "Optometry",
                "Dental": "Dental",
                "Dietary": "Dietary",
                "Health Tribe": "Health Tribe",
                "": ""
            }  # what to be sent to fhir
 
            eval_servicetype_dicts = {
                "Antenatal": "Antenatal",
                "Family Planning": "Family Planning",
                "Immunization": "Immunization",
                "": ""
            }
            ##########
            eval_type = "New Patient Consultation"
            eval_class = "Ambulatory"
            eval_service = "Doctor Consultation"
            evaluation_template = eval.template_id
            evaluation_type = eval.evaluation_type
            eval_result = eval_templates_dicts.get(evaluation_template.name, "")
            eval_type = eval_result if eval_result else "Other"
            if evaluation_type not in ['Antenatal', 'Family Planning', 'Immunization']:
                eval_class_result = eval_class_dicts.get(evaluation_type, "")
                eval_class = eval_class_result if eval_class_result else "Other"
            else:
                eval_service_result = eval_servicetype_dicts.get(evaluation_type, "")  # based on the value that was passed
                eval_service = eval_service_result if eval_service_result else "Other"
            _logger.info(
                f"this is my eval type {eval_type} {eval_class} {eval_service}")
            
            """ Evaluation FHIR RESOURCES
            "ctx/language": "en",
            "ctx/territory": "US",
            "ctx/composer_name": "{Name of the person that created the evaluation}", 
            "ctx/id_namespace": "HOSPITAL-NS",
            "ctx/id_scheme": "HOSPITAL-NS",
            "ctx/participation_name": "{Name of the nurse that worked on the encounter}",
            "ctx/participation_function": "requester",
            "ctx/participation_mode": "face-to-face communication",
            "ctx/participation_id": "199",
            "ctx/participation_name:1": "{Name of the doctor that worked on the encounter}",
            "ctx/participation_function:1": "performer",
            "ctx/participation_id:1": "198",
            "ctx/health_care_facility|name": "Hospital",
            "ctx/health_care_facility|id": "9091",
            "patient_encounter/context/encounter_context/date_created": "{Odoo Create date  YYYY-mm-dd}",
            "patient_encounter/patient_encounter/encounter_id": "{Evaluation number}",
            "patient_encounter/patient_encounter/encounter_id|issuer": "EHA Clinics",
            "patient_encounter/patient_encounter/encounter_id|assigner": "Assigner",
            "patient_encounter/patient_encounter/encounter_id|type": "Custom",
            "patient_encounter/patient_encounter/encounter_date": "{Evaluation date  YYYY-mm-dd}",
            "patient_encounter/patient_encounter/reason_for_encounter": "{Chief Complaint}",
                "patient_encounter/patient_encounter/encounter_type|value": "{eval_type}".format(eval_type=eval_type),
            "patient_encounter/patient_encounter/encounter_type": "{See explanation above on how to map}",
            "patient_encounter/patient_encounter/patient_membership_plan": "Patient membership plan 58",
            "patient_encounter/patient_encounter/patient_name": "{Full name of the patient}",
            "patient_encounter/patient_encounter/patient_id": "{HP Number}",
            "patient_encounter/patient_encounter/nurse/name": "{Name of the nurse: STRING}",
            "patient_encounter/patient_encounter/attending_clinician/name": "{Name of the care provider | string},
            "patient_encounter/patient_encounter/physical_location/facility/name": "{branch name | string}",
            "patient_encounter/patient_encounter/patient_age:0": "{the age of the patient at which the evaluation was created| integer}",
            "patient_encounter/patient_encounter/encounter_state": "{In progress maps to "Draft" , Completed maps to "Finished" }",
            "patient_encounter/patient_encounter/episode_of_care_-_additional_info/sensitivity|code": "at0004",
            "patient_encounter/patient_encounter/episode_of_care_-_additional_info/service_type|code": "{name of the service}",
            "patient_encounter/patient_encounter/episode_of_care_-_additional_info/service_type|value": "{name of the service}",
            "patient_encounter/patient_encounter/episode_of_care_-_additional_info/service_type|terminology": "EHA",
            "patient_encounter/patient_encounter/episode_of_care_-_additional_info/encounter_class": "See explanation above on how to map"

            """
            evaluation_fhir_resource = {
                "ctx/language": "en",
                "ctx/territory": "US",
                "ctx/composer_name": "{composer_name}".format(composer_name=eval.create_uid.name),
                "ctx/id_namespace": "HOSPITAL-NS",
                "ctx/id_scheme": "HOSPITAL-NS",
                "ctx/participation_name": "{nurse_name}".format(nurse_name=eval.nurse.name),
                "ctx/participation_function": "requester",
                "ctx/participation_mode": "face-to-face communication",
                "ctx/participation_id": "199",
                "ctx/participation_name:1": "{doctor_name}".format(doctor_name=eval.care_provider.name),
                "ctx/participation_function:1": "performer",
                "ctx/participation_id:1": "198",
                "ctx/health_care_facility|name": "Hospital",
                "ctx/health_care_facility|id": "9091",
                "patient_encounter/context/encounter_context/date_created": "{create_date}".format(create_date=f'''{datetime.strftime(eval.create_date, "%Y-%m-%d") if eval.create_date else ""}'''),
                "patient_encounter/patient_encounter/encounter_id": "{evaluation_name}".format(evaluation_name=eval.name),
                "patient_encounter/patient_encounter/encounter_id|issuer": "EHA Clinics", 
                "patient_encounter/patient_encounter/encounter_id|assigner": "Assigner",
                "patient_encounter/patient_encounter/encounter_id|type": "Custom",
                "patient_encounter/patient_encounter/encounter_date": "{evaluation_date}".format(evaluation_date=evaluation_date),
                "patient_encounter/patient_encounter/reason_for_encounter": "{}".format(eval.chief_complaint) if eval.chief_complaint else 'N/A',
                "patient_encounter/patient_encounter/encounter_type|code": "{eval_type}".format(eval_type=eval_type),
                "patient_encounter/patient_encounter/encounter_type|value": "{eval_type}".format(eval_type=eval_type),
                 "patient_encounter/patient_encounter/patient_membership_plan": "Patient membership plan 58",
                "patient_encounter/patient_encounter/patient_name": "{}".format(eval.patient.name),
                "patient_encounter/patient_encounter/patient_id": "{}".format(eval.patient.identification_code),
                "patient_encounter/patient_encounter/nurse/name": "{nurse_name}".format(nurse_name=eval.nurse.name),
                "patient_encounter/patient_encounter/attending_clinician/name":  "{care_provider}".format(care_provider=eval.care_provider.name),
                "patient_encounter/patient_encounter/physical_location/facility/name": "{}".format(eval.branch_id.name),
                "patient_encounter/patient_encounter/patient_age:0": "{}".format(eval.patient.age),
                "patient_encounter/patient_encounter/encounter_state": "Finished" if eval.state in "Completed" else "Draft",
                "patient_encounter/patient_encounter/episode_of_care_-_additional_info/sensitivity|code": "at0003",
                "patient_encounter/patient_encounter/episode_of_care_-_additional_info/service_type|code": "{}".format(eval_service),
                "patient_encounter/patient_encounter/episode_of_care_-_additional_info/service_type|value": "{}".format(eval_service),
                "patient_encounter/patient_encounter/episode_of_care_-_additional_info/service_type|terminology": "EHA",
                "patient_encounter/patient_encounter/episode_of_care_-_additional_info/encounter_class":  "{}".format(eval_class),
            }
            hpi_fhir_resource = {
                "ctx/language": "en",
                "ctx/territory": "US",
                "ctx/composer_name": "{composer_name}".format(composer_name=eval.create_uid.name),
                "ctx/id_namespace": "HOSPITAL-NS",
                "ctx/id_scheme": "HOSPITAL-NS",
                "ctx/participation_name": "{nurse_name}".format(nurse_name=eval.nurse.name),
                "ctx/participation_function": "requester",
                "ctx/participation_mode": "face-to-face communication",
                "ctx/participation_id": "199",
                "ctx/participation_name:1": "{care_provider}".format(care_provider=eval.care_provider.name),
                "ctx/participation_function:1": "performer",
                "ctx/participation_id:1": "198",
                "ctx/health_care_facility|name": "Hospital",
                "ctx/health_care_facility|id": "9091",
                "history_of_presenting_illness/context/encounter_identifier/encounter_id": "{evaluation_name}".format(evaluation_name=eval.name),
                "history_of_presenting_illness/story_history/any_event:0/story:0": "{hpi}".format(hpi=eval.hpi)
            }
            
            if operation == "evaluation":
                fhir_resource = evaluation_fhir_resource

            elif operation == "anthropometry":
                fhir_resource = eval_as_a_fhir_resource

            elif operation == "hpi":
                fhir_resource = hpi_fhir_resource

            # elif operation == "prescription":
            #     fhir_resource = prescription_fhir_resource
            pp.pprint(fhir_resource)
            return fhir_resource

    @api.model
    def _migrate_record_to_emr(self, operation):
        # e.g operation_to_run = 'evaluation'
        if operation == "evaluation":
            return self._migrate_evaluation_to_emr()
        elif operation == 'anthropometry':
            return self._migrate_anthropometry_to_emr()
        elif operation == 'hpi':
            return self._migrate_hpi_to_emr()
        elif operation == 'prescription':
            return self._migrate_prescription_to_emr()

    def _migrate_evaluation_to_emr(self):
        evals = self.search(
            [('migrated_evaluation_to_emr', '=', False), ('patient.ehr_id', '!=', False)], limit=2000).sorted(lambda r: r['create_date'], reverse=True)

        for eval in sp(evals):
            eval.migrate_evaluation_to_emr()

    def migrate_evaluation_to_emr(self):
        for eval in self:
            if eval.migrated_evaluation_to_emr:
                continue
            if not eval.patient.ehr_id:
                continue
            params = {}
            composition_url, template_id = self._get_composition_url_template(
                "evaluation")
            params['templateId'] = template_id
            params['ehrId'] = eval.patient.ehr_id
            params['format'] = "FLAT"
            parse_url = urlencode(params)
            target_url = f"{composition_url}?{parse_url}"
            _logger.info(f"====== see my url ====={target_url}=====")
            resp = self.env['eha.emr.connector'].sudo(
            )._create_record(eval, target_url, "evaluation")
            if resp:
                eval.update({'migrated_evaluation_to_emr': True})
                _logger.info(
                    f"====== Evaluation was created successful ==========")
            if not resp:
                _logger.info(
                    f"========= Evaluation was not created ================")
            self.env.cr.commit()

    def _migrate_anthropometry_to_emr(self):
        evals = self.search(
            [('migrated_anthropometry_to_emr', '=', False), ('patient.ehr_id', '!=', False)], limit=2000).sorted(lambda r: r['create_date'], reverse=True)

        for eval in sp(evals):  # batch the records
            # url = https://dev-bettercare.eha.ng/ehr/rest/v1/composition?templateId=Anthropometry&ehrId={ehrId}&format=FLAT
            eval.migrate_anthropometry_to_emr()

    def migrate_anthropometry_to_emr(self):
        for eval in self:
            if eval.migrated_anthropometry_to_emr:
                continue
            if not eval.patient.ehr_id:
                continue
            params = {}
            composition_url, template_id = self._get_composition_url_template(
                'anthropometry')
            params['templateId'] = template_id
            params['ehrId'] = eval.patient.ehr_id
            params['format'] = "FLAT"
            parse_url = urlencode(params)
            target_url = f"{composition_url}?{parse_url}"
            resp = self.env['eha.emr.connector'].sudo(
            )._create_record(eval, target_url, "anthropometry")
            if resp:
                eval.update({'migrated_anthropometry_to_emr': True})
                _logger.info(
                    f"====== Anthropometry was created successfully ==========")
            if not resp:
                _logger.info(
                    f"========= Anthropometry was not created ================")
            self.env.cr.commit()

    
    def _migrate_prescription_to_emr(self):
        evals = self.search(
            [('patient.ehr_id', '!=', False)], limit=2000).sorted(lambda r: r['create_date'], reverse=True)

        for eval in sp(evals):  # batch the records
            # url = https://dev-bettercare.eha.ng/ehr/rest/v1/composition?templateId=Anthropometry&ehrId={ehrId}&format=FLAT
            eval.migrate_prescription_to_emr()

    def migrate_prescription_to_emr(self):
        for eval in self:
            # if eval.migrated_prescription_to_emr:
            #     continue
            if not eval.patient.ehr_id:
                continue
            params = {}
            composition_url, template_id = self._get_composition_url_template(
                'prescription')
            # composition is the main link to eha care 
            # template id is e.g prescription
            params['templateId'] = template_id
            params['ehrId'] = eval.patient.ehr_id
            params['format'] = "STRUCTURED" # "FLAT" STRUCTURED #
            parse_url = urlencode(params)
            # https://dev-bettercare.eha.ng/ehr/rest/v1/composition?templateId=Prescription&ehrId={{ehrId}}&format=STRUCTURED
            target_url = f"{composition_url}?{parse_url}"
            prescription_ids =  set([rec.prescription_id.id for rec in eval.mapped('evaluation_prescription_ids').filtered(
                lambda pr: not pr.prescription_id.migrated_prescription_to_emr)])
            prescriptions = self.env['oeh.medical.prescription'].browse(prescription_ids)
            for pres in prescriptions:
                try:
                    pres.update({'evaluation_id': eval.id})
                except Exception as ex:
                    _logger.exception(ex)
                
                resp = self.env['eha.emr.connector'].sudo(
                )._create_record(pres, target_url, "prescription")
                if resp:
                    eval.update({'migrated_prescription_to_emr': True})
                    pres.update({'migrated_prescription_to_emr': True})
                    _logger.info(
                        f"====== prescription was created successfully ==========")
                if not resp:
                    _logger.info(
                        f"========= prescription was not created ================")
                self.env.cr.commit()


    def _migrate_hpi_to_emr(self):
        # TODO: Add domain to filterout already migrated records
        evals = self.search(
            [('migrated_hpi_to_emr', '=', False), ('patient.ehr_id', '!=', False)], limit=2000).sorted(lambda r: r['create_date'], reverse=True)

        for eval in sp(evals):  # batch the records
            # url = https://dev-bettercare.eha.ng/ehr/rest/v1/composition?templateId=Anthropometry&ehrId={ehrId}&format=FLAT
            eval.migrate_hpi_to_emr()

    def migrate_hpi_to_emr(self):
        """Method to migrate HPI information of a single instance to ehacare server
        """
        for eval in self:
            if eval.migrated_hpi_to_emr:
                continue
            if not eval.patient.ehr_id:
                continue
            params = {}
            composition_url, template_id = self._get_composition_url_template(
                'hpi')
            params['templateId'] = template_id
            params['ehrId'] = eval.patient.ehr_id
            params['format'] = "FLAT"
            parse_url = urlencode(params)
            target_url = f"{composition_url}?{parse_url}"
            resp = self.env['eha.emr.connector'].sudo(
            )._create_record(eval, target_url, "hpi")
            if resp:
                eval.update({'migrated_hpi_to_emr': True})
                _logger.info(
                    f"====== HPI was created successfully ==========")
            if not resp:
                _logger.info(
                    f"========= HPI was not created ================")
            self.env.cr.commit()

    @api.model
    def _get_composition_url_template(self, operation=None):
        """Get the composition url and template from system parameter
        """
        ICP = self.env['ir.config_parameter'].sudo()
        template_id = None
        composition_url = ICP.get_param(
            "eha_oehealth_migration.composition_url", '')
        if operation == "evaluation":
            template_id = ICP.get_param(
                "eha_oehealth_migration.evaluation_template_id", "")
        if operation == "anthropometry":
            template_id = ICP.get_param(
                "eha_oehealth_migration.anthropometry_template_id", "")
        if operation == "hpi":
            template_id = ICP.get_param(
                "eha_oehealth_migration.hpi_template_id", "")
        if operation == "prescription":
            template_id = ICP.get_param(
                "eha_oehealth_migration.prescription_template_id", "")
        return composition_url, template_id



class OehMedicalPrescription(models.Model):
    _inherit = 'oeh.medical.prescription'

    migrated_prescription_to_emr = fields.Boolean(string='Migrated to EMR', copy=False)

    def get_date_method(self, date):
        if date:
            return datetime.strftime(date, "%Y-%m-%d")
        else:
            return ""

    def _get_fhir_repr(self, operation=False):
        _logger.info(f'patient name is {self.patient}')
        prescription_fhir_resource = {
                "ctx/language": "en",
                "ctx/territory": "US",
                "ctx/composer_name": "{composer_name}".format(composer_name=self.create_uid.name), 
                "ctx/id_namespace": "HOSPITAL-NS",
                "ctx/id_scheme": "HOSPITAL-NS",
                "ctx/participation_name": "{nurse_name}".format(nurse_name=self.evaluation_id.name),
                "ctx/participation_function": "requester",
                "ctx/participation_mode": "face-to-face communication",
                "ctx/participation_id": "199",
                "ctx/participation_name:1": "{care_provider}".format(care_provider=self.evaluation_id.care_provider.name),
                "ctx/participation_function:1": "performer",
                "ctx/participation_id:1": "198",
                "ctx/health_care_facility|name": "Hospital",
                "ctx/health_care_facility|id": "9091",
                "prescription": {
                    "context": [
                        {
                            "encounter_context": [
                                {
                                    "encounter_id": [
                                        "{evaluation_name}".format(evaluation_name=self.evaluation_id.name),
                                    ],
                                    "date_created": [
                                        "{create_date}".format(create_date=f'''{datetime.strftime(self.evaluation_id.create_date, "%Y-%m-%d") if self.evaluation_id.create_date else ""}'''),
                                    ],
                                    "created_by": [
                                        "{create_uid}".format(create_uid=self.evaluation_id.create_uid.name),
                                    ],
                                    "patient_name": [
                                         "{}".format(self.patient.name),
                                    ],
                                    "patient_id": [
                                         f"{self.patient.identification_code or ''}" #.format(self.patient.identification_code),
                                    ],
                                    "branch_code": [
                                         f"{self.branch_id.code or ''}" #.format(self.branch_id.name or ""),
                                    ],
                                    "branch_name": [
                                        f"{self.branch_id.name or ''}" #.format(self.branch_id.name),
                                    ]
                                }
                            ],
                            "prescription_identifier": [
                                {
                                    "": f"{self.name or ''}",
                                    "|issuer": "Issuer",
                                    "|assigner": "Assigner",
                                    "|type": "Prescription"
                                }  
                            ],
                            "prescribed_by": [f"{self.prescriber.name or ''}"],
                            "prescribed_date": [datetime.strftime(self.date, "%Y-%m-%d") if self.date else '']
                            ,
                            "patient_name": [
                                f"{self.patient.name or ''}" # "{}".format(self.patient.name)
                            ],
                            "patient_dob": [
                                f"""{datetime.strftime(self.evaluation_id.patient.dob, "%Y-%m-%d")}"""
                                # "{}".format(datetime.strftime(self.evaluation_id.patient.dob, "%Y-%m-%d") if self.patient.dob else '')
                            ],
                            "patient_age": [
                                 f"{self.patient.age or '' }" #.format(self.patient.age),
                            ],
                            "patient_weight": [
                                {
                                    "|magnitude": "{weight}".format(weight=self.evaluation_id.weight  or ''), #  {patient weight from encounter} ,
                                    "|unit": "kg"
                                }
                            ],
                            "no_prescription_items": [
                                f'''{len([pl for pl in self.mapped('prescription_line')])}'''
                                #   "{}".format(len([pl for pl in self.mapped('prescription_line')])), #{count of items in prescription line:  type is integer}
                            ],
                            "no_refills": [
                                f'''{len(self.mapped('prescription_line').filtered(lambda norefill: norefill.is_refillable))}'''
                                # "{}".format(len(self.mapped('prescription_line').filtered(lambda norefill: norefill.is_refillable))), #{count of lines marked as refillable:  type is integer}
                            ],
                            "branch_name": [
                                f"{self.branch_id.name or ''}"#.format(self.branch_id.name),
                            ],
                            "branch_code": [
                                f"{self.branch_id.code or ''}" #"{}".format(self.branch_id.name),
                            ],
                            "state": [
                                {
                                    "|code": f"{'Dispensed' if self.state == 'Dispensed' else 'Ordered'}", # "Dispensed {if odoo state is draft or sent to pharmacy, then ehacare state = Ordered otherwise ehacare state = Dispensed}",
                                    "|value": f"{'Dispensed' if self.state == 'Dispensed' else 'Ordered'}", #"Dispensed  {if odoo state is draft or sent to pharmacy, then ehacare state = Ordered otherwise ehacare state = Dispensed}" 
                                }
                            ]
                        }
                    ],
                    "medication_order": [ # this corresponds to odoo prescription lines. a new object should be built for each prescription line
                        {
                            "_uid": [
                                ''.join(random.choice('abcdefghiklmo3peo32345699898rstuv') for _ in range(10))
                            ],
                            "order": [
                                {
                                    "medication_item": [
                                        {
                                            "|code": f"{prl.name.name or ''}",#.format(prl.name.name),
                                            "|value": f"{prl.name.name or ''}", # '{}'.format(prl.name.name),
                                            "|terminology": "external_terminology"
                                        }
                                    ],
                                    "medication_details": [
                                        {
                                            "form": [
                                                f"{prl.dose_form.name or 'Other'}"#.format(prl.dose), # "{prescription line does form}"
                                            ],
                                        }
                                    ],
                                    "route": [f"{prl.dose_route.name or ''}"],# .format(prl.dose_route.name)], #"{prescription line route of administration}"
                                    "therapeutic_direction": [
                                        {
                                            "dosage": [
                                                {
                                                    "dose": [
                                                        {
                                                            "|magnitude": f'{prl.dose or 1}', 
                                                            "|unit": f'{prl.dose_unit.name or "tablet"}',
                                                        }
                                                    ],
                                                    "timing_-_daily": [
                                                        {
                                                            "frequency": [
                                                                f'{prl.common_dosage.name or ""}'#.format(prl.common_dosage.name),#"{prescription line common_dosage}"
                                                            ]
                                                        }
                                                    ],
                                                    "administration_duration": [
                                                        f"""{'PT' if prl.duration_period in ['Hours', 'Minutes'] else 'P'}{prl.duration}{'M' if prl.duration_period in ['Months','Minutes'] else 'W' if prl.duration_period == 'Weeks' else  'D' if prl.duration_period == 'Days' else 'Y' if prl.duration_period == 'Years' else 'H' if prl.duration_period == 'Hours' else 'D'}"""
                                                    ],
                                                }
                                            ],
                                        }
                                    ],
                                    "additional_instruction": [
                                        f'{self.info or ""}', #"{prescription line DOCTOR instruction}"
                                    ],
                                    "clinical_indication": [
                                        {
                                            "|code": f'{prl.indication.code or "Others"}', #f'{prl.indication.code}', #.format(prl.indication.code), #"{prescription line indication.code}",
                                            "|value": f'{prl.indication.name or "Others"}', #'{}'.format(prl.indication.name), # "{prescription line indication.name}",
                                            "|terminology": "ICD10"
                                        }
                                    ],
                                    "medication_authorisation": [
                                        {
                                            "authorisation_type": [
                                                {
                                                    #"|code": "at0074" # note of the item is refillable the code should be at0076
                                                    "|code": 'at0076' if prl.is_refillable else 'at0074'
                                                }
                                            ],
                                            "maximum_number_of_refills": [
                                            len([dis for dis in prl.mapped('prescription_detail_ids')]) #if prl.is_refillable else 0, #{total refills: type integer}
                                            ],
                                            "number_of_refills_issued": [
                                                len([
                                                    dis for dis in prl.mapped('prescription_detail_ids').filtered(lambda st: st.state == 'done')
                                                    ])
                                            ],
                                            "number_of_refills_remaining": [
                                                len([
                                                    dis for dis in prl.mapped('prescription_detail_ids').filtered(lambda st: st.state != 'done')
                                                    ]) 
                                            ],
                                            "minimum_interval_between_refills": [
                                                f"""P{prl.refill_duration or 0}{'W' if prl.refill_duration_unit == 'Weeks' else 'M' if prl.duration_period == 'Months' else 'D'}"""
                                            ],
                                            "next_refill_date": [
                                                f"{self.get_date_method(prl.mapped('prescription_detail_ids').filtered(lambda st: st.state != 'done')[0].date_refill_proposed if prl.mapped('prescription_detail_ids').filtered(lambda st: st.state != 'done') else False)}"
                                            ]
                                        }
                                    ],
                                    "dispense_directions": [
                                        {
                                            "dispense_instruction": [
                                                ""
                                            ],
                                            "dispensed_by": [
                                                f'{prl.prescription_id.dispenser.name or ""}'# .format(prl.prescription_id.dispenser.name)
                                            ],
                                            "dispensing_start_date": [
                                                f'{datetime.strftime(prl.create_date, "%Y-%m-%d")}' #'{}'.format(datetime.strftime(prl.prescription_detail_ids[0].date_refill_proposed, "%Y-%m-%d") if prl.prescription_detail_ids[0] and prl.prescription_detail_ids[0].date_refill_proposed else "")
                                            ],
                                        }
                                    ]
                                }
                            ],
                            "order_identifier": [
                                {
                                    "": ''.join(random.choice('abcdefghiklmo3peo32345699898rstuv') for _ in range(10)),
                                    "|issuer": "Issuer",
                                    "|assigner": "Assigner",
                                    "|type": "Prescription"
                                }
                            ],
                            "state": [
                                {
                                    "|code": f'''{'Dispensed' if prl.state == 'Dispensed' else 'Ordered'}''',
                                    "|value":  f"{'Dispensed' if prl.state == 'Dispensed' else 'Ordered'}"
                                } 
                            ],
                        } for prl in self.mapped('prescription_line')
                    ]
                }
        }
        return prescription_fhir_resource

class EvaluationVitalSigns(models.Model):

    _inherit = 'oeha.vitalsigns'

    migrated_to_emr = fields.Boolean(string='Migrated to EMR', copy=False)

    def _get_fhir_repr(self, operation=False):
        """Convert vital sign record to a fhir resource
        {
            "ctx/language": "en",
            "ctx/territory": "US",
            "ctx/composer_name": "{Name of the person that created the evaluation}", 
            "ctx/id_namespace": "HOSPITAL-NS",
            "ctx/id_scheme": "HOSPITAL-NS",
            "ctx/participation_name": "{Name of the nurse that worked on the encounter}",
            "ctx/participation_function": "requester",
            "ctx/participation_mode": "face-to-face communication",
            "ctx/participation_id": "199",
            "ctx/participation_name:1": "{{Name of the doctor that worked on the encounter}}",
            "ctx/participation_function:1": "performer",
            "ctx/participation_id:1": "198",
            "ctx/health_care_facility|name": "Hospital",
            "ctx/health_care_facility|id": "9091",
            "vital_signs/context/encounter_identifier/encounter_id": "Evaluation number",
            "vital_signs/blood_pressure/any_event:0/systolic|magnitude": 377.0,
            "vital_signs/blood_pressure/any_event:0/systolic|unit": "mm[Hg]",
            "vital_signs/blood_pressure/any_event:0/diastolic|magnitude": 575.0,
            "vital_signs/blood_pressure/any_event:0/diastolic|unit": "mm[Hg]",
            "vital_signs/blood_pressure/any_event:0/position|code": "at1014",
            "vital_signs/blood_pressure/location_of_measurement|code": "at0028",
            "vital_signs/blood_pressure/method|code": "at1036",
            "vital_signs/pulse_heart_beat/any_event:0/rate|magnitude": 560.0,
            "vital_signs/pulse_heart_beat/any_event:0/rate|unit": "/min",
            "vital_signs/pulse_heart_beat/any_event:0/regularity|code": "at0006",
            "vital_signs/pulse_heart_beat/any_event:0/irregular_type|code": "at0008",
            "vital_signs/pulse_heart_beat/any_event:0/clinical_description": "Clinical description 14",
            "vital_signs/body_temperature/any_event:0/temperature|magnitude": 17.3,
            "vital_signs/body_temperature/any_event:0/temperature|unit": "Cel",
            "vital_signs/pulse_oximetry/any_event:0/spo|numerator": the actual value from odoo,
            "vital_signs/pulse_oximetry/any_event:0/spo|denominator": 100.0,
            "vital_signs/respiration/any_event:0/rate|magnitude": 155.0,
            "vital_signs/respiration/any_event:0/rate|unit": "/min"
        }
        {
            "ctx/language": "en",
            "ctx/territory": "US",
            "ctx/composer_name": "Silvia Blake",
            "ctx/id_namespace": "HOSPITAL-NS",
            "ctx/id_scheme": "HOSPITAL-NS",
            "ctx/participation_name": "Dr. Marcus Johnson",
            "ctx/participation_function": "requester",
            "ctx/participation_mode": "face-to-face communication",
            "ctx/participation_id": "199",
            "ctx/participation_name:1": "Lara Markham",
            "ctx/participation_function:1": "performer",
            "ctx/participation_id:1": "198",
            "ctx/health_care_facility|name": "Hospital",
            "ctx/health_care_facility|id": "9091",
            "vital_signs/context/encounter_context/encounter_id": "Encounter Id 77",
            "vital_signs/context/encounter_context/date_created": "2023-04-27T06:51:10.412Z",
            "vital_signs/context/encounter_context/created_by": "Created by 13",
            "vital_signs/context/encounter_context/patient_name": "Patient name 2",
            "vital_signs/context/encounter_context/patient_id": "Patient ID 14",
            "vital_signs/context/encounter_context/membership_plan": "Membership plan 70",
            "vital_signs/context/encounter_context/membership_status": "Membership status 85",
            "vital_signs/context/encounter_context/admission_id": "Admission Id 8",
            "vital_signs/context/encounter_context/branch_code": "Branch code 94",
            "vital_signs/context/encounter_context/branch_name": "Branch name 72",
            "vital_signs/blood_pressure/any_event:0/systolic|magnitude": 275.0,
            "vital_signs/blood_pressure/any_event:0/systolic|unit": "mm[Hg]",
            "vital_signs/blood_pressure/any_event:0/diastolic|magnitude": 334.0,
            "vital_signs/blood_pressure/any_event:0/diastolic|unit": "mm[Hg]",
            "vital_signs/blood_pressure/any_event:0/position|code": "at1000",
            "vital_signs/blood_pressure/location_of_measurement|code": "at1021",
            "vital_signs/blood_pressure/method|code": "at1037",
            "vital_signs/pulse_heart_beat/any_event:0/rate|magnitude": 587.0,
            "vital_signs/pulse_heart_beat/any_event:0/rate|unit": "/min",
            "vital_signs/pulse_heart_beat/any_event:0/regularity|code": "at1028",
            "vital_signs/pulse_heart_beat/any_event:0/irregular_type|code": "at0007",
            "vital_signs/pulse_heart_beat/any_event:0/clinical_description": "Clinical description 59",
            "vital_signs/body_temperature/any_event:0/temperature|magnitude": 40.1,
            "vital_signs/body_temperature/any_event:0/temperature|unit": "Cel",
            "vital_signs/pulse_oximetry/any_event:0/spo|numerator": 13.97,
            "vital_signs/pulse_oximetry/any_event:0/spo|denominator": 100.0,
            "vital_signs/pulse_oximetry/any_event:0/spo|type": 2,
            "vital_signs/pulse_oximetry/any_event:0/inspired_oxygen/flow_rate|magnitude": 25679.61,
            "vital_signs/pulse_oximetry/any_event:0/inspired_oxygen/flow_rate|unit": "ml/min",
            "vital_signs/pulse_oximetry/any_event:0/inspired_oxygen/on_air": true,
            "vital_signs/pulse_oximetry/any_event:0/inspired_oxygen/method_of_oxygen_delivery:0|code": "at0001",
            "vital_signs/pulse_oximetry/any_event:0/inspired_oxygen/method_of_oxygen_delivery:0|value": "Nasal Cannula",
            "vital_signs/respiration/any_event:0/rate|magnitude": 50.0,
            "vital_signs/respiration/any_event:0/rate|unit": "/min",
            "vital_signs/respiration/any_event:0/regularity|code": "at0006",
            "vital_signs/respiration/any_event:0/clinical_description": "Clinical description 14"
        }
        
        """
        for vital_sign in self:
            vital_sign_as_a_fhir_resource = {
                "ctx/language": "en",
                "ctx/territory": "US",
                "ctx/composer_name": "{composer_name}".format(composer_name=vital_sign.create_uid.name),
                "ctx/id_namespace": "HOSPITAL-NS",
                "ctx/id_scheme": "HOSPITAL-NS",
                "ctx/participation_name": "{nurse_name}".format(nurse_name=vital_sign.evaluation_id.nurse.name),
                "ctx/participation_function": "requester",
                "ctx/participation_mode": "face-to-face communication",
                "ctx/participation_id": "199",
                "ctx/participation_name:1": "{doctor_name}".format(doctor_name=vital_sign.evaluation_id.care_provider.name),
                "ctx/participation_function:1": "performer",
                "ctx/participation_id:1": "198",
                "ctx/health_care_facility|name": "Hospital",
                "ctx/health_care_facility|id": "9091",
                "vital_signs/context/encounter_context/encounter_id": "{eval_no}".format(eval_no=vital_sign.evaluation_id.name),
                "vital_signs/context/encounter_context/date_created": "{create_date}".format(create_date=f"{vital_sign.create_date.isoformat()}"),
                "vital_signs/context/encounter_context/created_by": f"{vital_sign.create_uid.name}",
                "vital_signs/context/encounter_context/patient_name": f"{vital_sign.evaluation_id.patient and vital_sign.evaluation_id.patient.name or ''}",
                "vital_signs/context/encounter_context/patient_id": f"{vital_sign.evaluation_id.patient and vital_sign.evaluation_id.patient.identification_code or ''}",
                "vital_signs/blood_pressure/any_event:0/systolic|magnitude": "{systolic}".format(systolic=vital_sign.systolic),
                "vital_signs/blood_pressure/any_event:0/systolic|unit": "mm[Hg]",
                "vital_signs/blood_pressure/any_event:0/diastolic|magnitude": "{diastolic}".format(diastolic=vital_sign.diastolic),
                "vital_signs/blood_pressure/any_event:0/diastolic|unit": "mm[Hg]",
                "vital_signs/blood_pressure/any_event:0/position|code": "at1014",
                "vital_signs/blood_pressure/location_of_measurement|code": "at0028",
                "vital_signs/blood_pressure/method|code": "at1036",
                "vital_signs/pulse_heart_beat/any_event:0/rate|magnitude": "{heart_rate}".format(heart_rate=vital_sign.heart_rate),
                "vital_signs/pulse_heart_beat/any_event:0/rate|unit": "/min",
                "vital_signs/pulse_heart_beat/any_event:0/regularity|code": "at0006",
                "vital_signs/pulse_heart_beat/any_event:0/irregular_type|code": "at0008",
                "vital_signs/pulse_heart_beat/any_event:0/clinical_description": "Clinical description 14",
                "vital_signs/body_temperature/any_event:0/temperature|magnitude": "{temperature}".format(temperature=vital_sign.temp),
                "vital_signs/body_temperature/any_event:0/temperature|unit": "Cel",
                "vital_signs/pulse_oximetry/any_event:0/spo|numerator": "{pulse_oximetry}".format(pulse_oximetry=vital_sign.oxy_saturate),
                "vital_signs/pulse_oximetry/any_event:0/spo|denominator": 100.0,
                "vital_signs/respiration/any_event:0/rate|magnitude": "{respiratory}".format(respiratory=vital_sign.respiratory),
                "vital_signs/respiration/any_event:0/rate|unit": "/min"
            }
            return vital_sign_as_a_fhir_resource

    @api.model
    def _migrate_record_to_emr(self):
        vital_signs = self.search(
            [('migrated_to_emr', '=', False), ('evaluation_id.patient.ehr_id', '!=', False)],limit=2000).sorted(lambda r: r['create_date'], reverse=True)

        for vital_sign in sp(vital_signs):  # batch the records
            # url = https://dev-bettercare.eha.ng/ehr/rest/v1/composition?templateId=Vital Signs&ehrId={ehrId}&format=FLAT
            vital_sign.migrate_to_emr()

    def migrate_to_emr(self):
        for vital_sign in self:
            if vital_sign.migrated_to_emr:
                continue
            if not vital_sign.evaluation_id.patient.ehr_id:
                continue
            params = {}
            composition_url, template_id = self._get_composition_url_template()
            params['templateId'] = template_id
            params['ehrId'] = vital_sign.evaluation_id.patient.ehr_id
            params['format'] = "FLAT"
            parse_url = urlencode(params)
            target_url = f"{composition_url}?{parse_url}"
            resp = self.env['eha.emr.connector'].sudo(
            )._create_record(vital_sign, target_url, False)
            if resp:
                vital_sign.update({'migrated_to_emr': True})
                _logger.info(
                    f"====== vital_sign was created successfully ==========")
            if not resp:
                _logger.info(
                    f"========= vital_sign was not created ================")
            self.env.cr.commit()

    @api.model
    def _get_composition_url_template(self):
        """Get the composition url and template from system parameter
        """
        ICP = self.env['ir.config_parameter'].sudo()
        composition_url = ICP.get_param(
            'eha_oehealth_migration.composition_url', '')
        template_id = ICP.get_param(
            'eha_oehealth_migration.vital_signs_template_id', '')
        return composition_url, template_id


class EvaluationAllergies(models.Model):

    _inherit = 'oeha.evaluation.medication.allergies'

    migrated_to_emr = fields.Boolean(string='Migrated to EMR', copy=False)

    def _get_fhir_repr(self, operation=False):
        """Convert allergies record to a fhir resource
        {
            "ctx/language": "en",
            "ctx/territory": "US",
            "ctx/composer_name": "{Name of the person that created the evaluation}", 
            "ctx/id_namespace": "HOSPITAL-NS",
            "ctx/id_scheme": "HOSPITAL-NS",
            "ctx/participation_name": "{Name of the nurse that worked on the encounter}",
            "ctx/participation_function": "requester",
            "ctx/participation_mode": "face-to-face communication",
            "ctx/participation_id": "199",
            "ctx/participation_name:1": "{Name of the doctor that worked on the encounter}",
            "ctx/participation_function:1": "performer",
            "ctx/participation_id:1": "198",
            "ctx/health_care_facility|name": "Hospital",
            "ctx/health_care_facility|id": "9091",
            "allergies/context/encounter_identifier/date_created": "{create_date format: YYYY-mm-dd H:M:S}",
            "allergies/adverse_reaction_risk:0/substance|code": "90260006",
            "allergies/adverse_reaction_risk:0/substance|value": "Other substance",
            "allergies/adverse_reaction_risk:0/substance|terminology": "Allergens2",
            "allergies/adverse_reaction_risk:0/verification_status|code": "at0067",
            "allergies/adverse_reaction_risk:0/criticality|code": "at0124",
            "allergies/adverse_reaction_risk:0/category|code": "at0123",
            "allergies/adverse_reaction_risk:0/other_allergies": "{Cause of allergy}",
            "allergies/adverse_reaction_risk:0/reaction_event:0/manifestation:0|code": "74964007",
            "allergies/adverse_reaction_risk:0/reaction_event:0/manifestation:0|value": "Other",
            "allergies/adverse_reaction_risk:0/reaction_event:0/manifestation:0|terminology": "allergicReaction",
            "allergies/adverse_reaction_risk:0/reaction_event:0/onset_of_reaction": "2022-11-17T13:25:08.516Z",
            "allergies/adverse_reaction_risk:0/last_updated": "{write_date -  2022-11-17}",
        }
        """
        for allergy in self:
            allergy_as_a_fhir_resource = {
                "ctx/language": "en",
                "ctx/territory": "US",
                "ctx/composer_name": "{composer_name}".format(composer_name=allergy.create_uid.name),
                "ctx/id_namespace": "HOSPITAL-NS",
                "ctx/id_scheme": "HOSPITAL-NS",
                "ctx/participation_name": "{nurse_name}".format(nurse_name=allergy.evaluation_id.nurse.name),
                "ctx/participation_function": "requester",
                "ctx/participation_mode": "face-to-face communication",
                "ctx/participation_id": "199",
                "ctx/participation_name:1": "{doctor_name}".format(doctor_name=allergy.evaluation_id.care_provider.name),
                "ctx/participation_function:1": "performer",
                "ctx/participation_id:1": "198",
                "ctx/health_care_facility|name": "Hospital",
                "ctx/health_care_facility|id": "9091",
                "allergies/context/encounter_identifier/encounter_id": "{evaluation_name}".format(evaluation_name=allergy.evaluation_id.name),
                "allergies/context/encounter_identifier/date_created": "{create_date}".format(create_date=f"{allergy.create_date.isoformat()}"),
                "allergies/adverse_reaction_risk:0/substance|code": "90260006",
                "allergies/adverse_reaction_risk:0/substance|value": "Other substance",
                "allergies/adverse_reaction_risk:0/substance|terminology": "Allergens2",
                "allergies/adverse_reaction_risk:0/verification_status|code": "at0127",
                "allergies/adverse_reaction_risk:0/criticality|code": "at0124",
                "allergies/adverse_reaction_risk:0/category|code": "at0123",
                "allergies/adverse_reaction_risk:0/other_allergies": "{name}".format(name=allergy.name),
                "allergies/adverse_reaction_risk:0/reaction_event:0/manifestation:0|code": "74964007",
                "allergies/adverse_reaction_risk:0/reaction_event:0/manifestation:0|value": "Other",
                "allergies/adverse_reaction_risk:0/reaction_event:0/manifestation:0|terminology": "allergicReaction",
                "allergies/adverse_reaction_risk:0/reaction_event:0/onset_of_reaction": "2022-11-17T13:25:08.516Z",
                "allergies/adverse_reaction_risk:0/last_updated": f"{allergy.write_date:%Y-%m-%d}",
            }
            return allergy_as_a_fhir_resource

    @api.model
    def _migrate_record_to_emr(self):
        allergies = self.search(
            [('migrated_to_emr', '=', False), ('evaluation_id.patient.ehr_id', '!=', False)], limit=2000).sorted(lambda r: r['create_date'], reverse=True)

        for allergy in sp(allergies):  # batch the records
            allergy.migrate_to_emr()

    def migrate_to_emr(self):
        for allergy in self:
            _logger.info(
                f"***** Has allergy been migrated to emr? ****** {allergy.migrated_to_emr}")
            if allergy.migrated_to_emr:
                continue
            if not allergy.evaluation_id.patient.ehr_id:
                continue
            params = {}
            composition_url, template_id = self._get_composition_url_template()
            params['templateId'] = template_id
            params['ehrId'] = allergy.evaluation_id.patient.ehr_id
            params['format'] = "FLAT"
            parse_url = urlencode(params)
            target_url = f"{composition_url}?{parse_url}"
            resp = self.env['eha.emr.connector'].sudo(
            )._create_record(allergy, target_url, False)
            if resp:
                allergy.update({'migrated_to_emr': True})
                _logger.info(
                    f"====== allergy was created successfully ==========")
            if not resp:
                _logger.info(
                    f"========= allergy was not created ================")
            self.env.cr.commit()

    @api.model
    def _get_composition_url_template(self):
        """Get the composition url and template from system parameter
        """
        ICP = self.env['ir.config_parameter'].sudo()
        composition_url = ICP.get_param(
            'eha_oehealth_migration.composition_url', '')
        template_id = ICP.get_param(
            'eha_oehealth_migration.allergy_template_id', '')
        return composition_url, template_id
