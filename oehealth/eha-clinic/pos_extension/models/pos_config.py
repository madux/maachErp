from odoo import api, fields, models, _

class PosConfigExtension(models.Model):
    _inherit = 'pos.config'
    _description = 'Odoo Point of sale module extension'
    
    pos_session_assigned = fields.Many2one('res.users', string="Assign POS To", required=False)