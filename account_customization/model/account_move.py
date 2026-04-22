from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    
    def button_set_draft(self):
        rec_ids = self.env.context.get('active_ids', []) 
        for rec in rec_ids:
            record = self.env['account.move'].browse([rec])
            record.button_draft()
    
    def button_set_cancel(self):
        rec_ids = self.env.context.get('active_ids', []) 
        for rec in rec_ids:
            record = self.env['account.move'].browse([rec])
            record.button_cancel()
            
    conversion_rate = fields.Float(
        string="Conversion Rate",
        digits=(12, 6),
        help="Custom conversion rate to override the default currency rate.",
    ) 
    
    @api.onchange('conversion_rate')
    def onchange_conversion_rate(self):
        if self.conversion_rate:
            if self.company_id.currency_id.id != self.currency_id.id:
                if self.currency_id.rate_ids:
                    rate_line = self.currency_id.rate_ids.filtered(
                        lambda r: fields.Date.to_date(r.name) <= self.invoice_date
                    ).sorted(key=lambda r: r.name, reverse=True)[:1]
                    # self.currency_id.rate_ids[0].inverse_company_rate = self.conversion_rate
                    rate_line.inverse_company_rate = self.conversion_rate
                    for rec in self.line_ids:
                        amount_currency = rec.amount_currency
                        rec.amount_currency = 0
                        rec.amount_currency = amount_currency
                    self.env.add_to_compute(self._fields['journal_id'], self)
                        
                    # container = {'records': self}
                    # self._sync_dynamic_lines(container)
                    
    @api.onchange('currency_id')
    def _inverse_currency_id(self):
        for invoice in self:
            invoice.get_currency_rate()
            # if invoice.journal_id.currency_id and invoice.journal_id.currency_id != invoice.currency_id:
            if self.company_id.currency_id.id != self.currency_id.id:
                self.env.add_to_compute(self._fields['journal_id'], invoice)

    def get_currency_rate(self):
        if self.company_id.currency_id.id != self.currency_id.id:
            cur_rate = self.currency_id.rate_ids
            rate_line = self.currency_id.rate_ids.filtered(
                lambda r: fields.Date.to_date(r.name) <= self.invoice_date
            ).sorted(key=lambda r: r.name, reverse=True)[:1]
            self.conversion_rate =rate_line.inverse_company_rate
            
    # @api.onchange('currency_id')
    # def onchange_currency_ids(self):
    #     if self.company_id.currency_id.id != self.currency_id.id:
    #         cur_rate = self.currency_id.rate_ids
    #         rate_line = self.currency_id.rate_ids.filtered(
    #             lambda r: fields.Date.to_date(r.name) <= self.invoice_date
    #         ).sorted(key=lambda r: r.name, reverse=True)[:1]
    #         self.conversion_rate =rate_line.inverse_company_rate
    #         container = {'records': self}
    #         self._sync_dynamic_lines(container)
            
            
    def convert_default_rate(self):
        lines = self.mapped('line_ids')
        if self.state not in ['draft']:
            raise ValidationError("You can only perform this operation in draft stage")
        if self.conversion_rate == 0:
            raise ValidationError("Currency rate must be greater than 0")
        # for ln in lines:
        #     # conver_rate = self.conversion_rate 
        #     # ln.conversion_rate = conver_rate 
        #     # ln.currency_rate = conver_rate 
        #     ln.currency_id = self.currency_id.id 
        
        
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.constrains('account_id', 'display_type')
    def _check_payable_receivable(self):
        for line in self:
            account_type = line.account_id.account_type
            if line.move_id.is_sale_document(include_receipts=True):
                if (line.display_type == 'payment_term') ^ (account_type == 'asset_receivable'):
                    pass 
                    # raise UserError(_("Any journal item on a receivable account must have a due date and vice versa."))
            if line.move_id.is_purchase_document(include_receipts=True):
                if (line.display_type == 'payment_term') ^ (account_type == 'liability_payable'):
                    pass 
                    # raise UserError(_("Any journal item on a payable account must have a due date and vice versa."))
    
    conversion_rate = fields.Float(
        string="Conversion Rate",
        digits=(12, 6),
        help="Custom conversion rate to override the default currency rate.",
    )
    @api.onchange('conversion_rate')
    def change_conversion_rate(self):
        if self.conversion_rate and not self.currency_id.is_current_company_currency:
            # self._compute_totals()
            self.currency_rate = self.conversion_rate
            self.currency_id.rate_ids[0].inverse_company_rate = self.conversion_rate
