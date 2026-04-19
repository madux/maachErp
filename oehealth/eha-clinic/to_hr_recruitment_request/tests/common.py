from odoo.tests import SavepointCase, Form


class Common(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(Common, cls).setUpClass()

        cls.department = cls.env.ref('hr.dep_ps')

        User = cls.env['res.users'].with_context(no_reset_password=True, tracking_disable=True)

        cls.user_request = User.create({
            'name': 'User Request',
            'login': 'user request',
            'email': 'request.user@example.viindoo.com',
            'groups_id': [(6, 0, [cls.env.ref('to_hr_recruitment_request.group_user').id])]
        })
        cls.user_request.action_create_employee()
        cls.user_request.department_id = cls.department

        cls.user_officer = User.create({
            'name': 'User Officer',
            'login': 'user officer',
            'email': 'officer.user@example.viindoo.com',
            'groups_id': [(6, 0, [cls.env.ref('hr_recruitment.group_hr_recruitment_user').id])]
        })
        cls.user_officer.action_create_employee()
        cls.user_officer.department_id = cls.department

        cls.user_manager = User.create({
            'name': 'User Manager',
            'login': 'user manager',
            'email': 'manager.user@example.viindoo.com',
            'groups_id': [(6, 0, [cls.env.ref('hr_recruitment.group_hr_recruitment_manager').id])]
        })
        cls.user_manager.action_create_employee()
        cls.user_manager.department_id = cls.department

        cls.hr_job = cls.env.ref('hr.job_developer')
        cls.hr_job.description = 'hr_job description'
        cls.hr_job.requirements = 'hr_job requirement'

    @classmethod
    def create_recruitment_request(cls, job=False, exp_count=1, user_create=False):
        request = cls.env['hr.recruitment.request'].with_user(
            user_create or cls.env.user).with_context(tracking_disable=True).create({
            'name': 'request',
            'job_tmp': 'job',
            'reason': 'reason',
            'job_id': job.id if job else False,
            'description': 'desc',
            'requirements': 'req',
            'expected_employees': exp_count
            })

        request = request.with_user(cls.env.user)
        return request

    @classmethod
    def create_accepted_recruitment_request(cls, job=False, exp_count=1, user_create=False):
        request = cls.create_recruitment_request(job, exp_count, user_create)
        request.action_confirm()
        request.action_accept()
        return request

    @classmethod
    def create_applicant_apply_job(cls, job):
        return cls.env['hr.applicant'].with_context(tracking_disable=True).create({
            'name': 'H',
            'job_id': job.id
            })

    @classmethod
    def action_recruit_applicant(cls, applicant):
        applicant.partner_name = applicant.name
        applicant.with_context(tracking_disable=True).create_employee_from_applicant()
        return applicant
