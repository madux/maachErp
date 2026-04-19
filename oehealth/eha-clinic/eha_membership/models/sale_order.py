# -*- coding: utf-8 -*-

from odoo import fields, models, _

class SaleSubscriptionTemplate(models.Model):
    _inherit = "sale.order.template"
 
    recurring_interval = fields.Integer('Recurring interval')

class SaleOrder(models.Model):
    _inherit = "sale.order"

    subscription_start_date = fields.Date(string='Subscription Start Date')

    def _prepare_subscription_data(self, template):
        res = super(SaleOrder, self)._prepare_subscription_data(template)
        res.update({
            'date_start': self.subscription_start_date if self.subscription_start_date else res["date_start"],
            'recurring_next_date': self.subscription_start_date if self.subscription_start_date else res["recurring_next_date"],
            'recurring_invoice_day': self.subscription_start_date.day if self.subscription_start_date else res["recurring_invoice_day"],
        })
        return res
