from odoo import fields, models


class Applicant(models.Model):
    _inherit = 'hr.applicant'

    applicant_skill_ids = fields.One2many('hr.applicant.skill', 'hr_applicant_id', string="Skills")
    resume_line_ids = fields.One2many('hr.applicant.resume.line', 'hr_applicant_id', string='Resumé lines')

    # Used to auto create employee from applicant
    def create_employee_from_applicant(self):
        # Call the function from parent class
        res = super(Applicant, self).create_employee_from_applicant()
        # Used to create skill and resume line of employee form skill and resume line of applicant
        for applicant in self:
            if applicant.emp_id:
                employee_skill = []
                for skill in applicant.applicant_skill_ids:
                    employee_skill.append((0, 0, {
                        'skill_id': skill.skill_id.id or False,
                        'skill_level_id': skill.skill_level_id.id or False,
                        'skill_type_id': skill.skill_type_id.id or False,
                        'level_progress': skill.level_progress}))

                employee_resume_line = []
                for resume in applicant.resume_line_ids:
                    employee_resume_line.append((0, 0, {
                        'name': resume.name or False,
                        'date_start': resume.date_start or False,
                        'date_end': resume.date_end or False,
                        'description': resume.description or False,
                        'line_type_id': resume.line_type_id.id or False}))

                applicant.emp_id.write({'employee_skill_ids':employee_skill, 'resume_line_ids':employee_resume_line})

        return res
