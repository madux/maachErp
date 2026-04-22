from datetime import datetime, timedelta
import time
import base64
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    @api.constrains('employee_number')
    def _check_duplicate_employee_number(self):
        employee = self.env['hr.employee'].sudo()
        if self.employee_number not in ["", False]:
            duplicate_employee = employee.search([('employee_number', '=', self.employee_number)], limit=2)
            if len([r for r in duplicate_employee]) > 1:
                raise ValidationError("Employee with same staff ID already existing")

    employee_number = fields.Char(
        string="Staff Number", 
        )
    administrative_supervisor_id = fields.Many2one('hr.employee', string="Administrative Supervisor")
    is_external_staff = fields.Boolean(string='Is External')
    external_company_id = fields.Many2one('res.partner', string='External Company')
    