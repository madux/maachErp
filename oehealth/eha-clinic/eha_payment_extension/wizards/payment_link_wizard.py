# -*- coding: utf-8 -*-
from werkzeug import urls

from odoo import models, _


class PaymentLinkWizard(models.TransientModel):
    _inherit = "payment.link.wizard"
    _description = "Generate Payment Link"

    def _generate_link(self):
        for payment_link in self:
            record = self.env[payment_link.res_model].browse(
                payment_link.res_id)
            link = ('%s/website_payment/pay?reference=%s&amount=%s&currency_id=%s'
                    '&partner_id=%s&access_token=%s') % (
                        record.get_base_url(),
                        urls.url_quote_plus(
                            payment_link.description.replace("/", "-")),
                        payment_link.amount,
                        payment_link.currency_id.id,
                        payment_link.partner_id.id,
                        payment_link.access_token
            )
            if payment_link.company_id:
                link += '&company_id=%s' % payment_link.company_id.id
            if payment_link.res_model == 'account.move':
                link += '&invoice_id=%s' % payment_link.res_id
            payment_link.link = link
