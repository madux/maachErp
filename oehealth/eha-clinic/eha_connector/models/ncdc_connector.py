from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
# from odoo.addons.eha_auth.controllers.helpers import convert_date_to_iso, convert_time, tolocale_time
import requests
import json
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import dateutil.parser as parser
_logger = logging.getLogger(__name__)

class NcdcConnector(models.TransientModel):
	_name = "ncdc.connector"
	_description = "Covid19 records Sync"

	def get_unsent_labtest_records(self, offset=0, limit=10000):
		pass 
		# dt_str = parser.parse("2021-09-16 19:00:00").strftime(DEFAULT_SERVER_DATETIME_FORMAT)
		# domain = [
		# 	('create_date', '>', dt_str),
		# 	('test_type.allow_ncdc_sync', '=', True),
		# 	('state', 'in', ['Completed', 'Reviewed']),
		# 	('ncdc_sent_status', '=', False),
		# 	('ncdc_retry_count', '<', 4)
		# ]
		# records = self.env['oeh.medical.lab.test'].sudo().search(domain, offset, limit)
		# return records

	def push_to_ncdc(self):
		pass 
		# offset = int(self.env['ir.config_parameter'].sudo().get_param('eha_connector.ncdc_sync_offset'))
		# limit = int(self.env['ir.config_parameter'].sudo().get_param('eha_connector.ncdc_sync_limit'))
		# ncdc_username = self.env['ir.config_parameter'].sudo().get_param('eha_connector.ncdc_login_username')
		# ncdc_password = self.env['ir.config_parameter'].sudo().get_param('eha_connector.ncdc_login_password')
		# records = self.get_unsent_labtest_records(offset=offset, limit=limit)
		# for record in records:
		# 	try:
		# 		_logger.info("[*] Syncing %s" %record.name)
		# 		result_interpretation = record.mapped('lab_test_criteria').filtered(lambda name: name.name.startswith('Result Interpretation'))
		# 		payload = { "test_id" : record.ncdc_test_id if record.ncdc_test_id else 0,
		# 			"passport_no" : record.patient.passport_no if record.patient.passport_no else None,
		# 			"first_name" : record.patient.firstname,
		# 			"last_name" : record.patient.lastname,
		# 			"other_names" : record.patient.lastname2 if record.patient.lastname2 else None,
		# 			"cert_no" : record.ncdc_cert_number,
		# 			"result_status" : result_interpretation[0].result if result_interpretation else '',
		# 			"sampling_date" : convert_date_to_iso(fields.Datetime.to_string(record.sample_collection_date)) if record.sample_collection_date else convert_date_to_iso(fields.Datetime.to_string(record.date_requested)),
		# 			"sampling_time" : convert_time(tolocale_time(record.sample_collection_date).split(' ')[1] if record.sample_collection_date else tolocale_time(record.date_requested).split(' ')[1]),
		# 			"test_name" : record.test_type.name,
		# 			"methodology" : "Real-Time PCR" if "RDT" not in str(record.test_type.code).split(" ") else "Rapid Diagnostic Test",
		# 			"sample_type" : "Nasopharyngeal Swab",
		# 			"test_purpose" : "Other Reasons" if record.cif_ref else "Travel Requirement",
		# 			"gender" : record.patient.sex,
		# 			"age" : ' '.join(str(record.patient.age).split(' ')[:2]),
		# 			"email" : record.patient.email if record.patient.email else record.patient.secondary_email,
		# 			"phone" : record.patient.phone if record.patient.phone else record.patient.mobile,
		# 			"access_key" : "{}&{}".format(ncdc_username, ncdc_password)
		# 		}

		# 		res = requests.post('https://rv.ncdc.gov.ng/Verify/PushResult', data=payload, timeout=60)
		# 		res_json = res.json()

		# 		values = {
		# 			"labtest_no": record.name,
		# 			"response_code": res.status_code,
		# 			"response_message": res_json.get("feedback")
		# 		}
		# 		#'feedback': 'Certificate Number Already Exists'
		# 		if res_json.get("is_success") or res_json.get('feedback','').lower() == "certificate number already exists":
		# 			_logger.info("[*] Report push status: Success")
		# 			values["is_success"] = True
		# 			record.write({"ncdc_sent_status": True, "ncdc_test_id":res_json.get("test_id")})
		# 		else:
		# 			_logger.info("[*] Report push status: Failed %s" %res_json)
		# 			current_retry_count = record.ncdc_retry_count
		# 			record.write({"ncdc_retry_count": current_retry_count+1})
				
		# 		log_instance = self.env['ncdc.log'].sudo().search([('labtest_no', '=', record.name)])
		# 		if log_instance:
		# 			values["date_attempted"] = datetime.now()
		# 			log_instance.sudo().write(values)
		# 		else:
		# 			self.env['ncdc.log'].sudo().create(values)
		# 	except Exception as ex:
		# 		_logger.exception(ex)
		# 		_logger.info("[*] NCDC Upload Error Occured! %s" %ex)

	def cron_sync_covid19_result(self):
		self.push_to_ncdc()
