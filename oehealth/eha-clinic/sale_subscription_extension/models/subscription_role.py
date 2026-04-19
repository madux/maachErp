from odoo import api, fields, models


class SaleSubscriptionPlan(models.Model):
    _name = 'sale.subscription.roles'
    _description = 'Sale Subscription Roles'

    # @api.onchange('plan_id')
    # def on_change_package_domain(self):
    #     product_ids = self.plan_id.mapped('line_ids.product_id')
    #     # if custom packages we also show them here
    #     if self.subscription_id and self.subscription_id.custom_package_ids:
    #         product_ids = product_ids + self.subscription_id.custom_package_ids.mapped('product_id')
    #     return {'domain': {'package_ids': [('id', 'in', product_ids.ids)]}}

    # def get_package_domain(self):
    #     product_ids = self.plan_id.mapped('line_ids.product_id')
    #     # if custom packages we also show them here
    #     if self.subscription_id and self.subscription_id.custom_package_ids:
    #         product_ids = product_ids + self.subscription_id.custom_package_ids.mapped('product_id')
    #     if product_ids:
    #         return [('id', 'in', product_ids.ids)]

    name = fields.Char(string="Role Name", required=1)
    subscription_id = fields.Many2one('sale.order', string="Subscription")
    currency_id = fields.Many2one(related='subscription_id.currency_id')
    plan_id = fields.Many2one('sale.subscription.plan', string="Plan")
    package_ids = fields.Many2many('product.template', string="Additional Packages")#, domain=get_package_domain)
    budget = fields.Float(string="Budget / yearly", default=0)
    billing_id = fields.Selection([('company', 'Company'), ('individual', 'Individual')], string="Billing")
