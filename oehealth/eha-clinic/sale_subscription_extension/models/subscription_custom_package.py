from odoo import api, fields, models


class SaleSubscriptionPlan(models.Model):
    _name = 'subscription.custom.package'
    _description = 'Subscription Custom Package'

    name = fields.Char(string="Package Name", required=1)
    qty = fields.Float(string="Quantity", default=1, required=1)
    product_id = fields.Many2one('product.template', string="Product")
    categ_id = fields.Many2one(related='product_id.categ_id', readonly=True)
    price = fields.Float(string="Price", default=0)
    subscription_id = fields.Many2one('sale.order', string="Subscription")