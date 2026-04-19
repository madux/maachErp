try:
    # try to use CheckViolation if psycopg2's version >= 2.8
    from psycopg2 import errors
    CheckViolation = errors.CheckViolation
except Exception:
    import psycopg2
    CheckViolation = psycopg2.IntegrityError

from odoo.tests import tagged, Form
from odoo.tools.misc import mute_logger
from odoo.exceptions import ValidationError

from .common import Common


@tagged('post_install', '-at_install')
class TestRecruitmentRequest(Common):

    def test_onchange_and_default_value_form_request(self):
        
        with Form(self.env['hr.recruitment.request'].with_user(self.user_request)) as f:
            f.name = 'test onchange'
            f.reason = 'test reason'
            f.job_id = self.hr_job
            self.assertEqual(f.department_id, self.user_request.employee_id.department_id)
            self.assertEqual(f.description, self.hr_job.description)
            self.assertEqual(f.requirements, self.hr_job.requirements)

    def test_percent_widgetbar(self):
        recruitment_req = self.create_accepted_recruitment_request(job=self.hr_job, exp_count=3, user_create=self.user_request)
        applicant = self.create_applicant_apply_job(recruitment_req.job_id)
        self.action_recruit_applicant(applicant)

        self.assertEqual(recruitment_req.recruited_employees, 100/3)

    def test_constraint_expect_employees_positive(self):
        with self.assertRaises(CheckViolation), mute_logger('odoo.sql_db'):
            self.create_accepted_recruitment_request(job=self.hr_job, exp_count=0, user_create=self.user_request)

    def test_generate_hr_job_when_accept_recruitment_request(self):
        recruitment_req = self.create_accepted_recruitment_request(user_create=self.user_request)
        self.assertTrue(recruitment_req.job_id)

        self.assertEqual(recruitment_req.job_id.department_id, recruitment_req.department_id)
        self.assertEqual(recruitment_req.job_id.name, recruitment_req.job_tmp)
        self.assertEqual(recruitment_req.job_id.description, recruitment_req.description)
        self.assertEqual(recruitment_req.job_id.requirements, recruitment_req.requirements)

    def test_state_approve_request_when_job_in_recruit_state(self):
        recruitment_req = self.create_accepted_recruitment_request(job=self.hr_job, user_create=self.user_request)
        self.assertEqual(recruitment_req.state, 'recruiting')

    def test_state_approve_request_when_job_in_open_state(self):
        self.hr_job.state = 'open'
        recruitment_req = self.create_accepted_recruitment_request(job=self.hr_job, user_create=self.user_request)
        self.assertEqual(recruitment_req.state, 'accepted')

    def test_compute_applicant_and_recruited_field_on_recruitment_request(self):
        recruitment_req = self.create_accepted_recruitment_request(job=self.hr_job, user_create=self.user_request)

        # Create 2 applicant apply to job
        applicant1 = self.create_applicant_apply_job(recruitment_req.job_id)
        applicant2 = self.create_applicant_apply_job(recruitment_req.job_id)

        self.assertEqual(recruitment_req.applicant_ids, applicant1 | applicant2)
        self.assertFalse(recruitment_req.employee_ids)

        # Recruit 2 applicant
        self.action_recruit_applicant(applicant1)
        self.action_recruit_applicant(applicant2)

        self.assertEqual(recruitment_req.employee_ids, applicant1.emp_id | applicant2.emp_id)

    def test_constraint_duplicate_recruitment_request(self):
        self.create_accepted_recruitment_request(job=self.hr_job, user_create=self.user_request)
        with self.assertRaises(ValidationError):
            self.create_accepted_recruitment_request(job=self.hr_job, user_create=self.user_request)
