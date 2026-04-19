from odoo import models, fields


class HREmployee(models.AbstractModel):
    _inherit = 'hr.employee.base'

    request_id = fields.Many2one('hr.recruitment.request', string="Recruitment Request", index=True)
