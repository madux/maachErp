from odoo.tests.common import TransactionCase, Form
from odoo.exceptions import AccessError, ValidationError, UserError
from psycopg2 import IntegrityError


class TestPosConfig(TransactionCase):

    def setUp(self):
        super(TestPosConfig, self).setUp()
        self.pos_config_form = self.env.ref('point_of_sale.pos_config_main')
        #new
        self.form = Form(self.env.ref('point_of_sale.pos_config_main'))
        #new
        self.company = self.env.ref('base.main_company')
        self.pricelist = self.env['product.pricelist'].search([('currency_id', '=', self.env.user.company_id.currency_id.id)], limit=1)
        self.stk_location_id = self.env['stock.warehouse'].search([], limit=1).lot_stock_id
        self.user_demo = self.env.ref('base.user_demo')

        self.pos_config_vals = {
                'pos_session_assigned':'',
                'company_id':self.company.id,
                'pricelist_id':self.pricelist.id,
                'name':'Field Nurse 020',
                'stock_location_id':12,
                'iface_tax_included':'subtotal',
            }


    def test_pos_config_failure(self):
        """ Test config failure when pos_session_assigned field is not provided"""
        with self.assertRaises(AssertionError) as e:
            self.form.pos_session_assigned = ''
            self.form.company_id = self.company.id
            self.form.pricelist_id = self.pricelist.id
            self.form.name = 'Field Nurse 020'
            self.form.stk_location_id =  12
            self.form.iface_tax_included = 'subtotal'
            self.form.save()

    def test_pos_config_success(self):
        """
        Test POS config success
        """
        self.pos_config_vals['pos_session_assigned'] = self.user_demo.id
        new_config = self.pos_config_form.create(self.pos_config_vals)
        self.assertEqual(new_config.name, 'Field Nurse 020')


class TestPosConfigAccessRules(TransactionCase):

    def setUp(self,*args, **kwargs):
        super_class = super().setUp(*args, **kwargs)
        # pos groups
        group_pos_user = self.env.ref('point_of_sale.group_pos_user', False)
        group_pos_manager = self.env.ref('point_of_sale.group_pos_manager', False)
        group_pos_accountant = self.env.ref('pos_extension.group_pos_accountant', False)

        # remove demo user from group_pos_accountant or group_pos_manager if he already belongs 
        user_demo = self.env.ref('base.user_demo')
        group_pos_manager.write({'users': [(3, user_demo.id)]})
        group_pos_accountant.write({'users': [(3, user_demo.id)]})
        #add demo user to field nurse group (Field nurse belongs to group_pos_user)
        group_pos_user.write({'users': [(4, user_demo.id)]})
        self.env= self.env(user=user_demo)

        #create a test POS user 
        self.user_id = self.env['res.users'].sudo().create({
            'name': 'Mr. Tester',
            'login': 'tester@testcomplex.com',
            'password': 'mytestpass',
        })
        return super_class


    def test_field_nurse_can_access_only_own_pos_config(self):
           "Test field nurse can access only own pos config record rules"
           PosConfig = self.env.ref('point_of_sale.pos_config_main')
           #create a pos config with admin and assign it to demo user
           config = PosConfig.sudo().copy({'name': 'New POS config','pos_session_assigned': self.user_id.id})
           with self.assertRaises(AccessError):
               #this should raise access error if demo user tries to access
               PosConfig.browse([config.id]).display_name
