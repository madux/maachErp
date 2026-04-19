from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class SmsLog(models.Model):
    _name="sms.log"
    _description = "SMS Log"

    model = fields.Char('Model',readonly=True)
    ref = fields.Char('Name', readonly=True)
    phone = fields.Char('Mobile No.', readonly=True)
    response_message = fields.Text('Response Message',readonly=True)
    text_message = fields.Text('Text Message',readonly=True)
    date_attempted = fields.Datetime(default=fields.Datetime.now())
    # date_started = fields.Date(default=fields.Date.today(), help='technical field used to implement labtest result sms start date')
    # gateway_id = fields.Many2one('gateway_setup', string='GateWay',readonly=True)

