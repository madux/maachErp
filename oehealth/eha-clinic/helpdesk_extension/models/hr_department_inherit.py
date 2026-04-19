from datetime import datetime, timedelta 
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
 

class Hr_Department(models.Model):
    _inherit = "hr.department"

    facility_manager_id = fields.Many2one('hr.employee', 'Facility Manager')
