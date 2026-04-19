from odoo import models, fields

class resUser(models.Model):
    _inherit = 'res.users'
    
    is_delivery_person = fields.Boolean("Is delivery person?")
    is_available = fields.Boolean("Is available")
