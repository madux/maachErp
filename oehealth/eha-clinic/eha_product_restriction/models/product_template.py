#-*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_returnable = fields.Boolean(string="Is Returnable")
    requires_appointment = fields.Boolean(string="Requires Appointment")

    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        res._restrict_product_creation()
        return res

    def _restrict_product_creation(self):
        for rec in self:
            if not rec.user_has_groups('eha_product_restriction.group_product_creation'):
                pass # raise UserError('You do not have rights to create an product(s), please contact store')
