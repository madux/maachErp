from odoo import api, fields, models, _


class OeHealthProgram(models.Model):
    _name = 'oeha.medical.program'
    _description='Oehealth Programs'

    name = fields.Char(string='Program', help="Program", required=False)
    description = fields.Text(string="Description of the program")
    

    
    def _program_count(self):
        for record in self:
            count = self.env['oeh.medical.patient'].search_count([('program_ids', 'in', record.id)])
            record.program_count = count
        return True

    program_count = fields.Integer(compute=_program_count, string="Patients")

class OeHealthProgramAssignment(models.Model):
    _name = 'oeha.medical.program.assignment'
    _description='Oehealth Program Assignment'
    _rec_name = 'nurse'

    nurse = fields.Many2one('res.users', string="Nurse", help="Nurse", required=False)
    program = fields.Many2many('oeha.medical.program', string="Program")
