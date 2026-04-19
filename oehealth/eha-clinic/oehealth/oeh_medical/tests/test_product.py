
from odoo.tests.common import TransactionCase


class TestProductSetup(TransactionCase):
    def setUp(self):
        super(TestProductSetup, self).setUp()

        self.product1 = self.env['product.template'].create({
            'name': 'Super Drug',
            'price': 2000,
            'is_oeh_product':True,
            'medicament_type':'Medicine'
        })

        self.product2 = self.env['product.template'].create({
            'name': 'Super Vaccine',
            'price': 2000,
            'is_oeh_product':True,
            'medicament_type':'Vaccine'
        })

        self.product3 = self.env['product.template'].create({
            'name': 'Super Vaccine',
            'price': 2000
        })

        
class TestProduct(TestProductSetup):

    def test_product_template_creation(self):
        self.assertEqual(self.product1.medicament_type, 'Medicine')
        self.assertEqual(self.product2.medicament_type, 'Vaccine')
        self.assertEqual(self.product3.medicament_type, None)