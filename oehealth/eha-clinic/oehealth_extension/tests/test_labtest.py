from odoo.tests.common import TransactionCase, Form
from datetime import datetime

class TestLabTest(TransactionCase):

    def setUp(self, *args, **kwargs):
        result = super().setUp(*args, **kwargs)
        # create lab department
        self.department = self.env['oeh.medical.labtest.department'].create({
            'name': 'Test Department'
        })

        # create lab test type
        self.test_type = self.env['oeh.medical.labtest.types'].create({
            'name': 'New Lab Test',
            'code': 'TEST100',
            'lab_department': self.department.id,
        })

        # create partner
        self.partner = self.env['res.partner'].create({
            'firstname': 'John',
            'lastname': 'Doe'
        })

        # create test patient
        self.patient = self.env['oeh.medical.patient'].create({
            'partner_id': self.partner.id,
            'phone': '1122334455',
            'dob': datetime.today(),
            'sex': 'Male'
        })

        # create test employee
        self.employee = self.env['hr.employee'].create({
            'name': 'John Doe'
        })

        # create test physician
        self.physician = self.env['oeh.medical.physician'].create({
            'employee_id': self.employee.id
        })

        return result

    def test_create(self):
        t = Form(self.env['oeh.medical.lab.test'])
        t.test_type = self.test_type
        t.patient = self.patient
        t.pathologist = self.physician
        test = t.save()

        self.assertEqual(test.test_type, self.test_type)
        self.assertEqual(test.patient, self.patient)
        self.assertEqual(test.pathologist, self.physician)
        self.assertEqual(test.formatted_time, datetime.strftime(test.create_date, "%d %b %Y"))

