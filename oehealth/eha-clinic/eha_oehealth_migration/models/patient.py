# -*- coding: utf-8 -*-
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlencode
from odoo import models, fields, api
from ..tools.country import get_corresponding_country
from ..tools.splittor import splittor as sp
import logging
from datetime import date, datetime
_logger = logging.getLogger(__name__)

BLOOD_GROUP = {
    "O": "at0007",
    "A": "at0008",
    "B": "at0009",
    "AB": "at0010",
}

RHESUS_FACTOR = {
    "+": "at0011",
    "-": "at0012",
}


def get_unique_records(recs):
    print("&&&&&&&&& Records &&&&&&&&&&&&&&", recs)
    unique_records = {}
    for rec in recs:
        if not rec.name:
            continue
        if unique_records.get(rec.name):
            continue
        if any(rec.name.lower() in name.lower() or name.lower() in rec.name.lower() for name in unique_records):
            continue
        unique_records[rec.name] = rec
    return unique_records.values()


class OehealthPatient(models.Model):
    _inherit = 'oeh.medical.patient'

    migrate_to_emr = fields.Boolean(
        string='Should Be Migrated to EMR', copy=False)
    migrated_to_emr = fields.Boolean(string='Migrated to EMR', copy=False)
    migrated_past_medical_history_to_emr = fields.Boolean(
        string='Migrated Past History to EMR', copy=False)
    migrated_blood_group_to_emr = fields.Boolean(
        string='Migrated Blood Group to EMR', copy=False)
    migrated_allergies_to_emr = fields.Boolean(
        string='Migrated Allergies to EMR', compute="_compute_migrated_allergies_to_emr")
    ehr_id = fields.Char(
        string='EHR ID', help="This is the ID from EHR server", copy=False)
    demographics_id = fields.Char('Demographics ID', copy=False)
    allergy_ids = fields.Many2many(
        'oeha.evaluation.medication.allergies', string='Allergies', copy=False)
    
    @api.depends("allergy_ids.migrated_to_emr")
    def _compute_migrated_allergies_to_emr(self):
        for patient in self:
            migrated_allergies_to_emr = False
            if patient.allergy_ids:
                if all(patient.allergy_ids.mapped('migrated_to_emr')):
                    migrated_allergies_to_emr = True
            patient.migrated_allergies_to_emr = migrated_allergies_to_emr

    def _get_fhir_repr(self, operation=False):
        """Convert patient record to a patient fhir resource
        {
            resourceType: "Patient",
            active: true,
            identifier: [
                {
                system: 'EHA Clinics',
                value: 'HP0003',
                assigner: {
                    reference: "Organization/EHA Clinics"
                }
                }
            ],
            name: [
                {
                use: "usual",
                text: "Ameen, Ahmad Muhd",
                family: 'Ameen',
                given: [
                    "Ahmad", "Muhd"
                ],
                prefix: [
                    "Mrs"
                ]
                }
            ],
            address: [
                {
                city: "Kano",
                line: [
                    '19 Muhd Kumashi Street'
                ],
                text: "19 Muhd Kumashi Street, Nasarawa, Kano",
                type: "physical",
                use: "home",
                country: "Nigeria",
                state: "Nasarawa",

                }
            ],
            birthDate: "2000-01-01",
            gender: "female",
            maritalStatus: {
                coding: [
                {
                    code: "M",
                    display: "Married",
                    system: "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus"
                }
                ]
            },
            telecom: [
                {
                system: "phone",
                use: "home",
                value: "09068387166"
                },
                {
                system: "email",
                use: "home",
                value: "ahmadmameen7@gmail.com"
                },
                {
                system: "email",
                use: "work",
                value: "ahmadmameen@gmail.com"
                }
            ]
        }
        """
        for patient in self:
            patient_as_a_fhir_resource = None
            past_medical_history_sickle_cell = "Sickle Cell" if self.past_medical_history_sickle_cell else ""
            past_medical_history_diabetes = "Diabetes" if self.past_medical_history_diabetes else ""
            past_medical_history_hypertension = "Hypertension" if self.past_medical_history_hypertension else ""
            past_medical_history_epilepsy = "Epilepsy" if self.past_medical_history_epilepsy else ""
            past_medical_history_dyslipidemia = "Dyslipidemia" if self.past_medical_history_dyslipidemia else ""
            past_medical_history_tia = "TIA" if self.past_medical_history_tia else ""
            past_medical_history_stroke = "Stroke" if self.past_medical_history_stroke else ""
            past_medical_history_myocardial_infarction = "Myocardial infarction" if self.past_medical_history_myocardial_infarction else ""
            past_medical_history_dvt = "DVT" if self.past_medical_history_dvt else ""
            past_medical_history_surgeries = "Surgeries" if self.past_medical_history_surgeries else ""
            past_medical_history_asthma = "Asthma" if self.past_medical_history_asthma else ""
            other_medical_history = "Others" if self.other_medical_history else ""
            past_medical_history_copd = "COPD" if self.past_medical_history_copd else ""
            past_medical_history_immunization = "Immunization" if self.past_medical_history_immunization else ""
            past_medical_history_developmental_milestones = "Developmental milestones" if self.past_medical_history_developmental_milestones else ""

            patient_past_histories = [
                past_medical_history_sickle_cell, past_medical_history_diabetes,
                past_medical_history_hypertension, past_medical_history_epilepsy,
                past_medical_history_dyslipidemia, past_medical_history_stroke,
                past_medical_history_tia, past_medical_history_myocardial_infarction,
                past_medical_history_dvt, past_medical_history_surgeries,
                past_medical_history_surgeries, past_medical_history_asthma,
                other_medical_history, past_medical_history_copd,
                past_medical_history_immunization, past_medical_history_developmental_milestones,
            ] 
            if operation == "medical_history":
                joined_past_history_as_comma_separated = ','.join(list(filter(bool, patient_past_histories)))
                create_date = create_date = datetime.strftime(
                patient.create_date, "%Y-%m-%d") if patient.create_date else ""
                patient_as_a_fhir_resource = {
                    "ctx/language": "en",
                    "ctx/territory": "US",
                    "ctx/composer_name": "{composer_name}".format(composer_name=patient.create_uid.name), 
                    "ctx/id_namespace": "HOSPITAL-NS",
                    "ctx/id_scheme": "HOSPITAL-NS",
                    "ctx/participation_name": "{composer_name}".format(composer_name=patient.create_uid.name),
                    "ctx/participation_function": "requester",
                    "ctx/participation_mode": "face-to-face communication",
                    "ctx/participation_id": "199",
                    "ctx/participation_name:1": "{composer_name}".format(composer_name=patient.create_uid.name),
                    "ctx/participation_function:1": "performer",
                    "ctx/participation_id:1": "198",
                    "ctx/health_care_facility|name": "Hospital",
                    "ctx/health_care_facility|id": "9091",
                    "past_medical_history/context/encounter_context/encounter_id": "",
                    "past_medical_history/context/encounter_context/date_created": "{created_date}".format(created_date=create_date),
                    "past_medical_history/problem_diagnosis/problem_diagnosis_name:0|code": "Others",
                    "past_medical_history/problem_diagnosis/problem_diagnosis_name:0|value": "Others",
                    "past_medical_history/problem_diagnosis/problem_diagnosis_name:0|terminology": "ICD10",
                    "past_medical_history/problem_diagnosis/clinical_description": joined_past_history_as_comma_separated,
                    "past_medical_history/problem_diagnosis/date_recognised": "{created_date}".format(created_date=create_date),
                }
                return patient_as_a_fhir_resource

            if operation == "blood_group":
                patient_as_a_fhir_resource = {
                    "ctx/language": "en",
                    "ctx/territory": "US",
                    "ctx/composer_name": "{created_by}".format(created_by=patient.create_uid.name),
                    "ctx/id_namespace": "HOSPITAL-NS",
                    "ctx/id_scheme": "HOSPITAL-NS",
                    "ctx/participation_name": "{nurse_name}".format(nurse_name=patient.create_uid.name),
                    "ctx/participation_function": "requester",
                    "ctx/participation_mode": "face-to-face communication",
                    "ctx/participation_id": "199",
                    "ctx/participation_name:1": "{care_provider}".format(care_provider=patient.create_uid.name),
                    "ctx/participation_function:1": "performer",
                    "ctx/participation_id:1": "198",
                    "ctx/health_care_facility|name": "Hospital",
                    "ctx/health_care_facility|id": "9091",
                    "blood_group/blood_group/abo_blood_group|code": BLOOD_GROUP.get(patient.blood_type),
                    "blood_group/blood_group/rh_d_antigen_status|code": RHESUS_FACTOR.get(patient.rh),
                    "blood_group/blood_group/last_updated": "{write_date}".format(write_date=patient.write_date.isoformat())
                }
                return patient_as_a_fhir_resource

            patient_as_a_fhir_resource = {
                "resourceType": "Patient",
                "identifier": [
                    {
                        "system": "EHA Clinics",
                        "value": f"{patient.identification_code}",
                        "assigner": {
                            "reference": "Organization/EHA Clinics"
                        }
                    }
                ],
                "active": True,
                "name": [
                    {
                        "use": "usual",
                        "family": f"{patient.lastname}",
                        "given": [
                            f"{patient.firstname}"
                        ],
                        "prefix": [
                            f"{patient.partner_id.title and patient.partner_id.title.name.title() or ''}"
                        ],
                        'text': f"{patient.lastname}, {patient.firstname} {patient.lastname2 or ''}"
                    }
                ],
                "gender": f"{patient.sex and patient.sex.lower() or ''}",
                "birthDate": f"{patient.dob:%Y-%m-%d}",
                "address": [
                    {
                        "use": "old",
                        "type": "postal",
                        "line": [
                            f"{patient.street}"
                        ],
                        "city": f"{patient.city}",
                        "state": f"{patient.state_id.name}",
                        "postalCode": f"{patient.zip}",
                        "country": f"{patient.country_id.name and get_corresponding_country(patient.country_id.name)}"
                    }
                ],
                "maritalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                            "code": f"{patient.marital_status and patient.marital_status[0].upper()}",
                            "display": f"{patient.marital_status}"
                        }
                    ]
                },
                "telecom": [
                    {
                        "system": "phone",
                        "use": "home",
                        "value": f"{patient.phone}"
                    },
                    {
                        "system": "email",
                        "use": "home",
                        "value": f"{patient.email}"
                    },
                    {
                        "system": "email",
                        "use": "work",
                        "value": f"{patient.email}"
                    }
                ]
            }
            return patient_as_a_fhir_resource

    def oeh_medical_patient_update_record_with_response(self, response, operation=None):
        """Get the response from the creation of patient demographics record and update the patient record with it.
        """
        for patient in self:
            if operation != "patient":
                continue
            demographics_id = response.get("id")
            patient.write({'demographics_id': demographics_id})

    def _create_oeh_medical_patient_additional_info(self, operation=None):
        """After creating the patient info on demographics server, also create an ehr id on the ehr server
        """
        for patient in self:
            if not operation == 'patient':
                return True
            ICP = self.env['ir.config_parameter'].sudo()
            ehr_url = ICP.get_param("eha_emr_connector.ehr_url", "")
            username = ICP.get_param("eha_emr_connector.ehr_username", "")
            password = ICP.get_param("eha_emr_connector.ehr_password", "")
            namespace = ICP.get_param("eha_emr_connector.namespace", "")
            if not all([ehr_url, username, password, namespace]):
                return False
            subject = patient.identification_code
            basic = HTTPBasicAuth(
                username, password)
            payload = {
                'subjectId': subject,
                'subjectNamespace': namespace
            }
            res = requests.post(
                url=ehr_url, auth=basic, params=payload, verify=False)
            _logger.info(
                f"&&&&& Response of ehrid creation &&&&&& {res}, {res.json()}")
            if res.status_code == 201:
                self.ehr_id = res.json()['ehrId']
                return True
            return False

    @api.model
    def _migrate_patient_to_emr(self):
        """Run scheduler to process records to be migrated
        """
        patients = self.search(
            [('migrate_to_emr', '=', True), ('migrated_to_emr', '=', False)])
        _logger.info(
            f"&&&&&&&&&&& patients to migrate &&&&&&&&&&&&& {patients}")

        for patient in sp(patients):  # batch the records
            patient.migrate_patient_to_emr()

    def migrate_patient_to_emr(self):
        for patient in self:
            if patient.migrated_to_emr:
                continue
            target_url = self._get_demographics_url()
            resp = self.env['eha.emr.connector'].sudo(
            )._create_record(patient, target_url, operation="patient")
            if resp:
                patient.update({'migrated_to_emr': True})
                _logger.info(
                    f"====== Patient was created successfully ==========")
            if not resp:
                _logger.info(
                    f"========= Patient was not created ================")
            self.env.cr.commit()

    @api.model
    def _migrate_past_medical_history_to_emr(self):
        """Run scheduler to process records to be migrated
        """
        patients = self.search(
            [('migrate_to_emr', '=', True), ('migrated_past_medical_history_to_emr', '=', False)])
        _logger.info(
            f"&&&&&&&&&&& Patients to migrate past history &&&&&&&&&&&&& {patients}")
        for patient in sp(patients):  # batch the records
            patient.migrate_past_medical_history_to_emr()

    def migrate_past_medical_history_to_emr(self):
        for patient in self:
            if patient.migrated_past_medical_history_to_emr:
                continue
            params = {}
            composition_url = self._get_composition_url()
            template_id = self._get_past_medical_history_template()
            params['templateId'] = template_id
            params['ehrId'] = patient.ehr_id
            params['format'] = "FLAT"
            target_url = f"{composition_url}?{urlencode(params)}"
            resp = self.env['eha.emr.connector'].sudo(
            )._create_record(patient, target_url, 'medical_history')
            if resp:
                patient.update({'migrated_past_medical_history_to_emr': True})
                _logger.info(
                    f"====== past medical history was created successfully ==========")
            if not resp:
                _logger.info(
                    f"========= past medical history was not created ================")
            self.env.cr.commit()

    # Blood group migration
    @api.model
    def _migrate_blood_group_to_emr(self):
        """Run scheduler to process records to be migrated
        """
        patients = self.search(
            [('migrate_to_emr', '=', True), ('migrated_blood_group_to_emr', '=', False),
             ('rh', '!=', False),('blood_type', '!=', False)], limit=2000)
        _logger.info(
            f"&&&&&&&&&&& Patients to migrate blood group &&&&&&&&&&&&& {patients}")

        for patient in sp(patients):  # batch the records
            patient.migrate_blood_group_to_emr()

    def migrate_blood_group_to_emr(self):
        for patient in self:
            if patient.migrated_blood_group_to_emr:
                continue
            params = {}
            composition_url = self._get_composition_url()
            template_id = self._get_blood_group_template()
            params['templateId'] = template_id
            params['ehrId'] = patient.ehr_id
            params['format'] = "FLAT"
            target_url = f"{composition_url}?{urlencode(params)}"
            resp = self.env['eha.emr.connector'].sudo(
            )._create_record(patient, target_url, 'blood_group')
            if resp:
                patient.update({'migrated_blood_group_to_emr': True})
                _logger.info(
                    f"====== Blood group was created successfully ==========")
            if not resp:
                _logger.info(
                    f"========= Blood group was not created ================")
            self.env.cr.commit()

    # Migrate allergies to emr
    @api.model
    def _migrate_allergies_to_emr(self):
        """Run scheduler to process records to be migrated
        """
        patients = self.search(
            [('migrate_to_emr', '=', True), ('migrated_allergies_to_emr', '=', False)])
        _logger.info(
            f"&&&&&&&&&&& Patients to migrate allergies &&&&&&&&&&&&& {patients}")

        for patient in sp(patients):  # batch the records
            patient.migrate_allergies_to_emr()

    def migrate_allergies_to_emr(self):
        """Migrate all the allergies of a particular patient to emr.

        How this would work is that we would get all evaluations for the patient and get all allergies
        related to the evaluations. We will filter to get unique allergies and remove the duplicates. It is
        the unique allergies that would be migrated to EMR. Once all these allergies are migrated, the patient would be considered to have their allergies migrated. 
        """
        for patient in self:
            if patient.migrated_blood_group_to_emr:
                continue
            related_allergies = patient.evaluation_ids.medication_allergies_ids
            if not related_allergies:
                continue
            unique_related_allergy_ids = get_unique_records(related_allergies)
            for allergy_id in unique_related_allergy_ids:
                if allergy_id not in patient.allergy_ids:
                    patient.allergy_ids += allergy_id

            for allergy in patient.allergy_ids:
                allergy.migrate_to_emr()

    @api.model
    def _get_demographics_url(self):
        """Get the Demographics url from system parameter
        """
        ICP = self.env['ir.config_parameter'].sudo()
        demographics_url = ICP.get_param(
            'eha_emr_connector.demographics_url', '')
        return demographics_url

    def _get_blood_group_template(self):
        ICP = self.env['ir.config_parameter'].sudo()
        template_id = ICP.get_param(
            'eha_oehealth_migration.blood_group_template_id', '')
        return template_id

    def _get_past_medical_history_template(self):
        ICP = self.env['ir.config_parameter'].sudo()
        template_id = ICP.get_param(
            'eha_oehealth_migration.past_medical_history_template_id', '')
        return template_id

    def _get_composition_url(self):
        ICP = self.env['ir.config_parameter'].sudo()
        composition_url = ICP.get_param(
            'eha_oehealth_migration.composition_url', '')
        return composition_url
