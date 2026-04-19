from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import requests
import json
from requests.auth import HTTPBasicAuth

_logger = logging.getLogger(__name__)

class BulkSms(models.Model):
    _name="bulk.sms"
    _description = "SMS Log"

    def _send_sms(self, phone_numbers, text):
        ''' send SMS using bulk sms api 
            sample data:
            {
                "to": ["+27001234567", "+27002345678", "+27003456789"],
                "body": "Happy Holidays!"
            }
        '''

        if type(phone_numbers) is not list:
            raise ValueError(_("args phone_numbers MUST be a list"))

        url = self.env['ir.config_parameter'].sudo().get_param('bulksms.api')
        token_id = self.env['ir.config_parameter'].sudo().get_param('bulksms.token.id')
        token_secret = self.env['ir.config_parameter'].sudo().get_param('bulksms.token.secret')
        headers = {"Content-Type": "application/json"}
        vals = {
            "to": phone_numbers,
            "body": text
        }
        data = json.dumps(vals)

        try:
            req = requests.post(url, data=data, headers=headers, auth=HTTPBasicAuth(token_id, token_secret), timeout=15)
            _logger.info('data %s' % req)
            resp = {'status': req.status_code, 'text': req.text}
            return resp
        except Exception as ex:
            _logger.exception(ex)
            raise UserError(_('BulkSMS Error: {}'.format(ex.args[0])))
        