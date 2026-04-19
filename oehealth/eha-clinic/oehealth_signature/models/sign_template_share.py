import uuid

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SignTemplateShare(models.TransientModel):
    _inherit = 'sign.template.share'

    partner_id = fields.Many2one('res.partner', string='Customer')
      
    @api.onchange('partner_id') 
    def Copy_Link(self):
        template = self.template_id
        if self.partner_id and self.template_id:
            email_address = self.partner_id.email
            if email_address:
                
                if not template.share_link:
                    template.share_link = str(uuid.uuid4())
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                self.url = "%s/sign/%s/%s" % (base_url, template.share_link, self.partner_id.id)
            else:
                raise ValidationError("The Selected Customer Must have an Email - \n Please Issue a Consent Form to the patient to sign instead")

    def open(self):
        return {
            'name': _('Sign'),
            'type': 'ir.actions.act_url',
            'url': '/sign/%s' % (self.template_id.share_link) if not self.partner_id else '/sign/%s/%s' % (self.template_id.share_link, self.partner_id.id),
        }

    def button_close(self):
        return{'type': 'ir.actions.act_window_close'}