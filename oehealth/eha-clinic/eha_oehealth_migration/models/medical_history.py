from odoo import models, fields, api
from datetime import datetime
from urllib.parse import urlencode
from ..tools.splittor import splittor as sp
import logging
from odoo.exceptions import ValidationError
import pprint
pp = pprint.PrettyPrinter(indent=4)
_logger = logging.getLogger(__name__)


class OehealthMedicalHistory(models.Model):
    _inherit = "oeh.medical.history"

    def migrate_mh_artifacts_to_emr(self):
        for mh in self:
            mh.migrate_medical_history_to_emr()

    def _get_fhir_repr(self, operation=False):
        """Convert Medical History record to a fhir resource
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
            "surgical_history/context/encounter_context/encounter_id": "{Evaluation number}",
            "surgical_history/context/encounter_context/date_created": "{create_date}",
            "surgical_history/procedure/procedure_name|code": "Others",
            "surgical_history/procedure/procedure_name|value": "Others",
            "surgical_history/procedure/procedure_name|terminology": "ICD10",
            "surgical_history/procedure/outcome:0": "{csv of surgery type and outcome}",
            "surgical_history/procedure/date_of_surgery": "{Date of surgery}",

        }
        """
        for medhis in self:
            surgery_type_outcome = f"Type: {medhis.type_of_surgery}, Outcome: {medhis.outcome_of_surgery}"
            create_date = datetime.strftime(
                medhis.create_date, "%Y-%m-%d") if medhis.create_date else ""
            date_of_surgery = datetime.strftime(
                medhis.date_of_surgery, "%Y-%m-%d") if medhis.date_of_surgery else ""
            _logger.info(f'OUTCOME EXAMPLE: {surgery_type_outcome}')
            medhis_as_a_fhir_resource = {
                "ctx/language": "en",
                "ctx/territory": "US",
                "ctx/composer_name": "{composer_name}".format(composer_name=medhis.create_uid.name), 
                "ctx/id_namespace": "HOSPITAL-NS",
                "ctx/id_scheme": "HOSPITAL-NS",
                "ctx/participation_name": "{composer_name}".format(composer_name=medhis.create_uid.name),
                "ctx/participation_function": "requester",
                "ctx/participation_mode": "face-to-face communication",
                "ctx/participation_id": "199",
                "ctx/participation_name:1":"{composer_name}".format(composer_name=medhis.create_uid.name),
                "ctx/participation_function:1": "performer",
                "ctx/participation_id:1": "198",
                "ctx/health_care_facility|name": "Hospital",
                "ctx/health_care_facility|id": "9091",
                "surgical_history/context/encounter_context/encounter_id": "",
                "surgical_history/context/encounter_context/date_created": "{create_date}".format(create_date=create_date),
                "surgical_history/procedure/procedure_name|code": "Others",
                "surgical_history/procedure/procedure_name|value": "Others",
                "surgical_history/procedure/procedure_name|terminology": "ICD10",
                "surgical_history/procedure/outcome:0": surgery_type_outcome or "",
                "surgical_history/procedure/date_of_surgery": "{date_of_surgery}".format(date_of_surgery=date_of_surgery),
            }
            fhir_resource = medhis_as_a_fhir_resource
            pp.pprint(fhir_resource)
            return fhir_resource

    @api.model
    def _migrate_record_to_emr(self, operation):
        if operation == "medical_history":
            return self._migrate_medical_history_to_emr()

    def _migrate_medical_history_to_emr(self):
        medhis = self.search([
            ('migrated_medical_history_to_emr', '=', False), 
            ('patient_id.ehr_id', '!=', False)
            ]).sorted(lambda r: r['create_date'], reverse=True)
        for mh in sp(medhis):
            mh.migrate_medical_history_to_emr()

    def migrate_medical_history_to_emr(self):
        for mh in self:
            if mh.migrated_medical_history_to_emr:
                continue
            if not mh.patient_id.ehr_id:
                continue
            params = {}
            composition_url, template_id = self._get_composition_url_template(
                "medical_history")

            # https://dev-bettercare.eha.ng/ehr/rest/v1/composition?templateId=Surgical History&ehrId={{ehrId}}&format=FLAT
            params['templateId'] = template_id
            params['ehrId'] = mh.patient_id.ehr_id
            params['format'] = "FLAT"
            parse_url = urlencode(params)
            target_url = f"{composition_url}?{parse_url}"
            resp = self.env['eha.emr.connector'].sudo(
            )._create_record(mh, target_url, "evaluation")
            if resp:
                mh.update({'migrated_medical_history_to_emr': True})
                _logger.info(
                    f"====== Medical history was migrated successful ==========")
            if not resp:
                _logger.info(
                    f"========= Medical history was migrated was not created ================")
            self.env.cr.commit()

    @api.model
    def _get_composition_url_template(self, operation=None):
        """Get the composition url and template from system parameter
        """
        ICP = self.env['ir.config_parameter'].sudo()
        template_id = None
        composition_url = ICP.get_param(
            "eha_oehealth_migration.composition_url", '')
        if operation == "medical_history":
            template_id = ICP.get_param(
                "eha_oehealth_migration.medical_history_template_id", "")
        return composition_url, template_id

