# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
import hashlib
import hmac
from werkzeug import urls
from odoo.tools.misc import formatLang, format_date, get_lang
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = ["account.move"]

    share_link = fields.Char(string="Payment Link")
 
    # def action_invoice_sent(self):
    #     """ Open a window to compose an email, with the edi invoice template
    #         message loaded by default
    #     """
    #     accountmoveObj = self.env['account.move'].browse([self.id])
    #     self.share_link = self.env['portal.share']._generate_payment_link(accountmoveObj)
    #     self.ensure_one()
    #     template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
    #     lang = get_lang(self.env)
    #     # if template and template.lang:
    #     #     lang = template._render_template(template.lang, 'account.move', self.id)
    #     # else:
    #     lang = lang.code
    #     compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
    #     ctx = dict(
    #         default_model='account.move',
    #         default_res_id=self.id,
    #         # For the sake of consistency we need a default_res_model if
    #         # default_res_id is set. Not renaming default_model as it can
    #         # create many side-effects.
    #         default_res_model='account.move',
    #         default_use_template=bool(template),
    #         default_template_id=template and template.id or False,
    #         default_composition_mode='comment',
    #         mark_invoice_as_sent=True,
    #         # custom_layout="mail.mail_notification_paynow",
    #         model_description=self.with_context(lang=lang).type_name,
    #         force_email=True
    #     )
    #     return {
    #         'name': _('Send Invoice'),
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'account.invoice.send',
    #         'views': [(compose_form.id, 'form')],
    #         'view_id': compose_form.id,
    #         'target': 'new',
    #         'context': ctx,
    #     }
    
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        accountmoveObj = self.env['account.move'].browse([self.id])
        self.share_link = self.env['portal.share']._generate_payment_link(accountmoveObj)
        template = self.env.ref(self._get_mail_template(), raise_if_not_found=False)
        lang = False
        if template:
            lang = template._render_lang(self.ids)[self.id]
        if not lang:
            lang = get_lang(self.env).code
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            # For the sake of consistency we need a default_res_model if
            # default_res_id is set. Not renaming default_model as it can
            # create many side-effects.
            default_res_model='account.move',
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            default_email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True,
            active_ids=self.ids,
        )

        report_action = {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

        if self.env.is_admin() and not self.env.company.external_report_layout_id and not self.env.context.get('discard_logo_check'):
            return self.env['ir.actions.report']._action_configure_external_report_layout(report_action)

        return report_action
     