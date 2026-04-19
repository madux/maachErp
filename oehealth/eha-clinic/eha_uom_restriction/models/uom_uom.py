#-*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError

class UoM(models.Model):
    _inherit = "uom.uom"

    @api.model
    def create(self, vals):
        res = super(UoM, self).create(vals)
        res._restrict_uom_creation()
        return res

    def _restrict_uom_creation(self):
        for rec in self:
            if not rec.user_has_groups('eha_uom_restriction.group_uom_creation'):
                pass # raise UserError('You currently do not have rights to create a UoM, please contact admin')