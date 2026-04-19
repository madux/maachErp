# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp

class product_template(models.Model):
    _inherit = "product.template"

    no_adults = fields.Integer(string="Number of Adult", default=1)
    no_youths = fields.Integer(string="Number of Youth", default=0)
    subscription_type = fields.Selection([('adult', 'Adult'), ('youth', 'Youth'), ('family', 'Family'), ('senior', 'Senior')],
                                         default='adult', string="Subscription Type")
    subscription_discount_type = fields.Selection([('fixed', 'Fixed'), ('perc', 'Percentage %')],
                                         default='perc', string="Discount Policy")
    subscription_discount = fields.Float(string="Discount (Based On Policy)", default=0.0, digits=dp.get_precision('Subscription'))
    subscription_template_id = fields.Many2one('sale.order.template', string="Template")

    def write(self, vals):
        res = super(product_template, self).write(vals)
        for rec in self:
            if self.subscription_discount_type == 'perc':
                if self.subscription_discount > 100 or self.subscription_discount < 0 or \
                        'subscription_discount' in vals and (vals.get('subscription_discount',0) > 100 or vals.get('subscription_discount',0) < 0):
                    raise ValidationError('Percentage discount should be between 0 and 100')
        return res

    @api.model
    def create(self, vals):
        res = super(product_template, self).create(vals)
        if res.subscription_discount_type == 'perc':
            if res.subscription_discount > 100 or res.subscription_discount < 0:
                raise ValidationError('Subscription discount(%) should be between 0 and 100')
        return res
