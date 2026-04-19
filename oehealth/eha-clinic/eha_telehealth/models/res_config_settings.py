from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    telehealth_product_id = fields.Many2one(comodel_name='product.product', string='Telehealth Product', config_parameter="eha_telehealth.telehealth_product_id")
    telehealth_service_id = fields.Many2one(comodel_name='eha.booking.services', string='Telehealth Service', config_parameter="eha_telehealth.telehealth_service_id")
    telehealth_location_id = fields.Many2one(comodel_name='eha.branch', string='Telehealth Location', config_parameter="eha_telehealth.telehealth_location_id")
    credentials_json = fields.Char('Credentials', config_parameter="eha_telehealth.api_credentials")
    token_json = fields.Char('Token', config_parameter="eha_telehealth.api_token")