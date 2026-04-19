#-*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError

class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def create(self, vals):
        res = super(ProductProduct, self).create(vals)
        res._restrict_product_creation()
        return res

    def _restrict_product_creation(self):
        for rec in self:
            if not rec.user_has_groups('eha_product_restriction.group_product_creation'):
                pass # raise UserError('You do not have rights to create an product(s), please contact admin')