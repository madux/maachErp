# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductPackaging(models.Model):
    _inherit = 'stock.package.type'
    
    package_carrier_type = fields.Selection([('mydhl', 'My DHL')], string="package carrier type")
    length = fields.Integer('length', help="Packaging length")
