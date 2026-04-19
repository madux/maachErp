# from odoo.tests.common import TransactionCase, Form

# from odoo.addons.sale_subscription.tests.test_sale_subscription import TestSubscription
from odoo.tests import tagged, Form
from odoo.tools import mute_logger
from odoo import fields
from datetime import date

# class SaleSubscriptionTest(TestSubscriptionCommon):
    
#     def test_validate_beneficiaries(self):
#         patient = self.env['oeh.medical.patient'].create({
#             'firstname': 'Brown',
#             'lastname':'Loard',
#             'dob': date.today() - relativedelta(years=35),
#             'phone':'090877755'
#         })
#         sub_form = Form(self.env['sale.order'])
#         sub_form.template_id = self.subscription_tmpl
#         sub_form.partner_id = patient.partner_id
#         sub_form.beneficiaries = patient.partner_id
#         sub = sub_form.save()
#         self.assertEqual(sub.beneficiaries[0], patient)