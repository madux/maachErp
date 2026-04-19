# models/res_partner.py
from odoo import models, fields, api

class saleOrder(models.Model):
    _inherit = 'sale.order'
    
    is_pharmacy_sale = fields.Boolean("Is pharmacy sale")
