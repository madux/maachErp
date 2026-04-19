from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    plan_id = fields.Many2one('sale.subscription.plan', 'Subscription Plan', help='Subscription Plans')
    yearly_price = fields.Monetary('Yearly Price', 
        help="Price for  Yearly Subscription. This was added because of web design requirements and only applies to DC membership")
    product_feature_ids = fields.Many2many("product.feature")
    categ_name =  fields.Char(related="categ_id.name")

    
    @api.constrains('sequence')
    def _check_existing_sequence(self):
        #check duplicate
        if self.plan_id:
            plans = self.env['product.template'].search([('plan_id', '=', self.plan_id.id)])
            filter_plan = plans.filtered(lambda  o: o.sequence == self.sequence)
            if len(filter_plan) > 1:
                raise ValidationError('The sequence number you specified has already \
                    been assigned to a product in this Subscription Plan. \n \
                    Please specify another number')


class ProductFeatures(models.Model):
    _name = 'product.feature'
    _description = 'Product Features'
    _order = "name"

    CAT = [
        ('ambulance', 'Ambulance Services'),
        ('dental', 'Dental Services'),
        ('eye', 'Eye Services'),
        ('evacuation', 'Evacuation Services'),
        ('ultrasound', 'Ultrasound Services'),
        ('pharmaceutical', 'Pharmaceutical Services'),
        ('prenatal', 'Prenatal Services'),
        ('others', 'Others'),
    ]
    name = fields.Char('Feature')
    description  = fields.Text()
    category = fields.Selection(CAT, required=False)


class SaleSubscriptionPlan(models.Model):
    _name = 'sale.subscription.plan'
    _description = 'Sale Subscription Plan'

    name = fields.Char('Name', required=False)
    description  = fields.Text()


