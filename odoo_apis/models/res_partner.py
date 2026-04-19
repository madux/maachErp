from odoo import models, fields

class resPartner(models.Model):
    _inherit = 'res.partner'
    
    is_delivery_person = fields.Boolean("Is delivery person?", )#related="user_id.is_delivery_person")
    