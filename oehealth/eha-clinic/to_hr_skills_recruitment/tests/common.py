from odoo.tests.common import SavepointCase


class Common(SavepointCase):
    
    @classmethod
    def setUpClass(cls):
        super(Common, cls).setUpClass()
        
        cls.hr_applicant_1 = cls.env['hr.applicant'].create({
            'name': 'hr applicant test',
            'partner_name': 'Mitchell Demo 1',
            'partner_mobile': '123456789'
        })
        cls.hr_applicant_resume_line_1 = cls.env['hr.applicant.resume.line'].create({
            'hr_applicant_id': cls.hr_applicant_1.id,
            'name': 'Company A',
            'date_start': '2020-01-01',
            'date_end': '2021-01-01'
        })
        cls.hr_applicant_skill_1 = cls.env['hr.applicant.skill'].create({
            'hr_applicant_id': cls.hr_applicant_1.id,
            'skill_type_id': cls.env.ref('hr_skills.hr_skill_type_dev').id,
            'skill_id': cls.env.ref('hr_skills.hr_skill_python').id,
            'skill_level_id': cls.env.ref('hr_skills.hr_skill_level_expert').id,
        })
        
        cls.user_recruitment = cls.env.ref('base.user_demo')
        cls.user_recruitment_admin = cls.env.ref('base.user_admin')
        
        cls.user_recruitment.groups_id = [(6, 0, [cls.env.ref('hr_recruitment.group_hr_recruitment_user').id])]
        cls.user_recruitment_admin.groups_id = [(6, 0, [cls.env.ref('hr_recruitment.group_hr_recruitment_manager').id])]
