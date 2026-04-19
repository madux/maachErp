from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HRRecruitmentRequest(models.Model):
    _name = 'hr.recruitment.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_expected desc, id desc'
    _description = "Recruitment Request"

    @api.model
    def _get_default_dept(self):
        return self.env.user.employee_id.department_id

    name = fields.Char(string='Subject', size=512, required=False,
                      
                       help='The subject of the recruitment request. E.g. Two new salesmen are requested for a new sales strategy',
                       states={'confirmed': [('readonly', True)],
                               'accepted':[('readonly', True)],
                               'recruiting':[('readonly', True)],
                               'done':[('readonly', True)]
                               },)
    job_id = fields.Many2one('hr.job', string='Requested Position',
                             states={'confirmed': [('readonly', True)],
                                     'accepted':[('readonly', True)],
                                     'recruiting':[('readonly', True)],
                                     'done':[('readonly', True)]
                                     },
                             help='The Job Position you expected to get more hired.',
                             )
    job_tmp = fields.Char(string="Job Title",
                          size=256,
                          help='If you don\'t select the requested position in the field above, you must specify a Job Title here. Upon this request is approved, the system can automatically create a new Job position and attach it to this request.')
    department_id = fields.Many2one('hr.department',
                                    string='Department',
                                    states={'confirmed': [('readonly', True)],
                                            'accepted':[('readonly', True)],
                                            'recruiting':[('readonly', True)],
                                            'done':[('readonly', True)]
                                            },
                                    default=_get_default_dept,
                                    required=False,
                                    index=True
                                    )
    user_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, readonly=True, index=True)
    no_of_hired_employee = fields.Integer('Hired Employees',
                                          compute='_count_dept_employees', required=False)
    expected_employees = fields.Integer('Expected Employees', default=1,
                                        help='Number of extra new employees to be expected via the recruitment request.',
                                        states={'confirmed': [('readonly', True)],
                                                'accepted':[('readonly', True)],
                                                'recruiting':[('readonly', True)],
                                                'done':[('readonly', True)]
                                                },
                                        required=False,
                                        index=True
                                        )
    date_expected = fields.Date('Date Expected', required=False,
                                default=fields.Date.today, index=True)
    description = fields.Text('Job Description',
                              help='Please describe the job',
                              readonly=False,
                              states={'done':[('readonly', True)]},
                              required=False
                              )
    requirements = fields.Text('Job Requirements',
                               help='Please specify your requirements on new employees',
                               readonly=False,
                               states={'done':[('readonly', True)]},
                               required=False
                               )
    reason = fields.Text('Reason',
                         help='Please explain why you request to recruit more employee(s) for your department',
                         states={'confirmed': [('readonly', True)],
                                 'accepted':[('readonly', True)],
                                 'recruiting':[('readonly', True)],
                                 'done':[('readonly', True)]
                                 },
                         required=False
                         )
    state = fields.Selection([
                              ('draft', 'Draft'),
                              ('refused', 'Refused'),
                              ('confirmed', 'Waiting Approval'),
                              ('accepted', 'Approved'),
                              ('recruiting', 'In Recruitment'),
                              ('done', 'Done'),
                              ],
            string='Status', readonly=True, copy=False, index=True, default='draft', required=False,
            help='When the recruitment request is created the status is \'Draft\'.\
            \n It is confirmed by the user and request is sent to the Approver, the status is \'Waiting Approval\'.\
            \n If the Approver accepts it, the status is \'Approved\'.\
            \n If the associated job recruitment is started, the status is \'In Recruitment\'.\
            \n If the number new employees created in association with the request, the status turns to \'Done\' automatically. Or, it can manually be set to \'Done\' whenever an authorized person press button Done'
            )
    date_confirmed = fields.Date('Date Confirmed')
    date_accepted = fields.Date('Date Approved', copy=False,
                                  help="Date of the acceptance of the recruitment request. It's filled when the button Approve is pressed.")
    date_refused = fields.Date('Date Refused')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.id
                                 )

    applicant_ids = fields.One2many('hr.applicant', 'request_id', string='Applicants', readonly=True, index=True)
    employee_ids = fields.One2many('hr.employee', 'request_id', string='Recruited Employees', compute='_compute_recruited_employees', store=True, index=True)

    employees_count = fields.Integer('# of Employees', compute='_count_recruited_employees', store=True, index=True)
    recruited_employees = fields.Float('Recruited Employees Rate', compute='_compute_recruited_employee_percentage')
    applicants_count = fields.Integer('# of Applications', compute='_count_applicants', store=True, index=True)

    # job_state = fields.Selection(string='Job Status', store=True)

    approver_id = fields.Many2one('res.users', string='Approved By', readonly=True, index=True)

    more_than_expected = fields.Boolean(string='More than expected', compute='_compute_more_than_expected',
                                        store=True, index=True)

    _sql_constraints = [
        ('expected_employees_check',
         'CHECK(expected_employees > 0)',
         "Expected Employees must be greater than 0"),
    ]

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'accepted':
            return self.env.ref('to_hr_recruitment_request.mt_recruitment_request_approved')
        elif 'state' in init_values and self.state == 'refused':
            return self.env.ref('to_hr_recruitment_request.mt_recruitment_request_refused')
        elif 'state' in init_values and self.state == 'confirmed':
            return self.env.ref('to_hr_recruitment_request.mt_recruitment_request_confirmed')
        elif 'state' in init_values and self.state == 'recruiting':
            return self.env.ref('to_hr_recruitment_request.mt_recruitment_request_recruiting')
        elif 'state' in init_values and self.state == 'done':
            return self.env.ref('to_hr_recruitment_request.mt_recruitment_request_done')
        return super(HRRecruitmentRequest, self)._track_subtype(init_values)

    @api.depends('applicant_ids', 'applicant_ids.emp_id')
    def _compute_recruited_employees(self):
        for r in self:
            applicants_hired = r.applicant_ids.filtered(lambda app: app.emp_id != False)
            if applicants_hired:
                r.employee_ids = applicants_hired.mapped('emp_id')
            else:
                r.employee_ids = False

    @api.depends('expected_employees', 'employees_count')
    def _compute_more_than_expected(self):
        for r in self:
            if r.expected_employees < r.employees_count:
                r.more_than_expected = True
            else:
                r.more_than_expected = False

    @api.depends('job_id', 'department_id')
    def _count_dept_employees(self):
        for r in self:
            employees = 0
            if r.job_id and r.department_id:
                domain = [('department_id', '=', r.department_id.id), ('job_id', '=', r.job_id.id)]
            elif not r.job_id and r.department_id:
                domain = [('department_id', '=', r.department_id.id)]
            elif self.job_id and not self.department_id:
                domain = [('job_id', '=', r.job_id.id)]
            else:
                domain = []

            if domain:
                employee_ids = self.env['hr.employee'].search(domain)
                employees = len(employee_ids)

            r.no_of_hired_employee = employees

    @api.onchange('department_id')
    def onchange_department_id(self):
        res = {}
        if self.department_id:
            res['domain'] = {'job_id': [('department_id', '=', self.department_id.id)]}
        return res

    @api.onchange('job_id')
    def _onchange_job_id(self):
        if self.job_id:
            if self.job_id.description and not self.description:
                self.description = self.job_id.description
            if self.job_id.requirements and not self.requirements:
                self.requirements = self.job_id.requirements

    @api.depends('employee_ids')
    def _count_recruited_employees(self):
        for r in self:
            r.employees_count = len(r.employee_ids)

    @api.depends('employees_count')
    def _compute_recruited_employee_percentage(self):
        for r in self:
            if r.expected_employees > 0:
                r.recruited_employees = 100.0 * r.employees_count / r.expected_employees

    @api.depends('applicant_ids')
    def _count_applicants(self):
        for r in self:
            r.applicants_count = len(r.applicant_ids)

    def action_confirm(self):
        self.write({
            'state':'confirmed',
            'date_confirmed': fields.Date.today()
            })
        
    def _prepare_new_job_data(self):
        self.ensure_one()
        return {
            'name': self.job_tmp,
            'expected_employees': self.expected_employees,
            'department_id': self.department_id.id,
            'company_id': self.company_id.id,
            'description': self.description,
            'requirements': self.requirements,
            'user_id': self.user_id.id,
            }

    def action_accept(self):
        HRJob = self.env['hr.job']
        for r in self:
            if r.job_id:
                job = r.job_id
            elif r.job_tmp:
                job = HRJob.create(r._prepare_new_job_data())
            else:
                job = self.env['hr.job']
                
            if not job:
                raise ValidationError(_("Please select an existing job or contact your administrator for further help."))

            vals = {
                'date_accepted':fields.Date.today(),
                'approver_id': self.env.user.id,
                'job_id': job.id
                }
            if job.state == 'recruit':
                vals['state'] = 'recruiting'
            else:
                vals['state'] = 'accepted'
            r.write(vals)
            job._suggest_no_of_recruitment()

    def action_refuse(self):
        self.write({
            'state':'refused',
            'date_refused':fields.Date.today(),
            'approver_id': self.env.user.id,
            })

    def action_start_recruit(self):
        self.write({
            'state':'recruiting',
            })

    def action_done(self):
        self.write({
            'state':'done',
            })
    
    def action_draft(self):
        self.write({
            'state':'draft',
            })

    @api.constrains('job_id', 'state')
    def _check_existing_request(self):
        RequestSudo = self.env['hr.recruitment.request'].sudo()
        for r in self:
            if r.job_id and r.state != 'done':
                request = RequestSudo.search([('id', '!=', r.id), ('state', '!=', 'done'), ('job_id', '=', r.job_id.id)], limit=1)
                if request:
                    raise ValidationError(_("An existing request for this job position already exists"))

