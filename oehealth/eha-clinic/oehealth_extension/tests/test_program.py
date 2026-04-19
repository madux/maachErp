from odoo.tests.common import TransactionCase, Form

class TestProgram(TransactionCase):

    def setUp(self, *args, **kwargs):
        result = super().setUp(*args, **kwargs)
        self.program = self.env['oeha.medical.program'].create({
            'name': 'Malaria',
            'description': 'The Malaria Program'
        })
        return result

    def test_create(self):
        p = Form(self.env['oeha.medical.program'])
        p.name = 'Malaria'
        p.description = 'The Malaria Program'
        program = p.save()

        self.assertEqual(program.name, 'Malaria')
        self.assertEqual(program.description, 'The Malaria Program')