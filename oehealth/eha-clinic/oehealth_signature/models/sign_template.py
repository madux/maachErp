from odoo import api, fields, models, _


class SignTemplate(models.Model):
    _inherit = "sign.template" 
    
    partner_id = fields.Many2one('res.partner', string='Customer')
    is_hr_document = fields.Boolean(string="Is HR document?")

    @api.model
    def default_get(self, fields):
        """Checks if user belong to HR document group"""
        res = super(SignTemplate, self).default_get(fields)
        res.update({
            'is_hr_document': True if self.env.user.has_group('oehealth_signature.group_hr_document') else False,
        })
        return res
