
from odoo import api, fields, models, _

class AccountInvoice(models.Model):
    _inherit = 'account.move'

    current_insurance = fields.Many2one('oeh.medical.insurance', string="Insurance", related="patient.current_insurance")
    current_insurance_company = fields.Char(string="Insurance Company", related="current_insurance.insurance_company.name")
    current_insurance_no = fields.Char(string="Enrollee Number", related="current_insurance.ins_no")
    






