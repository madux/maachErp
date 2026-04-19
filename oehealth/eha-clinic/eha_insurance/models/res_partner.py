from odoo import models, fields 


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    current_insurance_id = fields.Many2one('eha.medical.insurance', string="Insurance", domain="[('partner_id','=', active_id),('state','=','Active')]", help="Insurance information. You may choose from the different insurances belonging to the patient")
    is_insurance_organisation = fields.Boolean(string='Insurance Organisation', help='Check if the party is an Insurance Company')