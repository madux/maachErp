from odoo import api, fields, models

class SaleSubscriptionTemplate(models.Model):
    _inherit = "sale.order.template"

    active=fields.Boolean(string=True, default=True)
    subscription_type = fields.Selection([
        ('individual', 'Individual Subscription'),
        ('family', 'Family Subscription'),
        ('corporate', 'Corporate Subscription')
    ], string='Subscription Type')
