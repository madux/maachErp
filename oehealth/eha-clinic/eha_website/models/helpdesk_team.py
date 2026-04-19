from odoo import api, fields, models
from odoo.exceptions import ValidationError

class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    is_published = fields.Boolean(string="Is published")