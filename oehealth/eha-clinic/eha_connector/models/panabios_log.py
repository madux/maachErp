from odoo import models, fields


class PanabiosLog(models.Model):
    _name = "panabios.log"
    _description = "Panabios Log"

    name = fields.Char(string="Panabios Log")
    labtest_no = fields.Char(string="LT Number", readonly=True)
    response_code = fields.Integer(string="Response Code", readonly=True)
    response_message = fields.Text(string="Response Message", readonly=True)
    is_success = fields.Boolean(string="Is success", default=False, readonly=True)
    date_attempted = fields.Datetime(default=fields.Datetime.now())
