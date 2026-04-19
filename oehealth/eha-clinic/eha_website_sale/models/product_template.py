from odoo import api, fields, models
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    html_description_sale = fields.Text(
        string="Heathmate product description", help="Used by healthmate to get the default wysiwyg template")
    display_price_on_website = fields.Boolean(
        string="Display Price on Website", default=True)
    display_product_on_website = fields.Boolean(
        string="Display Product on Website", default=False)
    child_product_ids = fields.Many2many(
        'product.product',
        'product_product_child',
        'parent_id',
        'child_id',
        'Child Products',
        help='This are child products especially useful for family membership'
    )
    plan_id = fields.Many2one('sale.subscription.plan',
                              'Subscription Plan', help='Subscription Plans')
    yearly_price = fields.Monetary('Yearly Price',
                                   help="Price for  Yearly Subscription. This was added because of web design requirements and only applies to DC membership")
    product_feature_ids = fields.Many2many("product.feature")
    categ_name = fields.Char(related="categ_id.name")
    is_prescription_product = fields.Boolean(
        'Require Prescription', default=False)
    product_description_prescription = fields.Text(
        "Additional Description for Prescription")
    is_featured = fields.Boolean(string="Is Featured?")

    @api.constrains('sequence')
    def _check_existing_sequence(self):
        # check duplicate
        if self.plan_id:
            plans = self.env['product.template'].search(
                [('plan_id', '=', self.plan_id.id)])
            filter_plan = plans.filtered(lambda o: o.sequence == self.sequence)
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
    name = fields.Char('Feature', placeholder="Product Feature")
    description = fields.Text()
    category = fields.Selection(CAT, required=False)


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    code = fields.Char(string="Code")


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_ecommerce_prices(self):
        for record in self:
            price_info = {}
            param_members_pricelist = self.env['ir.config_parameter'].sudo().get_param("eha_website_sale.member_pricelist")
            param_non_members_pricelist = self.env['ir.config_parameter'].sudo().get_param("eha_website_sale.non_member_pricelist")
            
            members_pricelist = param_members_pricelist and self.env['product.pricelist'].sudo().search([('id', '=', int(param_members_pricelist))]) or None
            non_members_pricelist = param_non_members_pricelist and self.env['product.pricelist'].sudo().search([('id', '=', int(param_non_members_pricelist))]) or None
            
            try:    
                for item_id in members_pricelist.item_ids:
                    if item_id.product_id.id == record.id or item_id.product_tmpl_id.id == record.product_tmpl_id.id:
                        price_info['member_price'] = item_id.fixed_price
                        break
                    elif item_id.categ_id.id == record.categ_id.id:
                        product_tmpl_id = record.product_tmpl_id
                        combination = product_tmpl_id._get_combination_info(product_id=record.id, pricelist=members_pricelist)
                        price_info['member_price'] = combination.get('price', record.lst_price)
                        break
                else:
                    price_info['member_price'] = record.lst_price
            except TypeError:
                price_info['member_price'] = record.lst_price
            except AttributeError:
                price_info['member_price'] = record.lst_price
            
            try:        
                for item_id in non_members_pricelist.item_ids:
                    if item_id.product_id.id == record.id or item_id.product_tmpl_id.id == record.product_tmpl_id.id:
                        price_info['non_member_price'] = item_id.fixed_price
                        break
                    elif item_id.categ_id.id == record.categ_id.id:
                        product_tmpl_id = record.product_tmpl_id
                        combination = product_tmpl_id._get_combination_info(product_id=record.id, pricelist=non_members_pricelist)
                        price_info['non_member_price'] = combination.get('price', record.lst_price)
                        break
                else:
                    price_info['non_member_price'] = record.lst_price
            except TypeError:
                price_info['non_member_price'] = record.lst_price
            except AttributeError:
                price_info['non_member_price'] = record.lst_price
                    
            return price_info
