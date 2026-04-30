from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class Accountaccount(models.Model):
    _inherit = "account.account"

    active = fields.Boolean(default=True)

     