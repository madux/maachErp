# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
import hashlib
import hmac
from werkzeug import urls
from odoo.exceptions import ValidationError


class PortalShareInherit(models.TransientModel):
    _inherit = ["portal.share"]
    _description = 'Portal Sharing'

    # share_link = fields.Char(string="Link")

    def _generate_payment_link(self, record):
        """record: expects the invoice properties"""
        description = record.ref
        amount = record.amount_residual
        invoice_id = record.id
        currency_id = record.currency_id.id
        partner_id =  record.partner_id.id
        amount_max = record.amount_residual
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        token_str = '%s%s%s' % (partner_id, amount_max, currency_id)
        access_token = hmac.new(secret.encode('utf-8'), token_str.encode('utf-8'), hashlib.sha256).hexdigest()
        link = ('%s/website_payment/pay?reference=%s&amount=%s&currency_id=%s'
                '&partner_id=%s&access_token=%s&invoice_id=%s') % (
                    base_url,
                    urls.url_quote(description),
                    amount,
                    currency_id,
                    partner_id,
                    access_token,
                    invoice_id,
                )
        return link

    @api.model
    def default_get(self, fields):
        result = super(PortalShareInherit, self).default_get(fields)
        result['res_model'] = self._context.get('active_model', False)
        result['res_id'] = self._context.get('active_id', False)
        if result['res_model'] and result['res_id']:
            record = self.env[result['res_model']].browse(result['res_id'])
            if result.get('res_model') == 'account.move':
                result['share_link'] = self._generate_payment_link(record)
            else:
                result['share_link'] = record.get_base_url() + record._get_share_url(redirect=True)
        return result

    @api.onchange('res_model') 
    def onchange_res_model(self):
        # used to trigger the share link to display once the system detects its an account.move
        if self.res_model:
            record = self.env[f"{self.res_model}"].browse([self.res_id])
            if self.res_model in ['account.move']:
                self.share_link = self._generate_payment_link(record)
            else:
                self.share_link = record.get_base_url() + record._get_share_url(redirect=True)
 
    def action_send_mail(self):
        active_record = self.env[self.res_model].browse(self.res_id)
        template = self.env.ref('portal.portal_share_template', False)
        note = self.env.ref('mail.mt_note')
        signup_enabled = self.env['ir.config_parameter'].sudo().get_param('auth_signup.invitation_scope') == 'b2c'
        subject = _("You are invited to access %s" % active_record.display_name)
        if hasattr(active_record, 'access_token') and active_record.access_token or not signup_enabled:
            partner_ids = self.partner_ids
        else:
            partner_ids = self.partner_ids.filtered(lambda x: x.user_ids)
        # if partner already user or record has access token send common link in batch to all user
        for partner in self.partner_ids:
            if self.res_model == 'account.move':
                share_link =  self._generate_payment_link(active_record) # self.share_link or self._generate_payment_link(active_record)
                subject = f"Invoice: {active_record.display_name} Payment Link Shared"
            else:
                share_link = active_record.get_base_url() + active_record._get_share_url(redirect=True, pid=partner.id)
            active_record.with_context(mail_post_autofollow=True).message_post_with_view(template,
                values={'partner': partner, 'note': self.note, 'record': active_record,
                        'share_link': share_link},
                subject= subject,
                subtype_id=note.id,
                email_layout_xmlid='mail.mail_notification_light',
                partner_ids=[(6, 0, partner.ids)])
        # when partner not user send individual mail with signup token
        for partner in self.partner_ids - partner_ids:
            #  prepare partner for signup and send singup url with redirect url
            partner.signup_get_auth_param()
            if self.res_model == 'account.move':
                share_link = self.share_link or self._generate_payment_link(active_record)
                subject = f"Invoice: {active_record.display_name} Payment Link Shared"

            else:
                share_link = partner._get_signup_url_for_action(action='/mail/view', res_id=self.res_id, model=self.model)[partner.id]
            active_record.with_context(mail_post_autofollow=True).message_post_with_view(template,
                values={'partner': partner, 'note': self.note, 'record': active_record,
                        'share_link': share_link},
                subject= subject, # _("%s %s" % (display_message, active_record.display_name)),
                subtype_id=note.id,
                email_layout_xmlid='mail.mail_notification_light',
                partner_ids=[(6, 0, partner.ids)])
        return {'type': 'ir.actions.act_window_close'}
