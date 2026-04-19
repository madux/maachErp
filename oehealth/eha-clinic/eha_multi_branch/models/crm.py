from odoo import models, fields, api
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError


class Lead(models.Model):
    _inherit = "crm.lead"
    branch_id = fields.Many2one('eha.branch', 'Branch', default=lambda self: self.env['res.partner']._branch_default_get())

class CrmTeam(models.Model):
    _inherit = "crm.team"
    branch_id = fields.Many2one('eha.branch', 'Branch', default=lambda self: self.env['res.partner']._branch_default_get())