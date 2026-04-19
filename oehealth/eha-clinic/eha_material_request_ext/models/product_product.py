#-*- coding: utf-8 -*-

from odoo import models, fields, _

class ProductProduct(models.Model):
    _inherit = "product.product"

    associated_warehouse_product_id = fields.Many2one(comodel_name='product.product', string='Associated Warehouse Product', index=True)