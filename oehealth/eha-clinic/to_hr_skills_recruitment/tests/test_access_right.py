from odoo.tests.common import tagged
from .common import Common


@tagged('post_install', '-at_install', 'access_rights')
class TestAssertRight(Common):
    
    def test_01_user_recruitment_access_right(self):
        # model hr.applicant.skill
        self.env['hr.applicant.skill'].with_user(self.user_recruitment).create({
            'hr_applicant_id': self.hr_applicant_1.id,
            'skill_type_id': self.env.ref('hr_skills.hr_skill_type_dev').id,
            'skill_id': self.env.ref('hr_skills.hr_skill_android').id,
            'skill_level_id': self.env.ref('hr_skills.hr_skill_level_expert').id,
        })
        self.hr_applicant_skill_1.with_user(self.user_recruitment).read(['id'])
        self.hr_applicant_skill_1.with_user(self.user_recruitment).write({
            'skill_level_id': self.env.ref('hr_skills.hr_skill_level_advanced').id
        })
        self.hr_applicant_skill_1.with_user(self.user_recruitment).unlink()
        
    def test_02_user_recruitment_access_right(self):
        # model hr.applicant.resume.line
        self.env['hr.applicant.resume.line'].with_user(self.user_recruitment).create({
            'hr_applicant_id': self.hr_applicant_1.id,
            'name': 'Company B',
            'date_start': '2021-01-01',
            'date_end': '2022-01-01'
        })
        self.hr_applicant_resume_line_1.with_user(self.user_recruitment).read(['id'])
        self.hr_applicant_resume_line_1.with_user(self.user_recruitment).name = 'test'
        self.hr_applicant_resume_line_1.with_user(self.user_recruitment).unlink()
    
    def test_01_user_recruitment_admin_access_right(self):
        # model hr.applicant.skill
        self.env['hr.applicant.skill'].with_user(self.user_recruitment_admin).create({
            'hr_applicant_id': self.hr_applicant_1.id,
            'skill_type_id': self.env.ref('hr_skills.hr_skill_type_dev').id,
            'skill_id': self.env.ref('hr_skills.hr_skill_android').id,
            'skill_level_id': self.env.ref('hr_skills.hr_skill_level_expert').id,
        })
        self.hr_applicant_skill_1.with_user(self.user_recruitment_admin).read(['id'])
        self.hr_applicant_skill_1.with_user(self.user_recruitment_admin).write({
            'skill_level_id': self.env.ref('hr_skills.hr_skill_level_advanced').id
        })
        self.hr_applicant_skill_1.with_user(self.user_recruitment_admin).unlink()
    
    def test_02_user_recruitment_admin_access_right(self):
        # model hr.applicant.resume.line
        self.env['hr.applicant.resume.line'].with_user(self.user_recruitment_admin).create({
            'hr_applicant_id': self.hr_applicant_1.id,
            'name': 'Company B',
            'date_start': '2021-01-01',
            'date_end': '2022-01-01'
        })
        self.hr_applicant_resume_line_1.with_user(self.user_recruitment_admin).read(['id'])
        self.hr_applicant_resume_line_1.with_user(self.user_recruitment_admin).name = 'test'
        self.hr_applicant_resume_line_1.with_user(self.user_recruitment_admin).unlink()
