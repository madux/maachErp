from odoo import api, fields, models

import logging

#Get the logger
_logger = logging.getLogger(__name__)

class SaleOrderAlert(models.Model):
    _inherit = 'sale.order.alert'
    action = fields.Selection(selection_add=[('sms', 'Send an sms to the customer')])
    sms_message = fields.Text('Message Template', help="you can access name, phone, date, days by using {} e.g {name} -> the client name")
    sales_message = fields.Text('SalePerson Message',help="you can access name, phone, date, days by using {} e.g {name} -> the client name")

    """if records: 
            action = records.send_sms()
            log(model, level='info')
            log(self, level='info')
            log(records, level='info')"""