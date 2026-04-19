from odoo import models, fields, api


class Users(models.Model):
    _inherit = "res.users"

    is_healthmate_user = fields.Boolean(string="Is Healthmate User?")