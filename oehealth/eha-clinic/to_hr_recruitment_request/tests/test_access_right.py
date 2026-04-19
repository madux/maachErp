from datetime import datetime

from odoo.exceptions import AccessError, QWebException
from odoo.tests import tagged

from .common import Common


@tagged('post_install', '-at_install', 'access_rights')
class TestAccessRight(Common):

    @classmethod
    def setUpClass(cls):
        super(TestAccessRight, cls).setUpClass()

        other_user = cls.env['res.users'].with_context(no_reset_password=True, tracking_disable=True).create({
            'name': 'User other',
            'login': 'user other',
            'email': 'other.user@example.viindoo.com',
            'groups_id': [(6, 0, [cls.env.ref('to_hr_recruitment_request.group_user').id])]
        })
        other_user.action_create_employee()
        other_user.department_id = cls.department

        cls.recruitment_req_follow = cls.create_accepted_recruitment_request(user_create=other_user)
        cls.recruitment_req_follow.message_subscribe(cls.user_request.partner_id.ids)

    def test_user_request_access(self):
        # Recruitment request
        # Case 1: Create (1,1,1,1)
        recruitment_req = self.create_accepted_recruitment_request(job=self.hr_job, user_create=self.user_request).with_user(self.user_request)
        recruitment_req.read()
        recruitment_req.write({'expected_employees': 10})
        with self.assertRaises(QWebException), self.cr.savepoint():
            recruitment_req.unlink()
            raise QWebException

        # Case 2: Following (1,0,0,0)
        recruitment_req_follow = self.recruitment_req_follow.with_user(self.user_request)
        recruitment_req_follow.read()
        with self.assertRaises(AccessError):
            recruitment_req_follow.write({'expected_employees': 10})
        with self.assertRaises(AccessError):
            recruitment_req_follow.unlink()
        with self.assertRaises(AccessError):
            recruitment_req_follow.create({
                'name': 'recruit',
                'user_id': self.user_officer.id,
                'job_tmp': 'sales',
                'reason': 'need for pj',
                'description': 'des',
                'requirements': 'req'
                })

        # Case 3: Not create and not following (0,0,0,0)
        recruitment_req_follow.message_unsubscribe(self.user_request.partner_id.ids)
        self.assertRaises(AccessError, recruitment_req_follow.read)
        self.assertRaises(AccessError, recruitment_req_follow.write, {'expected_employees': 10})
        self.assertRaises(AccessError, recruitment_req_follow.unlink)

        # HrJob(1,0,0,0)
        job_pos = self.hr_job.with_user(self.user_request)
        job_pos.read()
        self.assertRaises(AccessError, job_pos.write, {'name': 'Dev'})
        self.assertRaises(AccessError, job_pos.unlink)
        self.assertRaises(AccessError, job_pos.create, {'name': 'MKT'})

        # Applicant
        # Case 1: Applicant apply to recruitment request created by user (1,1,1,1)
        applicant = self.create_applicant_apply_job(recruitment_req.job_id).with_user(self.user_request)
        applicant.read()
        applicant.write({'name': 'Tom'})
        applicant.create({'name': 'Jerry', 'job_id': recruitment_req.job_id.id})
        applicant.unlink()
        # Case 2: Applicant apply to job belonging department where user is manager (1,1,1,1)
        # Refollow to have access read recruitment request
        self.recruitment_req_follow.message_subscribe(self.user_request.partner_id.ids)
        self.department.manager_id = self.user_request.employee_id
        applicant = self.create_applicant_apply_job(self.recruitment_req_follow.job_id).with_user(self.user_request)
        applicant.read()
        applicant.write({'name': 'Tom'})
        new_applicant = applicant.create({'name': 'Jerry', 'job_id': recruitment_req.job_id.id})
        applicant.unlink()

        # HrResume(1,0,0,0)
        with self.assertRaises(AccessError):
            self.env['hr.applicant.resume.line'].with_user(self.user_request).create({
                'hr_applicant_id': new_applicant.id,
                'name': 'resume',
                'date_start': datetime.now()
                })
        resume_line = self.env['hr.applicant.resume.line'].create({
            'hr_applicant_id': new_applicant.id,
            'name': 'resume',
            'date_start': datetime.now()
            }).with_user(self.user_request)
        resume_line.read()
        self.assertRaises(AccessError, resume_line.write, {'name': 'resume line'})
        self.assertRaises(AccessError, resume_line.unlink)

        # HrRecruitment Stage (1,0,0,0)
        recruitment_state = self.env.ref('hr_recruitment.stage_job1').with_user(self.user_request)
        recruitment_state.read()
        self.assertRaises(AccessError, recruitment_state.write, {'name': 'new'})
        self.assertRaises(AccessError, recruitment_state.create, {'name': 'recruiting'})
        self.assertRaises(AccessError, recruitment_state.unlink)

    def test_user_officer_access(self):
        # Recruitment request
        # Case 1: Create (1,1,1,1)
        recruitment_req = self.create_accepted_recruitment_request(job=self.hr_job, user_create=self.user_officer).with_user(self.user_officer)
        recruitment_req.read()
        recruitment_req.write({'expected_employees': 10})
        recruitment_req.unlink()

        # Case 2: In state [accepted, done, recruiting] (1,1,0,0)
        recruitment_req_recruiting = self.recruitment_req_follow.with_user(self.user_officer)
        recruitment_req_recruiting.read()
        recruitment_req_recruiting.write({'name': 'req'})
        self.assertRaises(AccessError, recruitment_req_recruiting.unlink)

        # Applicant(1,1,1,1)
        applicant = self.create_applicant_apply_job(recruitment_req_recruiting.job_id).with_user(self.user_officer)
        applicant.read()
        applicant.write({'name': 'Tom'})
        new_applicant = applicant.create({'name': 'Jerry', 'job_id': recruitment_req_recruiting.job_id.id})
        applicant.unlink()

        # HrResume(1,1,1,1)
        resume_line = self.env['hr.applicant.resume.line'].with_user(self.user_officer).create({
                'hr_applicant_id': new_applicant.id,
                'name': 'resume',
                'date_start': datetime.now()
                })
        resume_line.read()
        resume_line.write({'name': 'resume line'})
        resume_line.unlink()

        # HrJob(1,1,1,1)
        job_pos = self.hr_job.with_user(self.user_officer)
        job_pos.read()
        job_pos.write({'name': 'Dev'})
        job_pos.unlink()
        job_pos.create({'name': 'MKT'})

    def test_user_manager_access(self):
        # User manager have all the same permission as user officer
        self.user_officer = self.user_manager
        self.test_user_officer_access()

        # Recruitment Request
        # Beside the same, without draft state records, user manager have read, write, create for all records that are not owned.
        draft_recruitment_req = self.env['hr.recruitment.request'].with_user(self.user_request).create({
            'name': 'req name',
            'job_tmp': 'title job',
            'reason': 'reason',
            'description': 'desc',
            'requirements': 'req'
            }).with_user(self.user_manager)
        self.assertRaises(AccessError, draft_recruitment_req.read)
        self.assertRaises(AccessError, draft_recruitment_req.write, {'name': 'new name'})
        self.assertRaises(AccessError, draft_recruitment_req.unlink)

        draft_recruitment_req.sudo().action_confirm()
        confirmed_recruitment_req = draft_recruitment_req
        confirmed_recruitment_req.read()
        confirmed_recruitment_req.write({'name': 'new name'})
        self.assertRaises(AccessError, confirmed_recruitment_req.unlink)

        # Test multi-company
        company2 = self.env['res.company'].create({
            'name': 'company2'
            })
        confirmed_recruitment_req.sudo().company_id = company2
        self.assertRaises(AccessError, confirmed_recruitment_req.read)
        self.assertRaises(AccessError, confirmed_recruitment_req.write, {'name': 'new name'})
        self.assertRaises(AccessError, confirmed_recruitment_req.unlink)
