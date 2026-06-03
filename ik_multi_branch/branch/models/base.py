# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class ResUsers(models.Model):
    _inherit = 'res.users'
    branch_ids = fields.Many2many('multi.branch', string='Allowed branches')

    @api.model
    def _get_default_branch(self):
        return self.env.user.branch_id

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _branch_default_get(self):
        return self.env.user.branch_id

    branch_id = fields.Many2one('multi.branch', string='Branch', default=_branch_default_get)
    hp_number = fields.Char(string='HP nummber')

    @api.constrains('hp_number')
    def check_hp_number_constraint(self):
        exist_hp_number = self.env['res.partner'].search([
            ('hp_number', '=', self.hp_number)], limit=2)
        if len(exist_hp_number) > 1:
            raise ValidationError("Sorry !!! you cannot create record with duplicate hp_number")
      

