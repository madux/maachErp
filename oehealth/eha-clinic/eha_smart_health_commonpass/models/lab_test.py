# -*- coding: utf-8 -*-
import pprint
import base64
from datetime import datetime, timedelta, timezone
from re import search
from io import BytesIO
from ..helpers import utils
from odoo import models, fields, api, _
from odoo.modules.module import get_module_resource, get_module_path

module_path = get_module_path('eha_smart_health_commonpass')

SMART_HEALTH_CARD_PREFIX = 'shc:/'

TEST_RESULT_CONCLUSION = {
    'negative': "No evidence of COVID-19 or Influenza infection on %s",
    'positive': "Evidence of COVID-19 or Influenza infection on %s",
    'invalid': "Invalid result on %s",
}


class LabTest(models.Model):
    _inherit = 'oeh.medical.lab.test'

    qr_code_commonpass = fields.Binary(string="CommonPass QR Code")

    def is_covid19_test(self):
        return self.test_type.is_covid_19

    def get_loinc_code(self):
        for record in self:
            test_loinc_code = ""
            loinc_codes = self.env['loinc.code'].search([])
            test_loinc_codes = loinc_codes.filtered(lambda code: record.test_type in code.eha_test_type_ids)
            if not test_loinc_codes:
                return test_loinc_code
            if len(test_loinc_codes) > 1:
                test_loinc_code = test_loinc_codes[0].name
            else:
                test_loinc_code = test_loinc_codes.name
            return test_loinc_code

    def get_timezone_aware_datetime(self):
        WAT = timezone(timedelta(hours=+1))
        t_now = datetime.utcnow() + timedelta(hours=1)
        t_now = t_now.replace(tzinfo=WAT)
        return t_now.isoformat()

    def generate_verifiable_credential(self):
        for labtest in self:
            issuer = labtest.env['ir.config_parameter'].sudo().get_param('eha_smart_health_commonpass.issuer_url') or labtest.env['ir.config_parameter'].sudo().get_param('web.base.url')
            provider_commonpass = labtest.env.ref('eha_smart_health_commonpass.smart_health_provider_commonpass')
            commonpass_sigining_key = provider_commonpass.private_key
            kid, private_signing_key = utils.get_signing_key_and_kid(commonpass_sigining_key, 'sig', 'ES256')
            patient_details = {
                "fullUrl": "resource:0",
                "resource": {
                    "resourceType": "Patient",
                    "name": [
                        {
                            "family": labtest.patient.lastname,
                            "given": [name for name in [labtest.patient.firstname, labtest.patient.lastname2] if name and name.strip()]
                        }
                    ],
                    "gender": labtest.patient.sex.lower(),
                    "birthDate": f"{labtest.patient.dob:%Y-%m-%d}",
                    "address": [
                        {
                            "postalCode": "12345",
                            "country": "US"
                        }
                    ]
                }
            }
            result = "invalid"
            result_interpretation = labtest.lab_test_criteria.filtered(
                lambda criterion: criterion.name.startswith('Result Interpretation'))
            if result_interpretation:
                if result_interpretation.result and result_interpretation.result.lower() == "negative":
                    result = 'negative'
                if result_interpretation.result and result_interpretation.result.lower() == "positive":
                    result = 'positive'

            diagnostic_report = {
                "fullUrl": "resource:1",
                "resource": {
                    "resourceType": "DiagnosticReport",
                    "status": "final",
                    "effectiveDateTime": labtest.get_timezone_aware_datetime(),
                    "subject": {
                        "reference": "resource:0"
                    },
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": labtest.get_loinc_code()
                            }
                        ]
                    },
                    "issued": labtest.get_timezone_aware_datetime(),
                    "performer": [
                        {
                            "display": "EHA Clinics"
                        }
                    ],
                    "result": [
                        {
                            "reference": "resource:2"
                        }
                    ],
                    "conclusion": TEST_RESULT_CONCLUSION[result] % f"{labtest.date_requested:%B %d, %Y}"
                }
            }
            observation = {
                "fullUrl": "resource:2",
                "resource": {
                    "resourceType": "Observation",
                    "status": "final",
                    "effectiveDateTime": self.get_timezone_aware_datetime(),
                    "subject": {
                        "reference": "resource:0"
                    },
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": labtest.get_loinc_code()
                            }
                        ]
                    },
                    "valueCodeableConcept": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "LA11883-8"
                            }
                        ]
                    }
                }
            }
            payload, fhir_bundle, credential_subject, verifiable_credential = {}, {}, {}, {}
            fhir_bundle["resourceType"] = "Bundle"
            fhir_bundle["type"] = "collection"
            fhir_bundle["entry"] = []
            fhir_bundle['entry'].append(patient_details)
            fhir_bundle['entry'].append(diagnostic_report)
            fhir_bundle['entry'].append(observation)
            credential_subject["fhirVersion"] = "4.0.1"
            credential_subject["fhirBundle"] = fhir_bundle
            verifiable_credential["type"] = [
                "https://smarthealth.cards#health-card",
                "https://smarthealth.cards#covid19",
                'https://smarthealth.cards#laboratory'
            ]
            verifiable_credential['credentialSubject'] = credential_subject
            payload["iss"] = issuer
            payload["nbf"] = round(labtest.date_requested.timestamp())
            payload["vc"] = verifiable_credential
            pprint.pprint(payload, compact=True)
            vc_jws = utils.encode_vc(payload, private_signing_key, kid)
            numeric_encoded_payload = utils.encode_to_numeric(vc_jws)
            img = utils.create_qr_code(numeric_encoded_payload)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            labtest.write({
                'qr_code_commonpass': img_str,
            })
        return True
