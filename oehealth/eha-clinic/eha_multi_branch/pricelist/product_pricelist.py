from odoo import models, fields


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'
    
    branch_ids = fields.Many2many(comodel_name='eha.branch', string='Branch')
    public_pricelist = fields.Boolean(string='Public Pricelist')
