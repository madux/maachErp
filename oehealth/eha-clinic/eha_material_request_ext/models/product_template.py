#-*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    associated_warehouse_product_id = fields.Many2one(comodel_name='product.template', string='Associated Warehouse Product', index=True)

    @api.onchange('associated_warehouse_product_id')
    def _onchange_associated_warehouse_product_id(self):
        for rec in self:
            if rec.associated_warehouse_product_id\
            and not rec.uom_id.category_id == rec.associated_warehouse_product_id.uom_id.category_id:
                raise ValidationError("Warehouse product does not belong to the same UOM Category.")
    
    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if vals.get("associated_warehouse_product_id"):
            self._update_product_variant()
        return res

    def _update_product_variant(self):
        for rec in self:
            product_variants = self.env['product.product'].search([('product_tmpl_id', '=', rec.id), ('default_code', '!=', 'Warehouse')])
            product_variants.update({
                'associated_warehouse_product_id': rec.associated_warehouse_product_id.product_variant_id.id
            })