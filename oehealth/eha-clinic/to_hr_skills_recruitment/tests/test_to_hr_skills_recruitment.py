from psycopg2 import IntegrityError

from odoo.tests.common import tagged
from odoo.tools.misc import mute_logger
from odoo.exceptions import ValidationError

from .common import Common


@tagged('post_install', '-at_install')
class TestToHrSkillsRecruitment(Common):
    
    def test_create_employee_from_applicant(self):
        self.hr_applicant_1.create_employee_from_applicant()
        employee = self.env['hr.employee'].search([('name', '=', 'Mitchell Demo 1')], limit=1)
        resume_line = employee.resume_line_ids[1]
        employee_skill = employee.employee_skill_ids[0]
        
        self.assertEqual(resume_line.name, 'Company A')
        self.assertEqual(resume_line.date_start.strftime('%Y-%m-%d'), '2020-01-01')
        self.assertEqual(resume_line.date_end.strftime('%Y-%m-%d'), '2021-01-01')
        
        self.assertEqual(employee_skill.skill_type_id.name, 'Dev')
        self.assertEqual(employee_skill.skill_id.name, 'Python')
        self.assertEqual(employee_skill.skill_level_id.name, 'Expert')
    
    def test_01_constraints_date_check(self):
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.hr_applicant_resume_line_1.write({
                'date_start': '2021-12-01',
                'date_end': '2021-01-01'
            })
            self.hr_applicant_resume_line_1.flush()
            
    def test_02_constraints_date_check(self):
        self.hr_applicant_resume_line_1.write({
            'date_start': '2021-12-01',
            'date_end': False
        })
        self.hr_applicant_resume_line_1.flush()
            
    def test_constraints_unique_skill(self):
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['hr.applicant.skill'].create({
                'hr_applicant_id': self.hr_applicant_1.id,
                'skill_type_id': self.env.ref('hr_skills.hr_skill_type_dev').id,
                'skill_id': self.env.ref('hr_skills.hr_skill_python').id,
                'skill_level_id': self.env.ref('hr_skills.hr_skill_level_intermediate').id
            }) 
        
    def test_check_skill_type(self):
        with self.assertRaises(ValidationError):
            self.env['hr.applicant.skill'].create({
                'hr_applicant_id': self.hr_applicant_1.id,
                'skill_type_id': self.env.ref('hr_skills.hr_skill_type_music').id,
                'skill_id': self.env.ref('hr_skills.hr_skill_js').id,
                'skill_level_id': self.env.ref('hr_skills.hr_skill_level_intermediate').id
            })
    
    def test_check_skill_level(self):
        with self.assertRaises(ValidationError):
            self.env['hr.applicant.skill'].create({
                'hr_applicant_id': self.hr_applicant_1.id,
                'skill_type_id': self.env.ref('hr_skills.hr_skill_type_dev').id,
                'skill_id': self.env.ref('hr_skills.hr_skill_js').id,
                'skill_level_id': self.env.ref('hr_skills.hr_skill_level_a1').id
            })
