from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import psycopg2
import logging
import json

from datetime import datetime
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class PosOrderExtension(models.Model):
    _inherit = 'pos.order'
    _description = "Point of Sale Orders Extension"

    @api.model
    def create_from_ui(self, orders, draft=False):
        """
        Create Subscription from subscription product when purchased from the POS module
        Field nurse will add the beneficiaries after the subscription is created
        """
        order_ids = super(PosOrderExtension, self).create_from_ui(orders, draft)

        #create subscription from the orders
        # self.create_subscription_from_order(order_ids)

        return order_ids


    # def create_subscription_from_order(self, order_ids):
    #     _logger.info('POS ORDER IDS %s' %order_ids)
    #     Subscription = self.env['sale.order.template']
    #     SubscriptionLine = self.env['sale.order.template.line']
    #     ids =[ o['id'] for o in order_ids ]
    #     orders = self.env['pos.order'].sudo().browse(ids)
    #     lines =  orders and orders.mapped('lines') or []

    #     # filter only subscription products and create subscription for each product
    #     # Odoo uses the field recurring_invoice (boolean) in product.template model
    #     # to identify subscription products

    #     for line in lines.filtered(lambda l: l.product_id.product_tmpl_id.recurring_invoice == True):

    #         # if order has multiple subscription products,
    #         # create a single subscription and add each as
    #         # subscription recurring_invoice_line_ids
    #         # (subscription products) to a single subscription
    #         subscr_line = {
    #             'name': line.product_id.product_tmpl_id.name,
    #             'price_unit': line.price_unit,
    #             'price_subtotal': line.price_subtotal,
    #             'quantity': line.qty,
    #             'product_id': line.product_id.id,
    #             'uom_id': line.product_id.product_tmpl_id.uom_id.id
    #         }


    #         # cache variables to create subscription
    #         subscr_tmpl = line.product_id.product_tmpl_id.subscription_template_id
    #         recurring_rule_type = subscr_tmpl.recurring_rule_type
    #         recurring_interval = subscr_tmpl.recurring_interval
    #         recurring_rule_count = subscr_tmpl.recurring_rule_count
    #         subscr_tmpl_id = subscr_tmpl.id
    #         recurring_invoice_line_ids = [(0, 0, subscr_line)]
    #         company_id = self.env.user.company_id.id
    #         partner_id = line.order_id.partner_id.id
    #         pricelist_id = line.order_id.pricelist_id.id
    #         user_id = line.order_id.user_id.id
    #         date_start = line.order_id.create_date
    #         sub_end_date = self.get_end_date_by_interval(
    #             date_start, recurring_rule_type, recurring_rule_count, recurring_interval) or False

    #         new_subscription = {
    #             'company_id': company_id,
    #             'name': line.product_id.product_tmpl_id.name,
    #             'partner_id': partner_id,
    #             'pricelist_id': pricelist_id,
    #             'template_id': subscr_tmpl_id,
    #             'user_id': user_id,
    #             'date_order': date_start,
    #             'date': sub_end_date,
    #             'recurring_next_date': sub_end_date,
    #             'sale_order_template_line_ids': recurring_invoice_line_ids,
    #             'in_progress': True,
    #             'stage_id': 2, #stage_id =2 = in progress 
    #             'recurring_total':line.price_unit
    #         }

    #         # add customer as beneficiary if he is a patient
    #         # since im not sure the eha subscription extension
    #         # that adds the beneficiaries field is installed,
    #         # check if the field exists in model before creating a beneficiary
    #         try:
    #             # subscr_model_fields = Subscription.fields_get()
    #             # for field in subscr_model_fields:
    #                 # if 'beneficiaries' in field:
    #                 #     if line.order_id.partner_id and line.order_id.partner_id.is_patient:
    #                 #         patient = self.env['oeh.medical.patient'].sudo().search([('partner_id', '=', line.order_id.partner_id.id)], limit=1)
    #                         # new_subscription['beneficiaries'] = [(4, patient.id)]

    #             # create subscription
    #             SubscriptionLine.sudo().create(subscr_line)
    #             subscription_id = Subscription.sudo().create(new_subscription)
    #             bene_vals = {
    #                 'partner_id': partner_id, 'is_staff': False,
    #                 'company_billing': 0.0, 'used_budget': 0.0, 'subscription_id': subscription_id.id,
    #             }
    #             self.env['sale.subscription.beneficiaries'].create(bene_vals)
    #         except Exception as ex:
    #             _logger.exception(ex)
    #             pass


    # def get_end_date_by_interval(self, start_date, recurring_rule_type, recurring_rule_count, recurring_interval):
    #     """
    #         compute subscription end date based on subscription template definitions
    #     """
    #     try:
    #         # This piece of code was borrowed from odoo enterprise sale_subscription.py
    #         periods = {'daily': 'days', 'weekly': 'weeks',
    #                 'monthly': 'months', 'yearly': 'years'}
    #         end_date = start_date + \
    #             relativedelta(
    #                 **{periods[recurring_rule_type]: recurring_rule_count * recurring_interval})

    #         return end_date
    #     except Exception as ex:
    #         _logger.exception(ex)
