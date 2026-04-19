from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError
from odoo import fields

from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class TestPosOrder(TransactionCase):

    def setUp(self, *args, **kwargs):
        super_class = super().setUp(*args, **kwargs)

        # setup env variables
        self.company = self.env.ref('base.main_company')
        self.partner = self.env.ref('base.res_partner_1')
        self.product = self.env.ref('product.product_product_3')
        self.pos_config = self.env.ref('point_of_sale.pos_config_main')

        # pos groups
        group_pos_user = self.env.ref('point_of_sale.group_pos_user', False)
        group_pos_manager = self.env.ref(
            'point_of_sale.group_pos_manager', False)
        group_pos_accountant = self.env.ref(
            'pos_extension.group_pos_accountant', False)

        # remove demo user from group_pos_accountant or group_pos_manager if he already belongs
        user_demo = self.env.ref('base.user_demo')
        group_pos_manager.write({'users': [(3, user_demo.id)]})
        group_pos_accountant.write({'users': [(3, user_demo.id)]})
        # add demo user to field nurse group
        group_pos_user.write({'users': [(4, user_demo.id)]})

        # change env to demo user
        self.env = self.env(user=user_demo)

        return super_class

    def test_field_nurse_can_access_only_own_orders(self):
        "Test user can access only own pos order record rules"
        PosOrder = self.env['pos.order']
        # create POS order as admin
        self.order = PosOrder.sudo().create({
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'pricelist_id': self.company.partner_id.property_product_pricelist.id,
            'session_id': 1,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product.id,
                'price_unit': 100,
                'discount': 0.0,
                'qty': 1.0,
                'price_subtotal': 100,
                'price_subtotal_incl': 100,
            })],
            'amount_total': 100,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
        })

        with self.assertRaises(AccessError):
            # trying to access the order as env user (demo) raises an access error
            PosOrder.browse([self.order.id]).name

class TestPosSubscriptionOrder(TransactionCase):

    def setUp(self, *args, **kwargs):
        super_class = super().setUp(*args, **kwargs)
        self.company = self.env.ref('base.main_company')
        self.partner = self.env.ref('base.res_partner_1')
        self.public_pricelist = self.env.ref('product.list0')
        self.pos_order = self.env['pos.order']
        self.product = self.env['product.product']
        self.sale_subscription = self.env['sale.subscription']
        self.pos_config = self.env.ref('point_of_sale.pos_config_main')
        self.sub_template = self.env['sale.subscription.template']
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.product_template = self.env['product.template']

        # Test Subscription Template
        self.subscription_tmpl = self.sub_template.create({
            'name': 'TestSubTemplate1',
            'description': 'Test Subscription Template 1',
            'recurring_rule_type': 'monthly', 
            'recurring_interval':1, 
            'recurring_rule_count':1
        })
        self.subscription_tmpl2 = self.sub_template.create({
            'name': 'TestSubTemplate2',
            'description': 'Test Subscription Template 2',
            'recurring_rule_type': 'yearly', 
            'recurring_interval':1, 
            'recurring_rule_count':1
        })

        self.product_template1 = self.product_template.sudo().create({
            'name': 'Sub Test 01',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'subscription_template_id':self.subscription_tmpl.id,
            'recurring_invoice': True,  # if true == subscription product
        })

        self.product_template2 = self.product_template.sudo().create({
            'name': 'Sub Test 02',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'subscription_template_id':self.subscription_tmpl2.id,
            'recurring_invoice': True,  # if true == subscription product
        })

        #non subcription template
        self.product_template3 = self.product_template.sudo().create({
            'name': 'Non Sub Test 01',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'recurring_invoice': False,
        })

        # subscription product
        self.product1 = self.product.sudo().create(
            {'product_tmpl_id': self.product_template1.id, })

        self.product2 = self.product.sudo().create(
            {'product_tmpl_id': self.product_template2.id, })

        # Non subscription product
        self.product3 = self.product.sudo().create(
            {'product_tmpl_id': self.product_template3.id, })

        return super_class

    def test_create_subscription_from_order(self):
        """
        Test selling subcription product from POS creates subscription success
        """

        non_sub_order = {
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'pricelist_id': self.public_pricelist.id,
            'session_id': 1,
            'lines': [(0, 0, {
                'name': "NONSUB/01",
                'product_id': self.product3.id,
                'price_unit': 100,
                'discount': 0.0,
                'qty': 1.0,
                'price_subtotal': 100,
                'price_subtotal_incl': 100,
            })],
            'amount_total': 100,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
        }

        sub_order_count_1 = {
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'pricelist_id': self.public_pricelist.id,
            'session_id': 1,
            'lines': [(0, 0, {
                'name': "TESTSUB/01",
                'product_id': self.product1.id,
                'price_unit': 700,
                'discount': 0.0,
                'qty': 1.0,
                'price_subtotal': 700,
                'price_subtotal_incl': 700,
            })],
            'amount_total': 700,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
        }

        sub_order_count_2 = {
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'pricelist_id': self.public_pricelist.id,
            'session_id': 1,
            'lines': [(0, 0, {
                'name': "TESTSUB/02",
                'product_id': self.product2.id,
                'price_unit': 700,
                'discount': 0.0,
                'qty': 1.0,
                'price_subtotal': 700,
                'price_subtotal_incl': 700,
            }),(0, 0, {
                'name': "TESTSUB/03",
                'product_id': self.product2.id,
                'price_unit': 500,
                'discount': 0.0,
                'qty': 1.0,
                'price_subtotal': 500,
                'price_subtotal_incl': 500,
            })],
            'amount_total': 1200,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
        }

        #create non subscription and subscription orders
        nonsuborder1 = self.pos_order.sudo().create(non_sub_order)
        suborder_count_1 = self.pos_order.sudo().create(sub_order_count_1)
        suborder_count_2 = self.pos_order.sudo().create(sub_order_count_2)

        #test non subscription order should not create a subscription
        self.pos_order.sudo().create_subscription_from_order([nonsuborder1.id])
        record = self.sale_subscription.sudo().search([('name','=','Non Sub Test 01')])
        self.assertFalse(record,msg='non subscription order should not create a subscription')

        #test subcription order to create a subscription
        self.pos_order.sudo().create_subscription_from_order([suborder_count_1.id])
        record1 = self.sale_subscription.sudo().search([('name','=','Sub Test 01')])
        self.assertEqual(record1.name,'Sub Test 01', msg='subscription order should create a subscription')

        #test subcription order with 2 sub subscription products to create 2 subscriptions
        self.pos_order.sudo().create_subscription_from_order([suborder_count_2.id])
        rec_count = self.sale_subscription.sudo().search_count([('name','=','Sub Test 02')])
        self.assertEqual(rec_count,2, msg='subcription order with 2 sub subscription products to create 2 subscriptions')

