import requests
import json
from re import search
from ast import literal_eval
from requests.adapters import HTTPAdapter
# from requests.packages.urllib3.util.retry import Retry
from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)

# retry_strategy = Retry(
#     total=3,
#     status_forcelist=[429, 500, 502, 503, 504],
#     method_whitelist=["POST", "HEAD", "GET", "OPTIONS"]
# )
# adapter = HTTPAdapter(max_retries=retry_strategy)
# http = requests.Session()
# http.mount("https://", adapter)
# http.mount("http://", adapter)

# DOMAIN = [
#     ('test_type.allow_panabios_sync', '=', True),
#     ('state', 'in', ['Completed', 'Reviewed']),
#     ('panabios_sent_status', '=', False)
# ]
# OFFSET = 0
# LIMIT = 1000

# TOKEN_LINK = "{}/api/external/obtain_access_token/"
# SEAL_LINK = "{}/api/external/lab/lab_test/seal/generate/"
# DATE_STR_FORMAT = "%Y-%m-%d"


class PanabiosConnector(models.Model):
    _name = "panabios.connector"
    _description = "Panabios Connector"

    @api.model
    def cron_sync_to_panabios(self):
        pass
    #     base_url = self.env['ir.config_parameter'].sudo().get_param('eha_connector.panabios_api_url') or ''
    #     token_link = TOKEN_LINK.format(base_url)
    #     seal_link = SEAL_LINK.format(base_url)
    #     domain = DOMAIN
    #     tests_to_sync = self.env['oeh.medical.lab.test'].sudo().search(domain, OFFSET, LIMIT)
    #     ALLOWED_COUNTRIES = self.env['ir.config_parameter'].sudo().get_param(
    #         'eha_connector.panabios_allowed_countries') and literal_eval(
    #         self.env['ir.config_parameter'].sudo().get_param('eha_connector.panabios_allowed_countries')) or ()
    #     ALLOWED_AIRLINES = self.env['ir.config_parameter'].sudo().get_param(
    #         'eha_connector.panabios_allowed_airliners') and literal_eval(
    #         self.env['ir.config_parameter'].sudo().get_param('eha_connector.panabios_allowed_airliners')) or ()
    #     if self.env['ir.config_parameter'].sudo().get_param('eha_connector.panabios_sync_start_date'):
    #         tests_to_sync.filtered(lambda test: test.create_date >= fields.Datetime.from_string(
    #             self.env['ir.config_parameter'].sudo().get_param('eha_connector.panabios_sync_start_date')))
    #     tests_to_sync = tests_to_sync.filtered(lambda test: test.cif_ref).filtered(
    #         lambda test: test.cif_ref.flight and test.cif_ref.destination).filtered(
    #         lambda test: any(search(test.cif_ref.flight.lower(), airline.lower()) for airline in ALLOWED_AIRLINES) or test.cif_ref.destination in ALLOWED_COUNTRIES)
    #     panabios_username = self.env['ir.config_parameter'].sudo().get_param('eha_connector.panabios_username')
    #     panabios_password = self.env['ir.config_parameter'].sudo().get_param('eha_connector.panabios_password')
    #     if not tests_to_sync:
    #         _logger.info("No test result to sync")
    #         return
    #     for test in tests_to_sync:
    #         payload = {
    #             "patient_info": {
    #                 "first_name": test.patient.firstname,
    #                 "last_name": test.patient.lastname,
    #                 "gender": test.patient.sex[0],
    #                 "date_of_birth": test.patient.dob.strftime(DATE_STR_FORMAT),
    #                 "age": test.patient.age_int,
    #                 "age_unit": "Y",
    #                 "email": test.patient.email or test.patient.secondary_email,
    #                 "dial_code": test.patient.country_id.phone_code or "234",
    #                 "phone_number": (lambda phone, code=None: phone.strip(str(code)))(
    #                     phone=test.patient.phone if test.patient.phone else test.patient.mobile,
    #                     code=test.patient.country_id.phone_code),
    #                 "nationality": test.patient.country_id.name,
    #                 "occupation": test.patient.function or "Business",
    #             },
    #             "user_port_health_info": {
    #                 "departure_country": test.cif_ref.depature_country or "Nigeria",
    #                 "destination_country": test.cif_ref.destination,
    #                 "flight_number": str(test.cif_ref.flight),
    #                 "national_id_number": str(test.cif_ref.id_card),
    #             },
    #             "samples": [
    #                 {
    #                     "sample_code": "",
    #                     "sample_name": "NP SWAB",
    #                     "sample_result": criterion.result and criterion.result.capitalize() or "",
    #                     "remark": test.interpretation,
    #                     "test_kit_serial_number": "",
    #                     "external_sample_number": test.name,
    #                     "date_received_in_lab": test.sample_collection_date.date().strftime(DATE_STR_FORMAT),
    #                     "date_of_collection": test.sample_collection_date.date().strftime(DATE_STR_FORMAT)
    #                 }
    #                 for criterion in test.lab_test_criteria.filtered(
    #                     lambda criterion: criterion.name.startswith('Result Interpretation')) if criterion.result
    #             ],
    #             "lab_test_info": {
    #                 "name": test.name,
    #                 "market": test.cif_ref.country_id.name,
    #                 "lonic_code": "94563-4",
    #                 "date_taken": test.date_requested.strftime(DATE_STR_FORMAT),
    #                 "case_type": "Initial",
    #                 "reason_for_testing": "Air Travel"
    #             }
    #         }
    #         is_success = False
    #         error = []
    #         response_code = False
    #         response_message = []
    #         try:
    #             response = http.post(
    #                 token_link,
    #                 data={
    #                     "username": panabios_username,
    #                     "password": panabios_password,
    #                 },
    #                 timeout=10
    #             )
    #             access_token = response.json()["token"]
    #             response_code = response.status_code
    #         except KeyError:
    #             error.append(f"Token not found")
    #             response_message.append("Invalid credentials")
    #         else:
    #             is_success = False
    #             try:
    #                 response = http.post(seal_link, json=payload, headers={"Authorization": f"Token {access_token}"},
    #                                      timeout=20)
    #                 response_code = response.status_code
    #             except Exception as e:
    #                 _logger.error(f"The following error occurred when trying to generate a seal: {e}")
    #                 error.append(e)
    #             finally:
    #                 if response.status_code in (200, 201):
    #                     _logger.info(f"The following seal was generated for test {test.name}: \n {response.json()}")
    #                     _logger.info(f"Panabios upload success for test {test.name}")
    #                     is_success = True
    #                     test.write({
    #                         'panabios_sent_status': True,
    #                     })
    #                     response_message.append(json.dumps(response.json().get("status", "")))
    #                 else:
    #                     error.extend(response.json().get("errors"))
    #                     response_message.append(json.dumps(response.json().get("errors")))
    #                     _logger.error(
    #                         f"Panabios upload did not complete successfully for test {test.name}\nReturned with error {response.json()}")
    #         finally:
    #             PanabiosLog = self.env['panabios.log'].sudo()
    #             log_instance = PanabiosLog.search([('labtest_no', '=', test.name)])
    #             if log_instance:
    #                 log_instance.sudo().write({
    #                     'is_success': is_success,
    #                     'date_attempted': fields.Datetime.now(),
    #                     "response_code": response_code and int(response_code) or False,
    #                     "response_message": ",".join(response_message)
    #                 })
    #             else:
    #                 PanabiosLog.create({
    #                     "name": test.name,
    #                     "labtest_no": test.name,
    #                     "response_code": response_code and int(response_code) or False,
    #                     "response_message": ",".join(response_message),
    #                     "is_success": is_success,
    #                     "date_attempted": fields.Datetime.now()
    #                 })
