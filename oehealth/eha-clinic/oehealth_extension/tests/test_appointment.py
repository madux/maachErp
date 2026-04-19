from odoo.tests.common import TransactionCase, Form
from datetime import datetime, timedelta
import time

class TestAppointment(TransactionCase):

    def setUp(self, *args, **kwargs):
        '''
        Set up objects for testing appointment models
        '''
        result = super().setUp(*args, **kwargs)

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
            'sex': 'Male',
        })

        # create test employee
        self.employee = self.env['hr.employee'].create({
            'name': 'John Doe'
        })

        # create test physician
        self.physician = self.env['oeh.medical.physician'].create({
            'employee_id': self.employee.id
        })

        # create test user
        self.user = self.env['res.users'].create({
            'partner_id': self.partner.id,
            'login': 'test@test.com'
        })

        # get reference to field nurse group
        self.group_field_nurse = self.env.ref('oehealth_extension.group_oeh_medical_chp_nurse', False)

        return result

    def test_create(self):
        '''
        Test for creating new appointments
        '''
        app = self.env['oeh.medical.appointment'].create({
            'patient': self.patient.id,
            'doctor': self.physician.id,
            'appointment_date': datetime.now().isoformat(' ', 'seconds'),
            'duration': 30
        })
        
        appointment_end = app.appointment_date + timedelta(minutes=30)
        appointment_ends = appointment_end.isoformat(' ', 'seconds')

        self.assertEqual(app.patient, self.patient)
        self.assertEqual(app.doctor, self.physician)
        self.assertEqual(app.appointment_end, appointment_end)

    
    def test_field_nurse_appointment(self):
        '''
        Appointments created by a field nurse should be assigned to her automatically
        '''
        
        # add demo user to field nurse group
        demo_user = self.env.ref('base.user_demo')
        self.group_field_nurse.write({'users': [(4, demo_user.id)]})

        # create an appointment then check if the field_nurse is this current nurse
        app = self.env['oeh.medical.appointment'].sudo(demo_user).create({
            'patient': self.patient.id,
            'doctor': self.physician.id,
            'appointment_date': datetime.now(),
            'duration': 30,
        })
        self.assertEqual(app.field_nurse, demo_user)
    
    
    def test_create_ticket(self):
        '''
        Test create_ticket method
        '''
        app = self.env['oeh.medical.appointment'].create({
            'patient': self.patient.id,
            'doctor': self.physician.id,
            'appointment_date': datetime.now(),
            'duration': 30
        })
        
        ticket_obj = self.env['helpdesk.ticket']
        team_id = self.env['ir.model.data'].get_object_reference('oehealth_extension','helpdesk_team_front_desk')
        data = {                    
                    'partner_id': self.patient.partner_id.id,
                    'appointment_id': app.id,
                    'team_id': team_id[1],
                    'name': app.name + " " + self.patient.name
                }
        ticket = ticket_obj.create(data)
        self.assertEqual(ticket.partner_id, self.patient.partner_id)
        self.assertEqual(ticket.appointment_id, app)
        self.assertEqual(ticket.team_id.id, team_id[1])
