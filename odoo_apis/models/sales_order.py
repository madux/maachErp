from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    assigned_delivery_man = fields.Many2one(
        "res.users", 
        string="Delivery person")