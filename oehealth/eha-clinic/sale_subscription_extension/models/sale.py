from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    allowed_payer_ids = fields.Many2many('res.partner', 'Allowed Payers', compute="_compute_payer_ids")
    payer_id = fields.Many2one('res.partner', 'Payer', help='Specify the partner that will make the payment')

    def _send_order_confirmation_mail_pharmacy(self):
        self._send_order_confirmation_mail
        # sending email to physical sales email address
        pharmacy_email = self.env['ir.config_parameter'].sudo().get_param('eha_website_sale.pharmacy_email')
        pharmacy_sale_template_id = int(self.env['ir.config_parameter'].sudo().get_param('eha_website_sale.confirmation_template'))
        if pharmacy_sale_template_id and pharmacy_email:
            pharmacy_sale_template_id = self.env['mail.template'].sudo().search([('id', '=', pharmacy_sale_template_id)])
            pharmacy_sale_template_id.send_mail(
                self.id, force_send=True,
                raise_exception=False,
                email_values={'email_to': pharmacy_email, 'subject': 'Sale Order Confirmation'}
            )

    @api.depends('partner_id')
    def _compute_payer_ids(self):
        for rec in self:
            parent_id = rec.partner_id.parent_id
            # Would have recursively determined the dependencies, but since
            # we maintain only 2 levels of dependency, this will satisfy that requirement.
            if rec.partner_id and parent_id:
                rec.allowed_payer_ids = [(6,0,[rec.partner_id.id,parent_id.id ])] if not parent_id.parent_id else [(6,0,[rec.partner_id.id, parent_id.id, parent_id.parent_id.id])]
            elif rec.partner_id and not parent_id:
                rec.allowed_payer_ids = [(6,0,[rec.partner_id.id])]
            else:
                rec.allowed_payer_ids = []
        

    def action_invoice_create(self, grouped=False, final=False):
        inv_ids = super(SaleOrder, self).action_invoice_create(grouped, final)
        for rec in self:
            invoices = rec.env['account.move'].browse(inv_ids)
            invoices.write({'payer_id': rec.payer_id.id, 'partner_id': rec.payer_id.id, 'partner_shipping_id':rec.payer_id.id})