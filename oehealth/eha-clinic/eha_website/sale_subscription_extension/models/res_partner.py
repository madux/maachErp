from odoo import api, models
from odoo.exceptions import ValidationError


# class ResPartner(models.Model):
#     _inherit = 'res.partner'

#     @api.model
#     def website_form_input_filter(self, request, values):
#         if values.get('name'):
#             # Modify values
#             values['name'] = values['name'].strip()

#         return values
