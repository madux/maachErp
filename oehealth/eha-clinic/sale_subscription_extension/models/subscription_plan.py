from odoo import api, fields, models

class SaleSubscriptionPlan(models.Model):
    _name = 'sale.subscription.plan'
    _description = 'Sale Subscription Plan'

    name = fields.Char('Name', required=False)
    description  = fields.Text()
    line_ids = fields.One2many('sale.subscription.plan.line', 'plan_id', string='Subscription Plan Lines')



class SaleSubscriptionPlanLine(models.Model):
    _name = 'sale.subscription.plan.line'
    _description = 'Subscription Plan Line'

    name = fields.Char(string="Name", required=False)
    plan_id = fields.Many2one("sale.subscription.plan", string="Subscription Plan")
    product_id = fields.Many2one('product.template', string="Related Product", required=False, index=True)
    qty = fields.Integer(string="quantity", required=False)