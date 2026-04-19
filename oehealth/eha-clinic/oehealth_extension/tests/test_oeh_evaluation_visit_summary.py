from odoo.tests.common import TransactionCase, Form
from datetime import datetime

class TestEvaluationVisitSummaryTest(TransactionCase):

    def setUp(self):
        super(TestEvaluationVisitSummaryTest, self).setUp()
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

        self.evaluation_type = 'Follow Up'

        self.evaluation_start_date = datetime.now()


    def test_create(self):
        evaluation = self.env['oeh.medical.evaluation'].create({
            'evaluation_type': self.evaluation_type,
            'patient': self.patient.id,
            'doctor': self.physician.id,
            'evaluation_start_date': self.evaluation_start_date,
            'height': 167,
            'vitalsigns': [(0, 0, {
                'time': datetime.now(),
                'temp': 37.8,
                'systolic': 89,
                'diastolic': 92.5,
                'heart_rate': 74,
                'respiratory': 15,
                'oxy_saturate': 93})]
        })

        self.assertEqual(evaluation.evaluation_type, 'Follow Up')
        self.assertEqual(evaluation.patient.firstname, 'John')
        self.assertEqual(evaluation.doctor.name, 'John Doe')

        evaluation.change_info_diagnosis_discharge()
        self.assertEqual(evaluation.info_diagnosis, evaluation.info_diagnosis_discharge)

        evaluation.change_directions_diagnosis()
        self.assertEqual(evaluation.directions, evaluation.directions_diagnosis)

        evaluation.change_follow_up_discharge()
        self.assertEqual(evaluation.follow_up, evaluation.follow_up_diagnosis)

        evaluation.change_indication_discharge()
        self.assertEqual(evaluation.indication, evaluation.indication_discharge)

        print('Test was succesfull!')


