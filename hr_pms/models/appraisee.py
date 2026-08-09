from datetime import datetime, timedelta
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
from odoo import http
import logging
# from lxml import etree

_logger = logging.getLogger(__name__)


class PMS_Appraisee(models.Model):
    _name = "pms.appraisee"
    _description= "Employee appraisee"
    _inherit = "mail.thread"

    @api.constrains('training_section_line_ids')
    def constrain_for_training_section_line_ids(self):
        user_id = self.env.user
        # if the user is administative supervisor => find the lines he has requested
        # and ensure it is not greater than 2
        if self.env.uid not in [self.manager_id.user_id.id, self.administrative_supervisor_id.user_id.id]:
            raise ValidationError('You are not allowed to add training needs')
        if len(self.mapped('training_section_line_ids').\
                   filtered(lambda self: self.env.user.id == self.requester_id.id)) > 2:
            raise ValidationError('Maximum number of training needs added by you must not exceed 2. Please remove the line and save')

    name = fields.Char(
        string="Description Name", 
        required=True,
        size=120
        )
    active = fields.Boolean(
        string="Active", 
        default=True,
        tracking=True,
        )
    fold = fields.Boolean(
        string="Fold", 
        default=False
        )
    
    lock_fields = fields.Boolean(
        string="Lock Fields", 
        default=False
        )
    is_current_user = fields.Boolean(
        default=False, 
        compute="compute_current_user", 
        store=False,
        help="Used to determine what the appraisee sees"
        )

    pms_department_id = fields.Many2one(
        'pms.department', 
        string="PMS Department ID",
        copy=True,
        store=True
        )
    section_id = fields.Many2one(
        'pms.section', 
        string="Section ID",
        copy=True
        )
    submitted_date = fields.Datetime('Submitted Date')
    dummy_kra_section_scale = fields.Integer(
        string="Dummy KRA Section scale",
        help="Used to get the actual kra section scale because it wasnt setup",
        compute="get_kra_section_scale"
        )
            
    employee_id = fields.Many2one(
        'hr.employee', 
        string="Employee",
        copy=False
        )
    employee_number = fields.Char( 
        string="Staff ID",
        related="employee_id.employee_number",
        store=True,
        size=6,
        copy=False
        )
    job_title = fields.Char( 
        string="Job title",
        related="employee_id.job_title",
        store=True
        )
    work_unit_id = fields.Many2one(
        'hr.work.unit',
        string="Job title",
        related="employee_id.work_unit_id",
        store=True
        )
    job_id = fields.Many2one(
        'hr.job',
        string="Function", 
        related="employee_id.job_id"
        )
    ps_district_id = fields.Many2one(
        'hr.district',
        string="District", 
        related="employee_id.ps_district_id",
        store=True
        )
    department_id = fields.Many2one(
        'hr.department', 
        string="Department ID",
        copy=True,
        store=True,
        related="employee_id.department_id",
        )

    template_category_id = fields.Many2one(
        'pms.category', 
        string="Category",
        copy=True,
        store=True, 
        )

    reviewer_id = fields.Many2one(
        'hr.employee', 
        string="Reviewer",
        related="employee_id.reviewer_id",
        store=True
        )
    administrative_supervisor_id = fields.Many2one(
        'hr.employee', 
        string="Administrative Supervisor",
        related="employee_id.administrative_supervisor_id",
        store=True
        )
    manager_id = fields.Many2one(
        'hr.employee', 
        string="Functional Manager",
        related="employee_id.parent_id",
        store=True
        )
    approver_ids = fields.Many2many(
        'hr.employee', 
        string="Approvers",
        readonly=True
        )
    appraisee_comment = fields.Text(
        string="Appraisee Comment",
        tracking=True,
        copy=False,
        store=True,
        )
    appraisee_attachement_ids = fields.Many2many(
        'ir.attachment', 
        'ir_pms_appraisee_attachment_rel',
        'pms_appraisee_attachment_id',
        'attachment_id',
        string="Attachment",
        copy=False
    )
    appraisee_attachement_set = fields.Integer(default=0, required=1) # Added to field to check whether attachment have been updated
    supervisor_comment = fields.Text(
        string="Supervisor Comment", 
        # tracking=True
        copy=False
        )
    supervisor_attachement_ids = fields.Many2many(
        'ir.attachment', 
        'ir_pms_supervisor_attachment_rel',
        'pms_supervisor_attachment_id',
        'attachment_id',
        string="Attachment"
    )
    supervisor_attachement_set = fields.Integer(default=0, required=1)
    manager_comment = fields.Text(
        string="Manager Comment",
        # tracking=True 
        )
    manager_attachement_ids = fields.Many2many(
        'ir.attachment', 
        'ir_pms_attachment_rel',
        'pms_manager_attachment_id',
        'attachment_id',
        string="Attachment"
    )
    manager_attachement_set = fields.Integer(default=0, required=1)
    reviewer_comment = fields.Text(
        string="Reviewers Comment", 
        # tracking=True,
        )     
        
    reviewer_attachement_ids = fields.Many2many(
        'ir.attachment', 
        'ir_pms_reviewer_attachment_rel',
        'pms_reviewer_attachment_id',
        'attachment_id',
        string="Attachment"
    )
    reviewer_attachement_set = fields.Integer(default=0, required=1)
    appraisee_satisfaction = fields.Selection([
        ('none', 'None'),
        ('fully_agreed', 'Fully Agreed'),
        ('largely_agreed', 'Largely Agreed'),
        ('partially_agreed', 'Partially Agreed'),
        ('largely_disagreed', 'Largely Disagreed'),
        ('totally_disagreed', 'Totally Disagreed'),
        ], string="Perception on your Appraisal", default = "none", 
        tracking=True, copy=False)
    type_of_pms = fields.Selection([
        ('gs', 'Goal Setting'),
        ('hyr', 'Mid year review'),
        ('fyr', 'Full Appraisal'),
        ], string="Type of PMS", default = "", 
        copy=True)
    line_manager_id = fields.Many2one(
        'hr.employee', 
        string="Line Manager"
        )
    
    directed_user_id = fields.Many2one(
        'res.users', 
        string="Appraisal with ?", 
        readonly=True
        )
    goal_setting_section_line_ids = fields.One2many(
        "goal.setting.section.line",
        "goal_setting_section_id",
        string="Goal Settings",
        copy=False
    )
    hyr_kra_section_line_ids = fields.One2many(
        "hyr.kra.section.line",
        "hyr_kra_section_id",
        string="HYR KRAs",
        copy=False
    )
    kra_section_line_ids = fields.One2many(
        "kra.section.line",
        "kra_section_id",
        string="KRAs",
        copy=True
    )
    
    lc_section_line_ids = fields.One2many(
        "lc.section.line",
        "lc_section_id",
        string="Leadership Competence",
        copy=True
    )
    fc_section_line_ids = fields.One2many(
        "fc.section.line",
        "fc_section_id",
        string="Functional Competence",
        copy=True
    )
    training_section_line_ids = fields.One2many(
        "training.section.line",
        "training_section_id",
        string="Training section",
        copy=False
    )
    current_assessment_section_line_ids = fields.One2many(
        "current.assessment.section.line",
        "current_assessment_section_id",
        string="Assessment section",
        # default=lambda self: self._get_current_assessment_lines()
    )

    potential_assessment_section_line_ids = fields.One2many(
        'potential.assessment.section.line',
        'potential_section_id',
        string="potential assessment Appraisal"
    )
    qualitycheck_section_line_ids = fields.One2many(
        "qualitycheck.section.line",
        "qualitycheck_section_id",
        string="Quality check section"
    )
    state = fields.Selection([
        ('goal_setting_draft', 'Goal Settings'),
        ('gs_fa', 'Goal Settings: FA TO APPROVE'),
        ('hyr_draft', 'Mid Year Review'),
        ('hyr_admin_rating', 'Admin Supervisor'),
        ('hyr_functional_rating', 'Functional Appraiser(HYR)'),
        ('draft', 'Full Appraisal Review'),
        ('admin_rating', 'Administrative Appraiser'),
        ('functional_rating', 'Functional Appraiser'),
        ('reviewer_rating', 'Reviewer'),
        ('wating_approval', 'HR to Approve'),
        ('done', 'Completed'),
        ('signed', 'Signed Off'),
        ('withdraw', 'Withdrawn'), 
        ], 
        string="Status", 
        default = "goal_setting_draft", 
        readonly=True, 
        store=True, 
        tracking=True, 
        copy=False
    )
    dummy_state = fields.Selection([
        ('gs', 'Goal Settings'),
        ('gs_fa', 'Goal Settings FA For Approval'),
        ('my', 'Mid Year Review'),
        ('hyr_a', 'Admin Supervisor'),
        ('hyr_f', 'Functional Appraiser(HYR)'),
        ('a', 'Draft'),
        ('b', 'Administrative Appraiser'),
        ('c', 'Functional Appraiser'),
        ('d', 'Reviewer'),
        ('e', 'HR to Approve'),
        ('f', 'Completed'),
        ('g', 'Signed Off'),
        ('h', 'Withdrawn'),
        ], string="Dummy Status", readonly=True,compute="_compute_new_state", store=True,copy=False)
    

    @api.onchange('type_of_pms')
    def onchange_type_of_pms(self):
        """This is to enable status move directly to
          final year review or Mid year review when 
          the type of pms is triggered
        """
        self.ensure_one()
        if self.type_of_pms:
            self.state = 'hyr_draft' if self.type_of_pms == "hyr" else "draft"

    @api.onchange('appraisee_satisfaction')
    def onchange_appraisee_satisfaction(self):
        '''
        This is to trigger the state to notify that employee 
        has completed his perception
        '''
        if self.appraisee_satisfaction != 'none':
            self.update({'state': 'signed'})
        else:
            self.update({'state': 'done'})
    
    def compute_score(self):
        self.compute_current_assessment_score()
        self.compute_potential_assessment_score()
        self.compute_final_lc_score()
        self.compute_final_fc_score()
        self.compute_final_kra_score()
        self.compute_overall_score()

    @api.depends('state')
    def _compute_new_state(self):
        for rec in self:
            if rec.state == 'goal_setting_draft':
                rec.dummy_state = 'gs'
            elif rec.state == 'gs_fa':
                rec.dummy_state = 'gs_fa'
            elif rec.state == 'hyr_draft':
                rec.dummy_state = 'my'
            elif rec.state == 'hyr_admin_rating':
                rec.dummy_state = 'hyr_a'
            elif rec.state == 'hyr_functional_rating':
                rec.dummy_state = 'hyr_f'
            elif rec.state == 'draft':
                rec.dummy_state = 'a'
            elif rec.state == 'admin_rating':
                rec.dummy_state = 'b'
            elif rec.state == 'functional_rating':
                rec.dummy_state = 'c'
            elif rec.state == 'reviewer_rating':
                rec.dummy_state = 'd'
            elif rec.state == 'wating_approval':
                rec.dummy_state = 'e'
            elif rec.state == 'done':
                rec.dummy_state = 'f'
            elif rec.state == 'signed':
                rec.dummy_state = 'g'
            else:
                rec.dummy_state = 'gs'

    pms_year_id = fields.Many2one(
        'pms.year', string="Period", copy=True)
    date_close = fields.Date(
        string="Date close", 
        readonly=False, 
        store=True, copy=True)
    date_from = fields.Date(
        string="Date From", 
        readonly=False, 
        store=True, copy=True)
    date_end = fields.Date(
        string="Date End", 
        readonly=False,
        store=True, 
        copy=True
        )
    deadline = fields.Date(
        string="Deadline Date", 
        # compute="get_appraisal_deadline", 
        store=True, copy=True)
    online_deadline_date = fields.Date(
        string="Appraisee Deadline Date", 
        # compute="get_appraisal_deadline", 
        store=True)

    overall_score = fields.Float(
        string="Overall score", 
        compute="compute_overall_score", 
        store=True)
    
    current_assessment_score = fields.Float(
        string="Current Assessment score", 
        compute="compute_current_assessment_score", 
        store=True)
    potential_assessment_score = fields.Float(
        string="Potential Assessment score", 
        compute="compute_potential_assessment_score", 
        store=True)
    post_normalization_score = fields.Float(
        string="Post normalization score", 
        store=True)
    post_normalization_description = fields.Text(
        string="Post normalization Description", 
        store=True)
    normalized_score_uploader_id = fields.Many2one(
        'res.users',
        string='Uploaded by'
        )

    final_kra_score = fields.Float(
        string='Final KRA Score', 
        store=True,
        compute="compute_final_kra_score"
        )
    final_fc_score = fields.Float(
        string='Final FC Score', 
        store=True,
        compute="compute_final_fc_score"
        )
    
    final_lc_score = fields.Float(
        string='Final LC Score', 
        store=True,
        compute="compute_final_lc_score"
        )
    
    def _get_default_instructions(self):
        ins = self.env.ref('hr_pms.pms_instruction_1').description
        return ins
    
    instruction_html = fields.Text(
        string='Instructions', 
        store=True,
        copy=True,
        default=lambda self: self._get_default_instructions()
        )
    
    # consider removing
    kra_section_weighted_score = fields.Float(
        string='KRA Weight', 
        readonly=True,
        store=True,
        )
    # consider removing
    fc_section_weighted_score = fields.Integer(
        string='Functional Competency Weight', 
        readonly=True,
        store=True,
        )
    # consider removing
    lc_section_weighted_score = fields.Integer(
        string='Leadership Competency Weight', 
        readonly=True,
        store=True,
        )
    # consider removing
    kra_section_avg_scale = fields.Integer(
        string='KRA Scale', 
        readonly=True,
        store=True,
        )
     
    # consider removing
    fc_section_avg_scale = fields.Integer(
        string='Functional Competency Scale', 
        store=True,
        )
    
    reviewer_work_unit = fields.Many2one(
        'hr.work.unit',
        string="Reviewer Unit", 
        related="employee_id.reviewer_id.work_unit_id",
        store=True
        )
    reviewer_job_title = fields.Char(
        string="Reviewer Designation", 
        related="employee_id.reviewer_id.job_title",
        store=True
        )
    reviewer_job_id = fields.Many2one(
        'hr.job',
        string="Reviewer Function",
        related="employee_id.reviewer_id.job_id",
        store=True
        )
    reviewer_district = fields.Many2one(
        'hr.district',
        string="Reviewer District", 
        related="employee_id.reviewer_id.ps_district_id",
        store=True
        )
    reviewer_department = fields.Many2one(
        'hr.department',
        string="Reviewer department", 
        related="employee_id.reviewer_id.department_id",
        store=True
        )
    reviewer_employee_number = fields.Char(
        string="Reviewer Employee Number", 
        related="employee_id.reviewer_id.employee_number",
        store=True
        )
    
    manager_work_unit = fields.Many2one(
        'hr.work.unit',
        string="Manager Unit", 
        related="employee_id.parent_id.work_unit_id",
        store=True
        )
    manager_job_title = fields.Char(
        string="Manager Designation", 
        related="employee_id.parent_id.job_title",
        store=True
        )
    manager_job_id = fields.Many2one(
        'hr.job',
        string="Manager Function", 
        related="employee_id.parent_id.job_id",
        store=True
        )
    manager_district = fields.Many2one(
        'hr.district',
        string="Manager District", 
        related="employee_id.parent_id.ps_district_id",
        store=True
        )
    
    manager_department = fields.Many2one(
        'hr.department',
        string="Manager department", 
        related="employee_id.parent_id.department_id",
        store=True
        )
    manager_employee_number = fields.Char(
        string="Manager Employee Number", 
        related="employee_id.parent_id.employee_number",
        store=True
        )
    supervisor_work_unit = fields.Many2one(
        'hr.work.unit',
        string="Supervisor Unit", 
        related="employee_id.administrative_supervisor_id.work_unit_id",
        store=True
        )
    supervisor_job_title = fields.Char(
        string="Supervisor Designation", 
        related="employee_id.administrative_supervisor_id.job_title",
        store=True
        )
    supervisor_job_id = fields.Many2one(
        'hr.job',
        string="Supervisor Function", 
        related="employee_id.administrative_supervisor_id.job_id",
        store=True
        )
    supervisor_department = fields.Many2one(
        'hr.department',
        string="Supervisor Dept", 
        related="employee_id.administrative_supervisor_id.department_id",
        store=True
        )
    supervisor_district = fields.Many2one(
        'hr.district',
        string="Supervisor District", 
        related="employee_id.administrative_supervisor_id.ps_district_id",
        store=True
        )
    supervisor_employee_number = fields.Char(
        string="Supervisor Employee Number", 
        related="employee_id.administrative_supervisor_id.employee_number",
        store=True
        )
    is_functional_appraiser = fields.Boolean(string='Is functional appraiser', compute="compute_functional_appraiser")
    reason_back = fields.Text(string='Return Reasons', tracking=True)
    
    @api.depends('pms_department_id')
    def get_kra_section_scale(self):
        if self.pms_department_id:
            kra_scale = self.pms_department_id.sudo().mapped('section_line_ids').filtered(
                    lambda res: res.type_of_section == "KRA")
            scale = kra_scale[0].section_avg_scale if kra_scale else 4
            self.dummy_kra_section_scale = scale 
        else:
            self.dummy_kra_section_scale = 4
      
    @api.depends('kra_section_line_ids')
    def compute_final_kra_score(self):
        for rec in self:
            if rec.kra_section_line_ids:
                kra_total = sum([
                    weight.weighted_score for weight in rec.mapped('kra_section_line_ids')
                    ])
                rec.final_kra_score = kra_total
            else:
                rec.final_kra_score = 0

    @api.depends('fc_section_line_ids')
    def compute_final_fc_score(self):
        for rec in self:
            if rec.fc_section_line_ids:
                fc_total = sum([
                    weight.weighted_score for weight in rec.mapped('fc_section_line_ids')
                    ])
                rec.final_fc_score = fc_total
            else:
                rec.final_fc_score = 0

    @api.depends('lc_section_line_ids')
    def compute_final_lc_score(self):
        for rec in self:
            if rec.lc_section_line_ids:
                fc_total = sum([
                    weight.weighted_score for weight in rec.mapped('lc_section_line_ids')
                    ])
                rec.final_lc_score = fc_total 
            else:
                rec.final_lc_score = 0

    @api.depends(
            'final_kra_score',
            'final_lc_score',
            'final_fc_score'
            ) 
    def compute_overall_score(self):
        for rec in self:
            if rec.final_kra_score and rec.final_lc_score and rec.final_fc_score:
                kra_section_weighted_score = rec.pms_department_id.hr_category_id.kra_weighted_score 
                fc_section_weighted_score = rec.pms_department_id.hr_category_id.fc_weighted_score
                lc_section_weighted_score = rec.pms_department_id.hr_category_id.lc_weighted_score 

                # rec.section_id.weighted_score
                # e.g 35 % * kra_final + 60% * lc_final * 15% + fc_final * 45%
                # e.g 35 % * kra_final + 0.60% * lc_final * 0.15% + fc_final * 0.45

                rec.overall_score = (kra_section_weighted_score / 100) * rec.final_kra_score + \
                (fc_section_weighted_score/ 100) * rec.final_fc_score + \
                (lc_section_weighted_score/ 100) * rec.final_lc_score
            else:
                rec.overall_score = 0
    
    @api.depends(
            'current_assessment_section_line_ids.assessment_type',
            )
    def compute_current_assessment_score(self):
        'get the lines for appraisers and compute'
        ar_rating = 0
        fa_rating = 0
        fr_rating = 0
        for rec in self.current_assessment_section_line_ids:
            rec.generate_current_assessment_type()
        
        ar = self.mapped('current_assessment_section_line_ids').filtered(
            lambda s: s.state == 'admin_rating'
        )
        fa = self.mapped('current_assessment_section_line_ids').filtered(
            lambda s: s.state == 'functional_rating'
        )
        fr = self.mapped('current_assessment_section_line_ids').filtered(
            lambda s: s.state == 'reviewer_rating'
        )
        if ar:
            ar_rating = ar[0].administrative_supervisor_rating if self.employee_id.administrative_supervisor_id else 0
        if fa:
            fa_rating = fa[0].functional_supervisor_rating if self.employee_id.parent_id else 0
        if fr:
            fr_rating = fr[0].reviewer_rating if self.employee_id.reviewer_id else 0
        aar = ar_rating * 30 if self.employee_id.administrative_supervisor_id else 0
        f_rating = self.get_fa_rating(
                    self.employee_id.parent_id, 
                    self.employee_id.administrative_supervisor_id, 
                    self.employee_id.reviewer_id)
        faa = fa_rating * f_rating
        ffr = fr_rating * 40 if self.employee_id.reviewer_id else 0
        weightage = (aar) + (faa) + (ffr)
        self.current_assessment_score = weightage / 4
        _logger.info(f"Current assessment score is ==> {weightage / 4}")

    def get_fa_rating(self, manager_id, administrative_supervisor_id,reviewer_id):
        f_rating = 30
        if not administrative_supervisor_id and not reviewer_id:
            f_rating = 100
        elif reviewer_id and not administrative_supervisor_id:
            f_rating = 60
        elif administrative_supervisor_id and not reviewer_id:
            f_rating = 70
        return f_rating

    @api.depends(
        'potential_assessment_section_line_ids',
        )
    def compute_potential_assessment_score(self):
        'get the lines for appraisers and compute'
        ar_rating = 0
        fa_rating = 0
        fr_rating = 0
        for rec in self.current_assessment_section_line_ids:
            rec.generate_potential_assessment_type()
        ar = self.mapped('potential_assessment_section_line_ids').filtered(
            lambda s: s.state == 'admin_rating'
        )
        fa = self.mapped('potential_assessment_section_line_ids').filtered(
            lambda s: s.state == 'functional_rating'
        )
        fr = self.mapped('potential_assessment_section_line_ids').filtered(
            lambda s: s.state == 'reviewer_rating'
        )
        if ar:
            ar_rating = ar[0].administrative_supervisor_rating if self.employee_id.administrative_supervisor_id else 0
        if fa:
            fa_rating = fa[0].functional_supervisor_rating if self.employee_id.parent_id else 0
        if fr:
            fr_rating = fr[0].reviewer_rating if self.employee_id.reviewer_id else 0
        
        aar = ar_rating * 30 if self.employee_id.administrative_supervisor_id else 0
        f_rating = self.get_fa_rating(
                    self.employee_id.parent_id, 
                    self.employee_id.administrative_supervisor_id, 
                    self.employee_id.reviewer_id)
        faa = fa_rating * f_rating
        ffr = fr_rating * 40 if self.employee_id.reviewer_id else 0
        weightage = (aar) + (faa) + (ffr)
        self.potential_assessment_score = weightage / 4

    def check_kra_section_lines(self):
        # if the employee has administrative reviewer, 
        # system should validate to see if they have rated
        if self.state == "admin_rating":
            if self.mapped('kra_section_line_ids').filtered(
                lambda line: line.administrative_supervisor_rating < 1):
                raise ValidationError(
                    "Ops! Please ensure all administrative supervisor's rating on KRA section is at least 1"
                )
        elif self.state == "functional_rating":
            if self.mapped('kra_section_line_ids').filtered(
                lambda line: line.functional_supervisor_rating < 1):
                raise ValidationError(
                    "Ops! Please ensure all functional manager's rating on KRA section is at least 1"
                ) 
            
    def check_fc_section_lines(self):
        if self.state == "admin_rating":
            if self.mapped('fc_section_line_ids').filtered(
                lambda line: line.administrative_supervisor_rating < 1):
                raise ValidationError(
                    "Ops! Please ensure all administrative supervisor's rating on functional competency section is at least 1"
                )
        elif self.state == "functional_rating":
            if self.mapped('fc_section_line_ids').filtered(
                lambda line: line.functional_supervisor_rating < 1):
                raise ValidationError(
                    "Ops! Please ensure all functional manager's rating on functional competency line is at least 1"
                )

        elif self.state == "reviewer_rating":
            if self.mapped('fc_section_line_ids').filtered(
                lambda line: line.reviewer_rating < 1):
                raise ValidationError(
                    "Ops! Please ensure all reviewers manager rating's on functional competency line is at least rated 1"
                ) 
            
    def check_lc_section_lines(self):
        if self.state == "admin_rating":
            if self.mapped('lc_section_line_ids').filtered(
                lambda line: line.administrative_supervisor_rating < 1):
                raise ValidationError(
                    "Ops! Please ensure all administrative supervisor's rating at leadership competency is at least 1"
                )
        elif self.state == "functional_rating":
            if self.mapped('lc_section_line_ids').filtered(
                lambda line: line.functional_supervisor_rating < 1):
                raise ValidationError(
                    "Ops! Please ensure all functional manager's rating at leadership competency is at least 1"
                )

        elif self.state == "reviewer_rating":
            if self.mapped('lc_section_line_ids').filtered(
                lambda line: line.reviewer_rating < 1):
                raise ValidationError(
                    "Ops! Please ensure all reviewer's rating at leadership competency is at least 1"
                )
    def check_current_potential_assessment_section_lines(self):
        if self.state == "admin_rating":
            if self.mapped('current_assessment_section_line_ids').filtered(
                lambda line: line.name == "Administrative Appraiser" and line.assessment_type == False):
                raise ValidationError(
                    "Ops! Please ensure all administrative supervisor's rating at current assessment section is at least Ordinary"
                )
            if self.mapped('potential_assessment_section_line_ids').filtered(
                lambda line: line.name == "Administrative Appraiser" and line.assessment_type == False):
                raise ValidationError(
                    "Ops! Please ensure all administrative supervisor's rating at potential assessment section is at least Low potential"
                )
            
        elif self.state == "functional_rating":
            if self.mapped('current_assessment_section_line_ids').filtered(
                lambda line: line.name == "Functional Appraiser" and line.assessment_type == False):
                raise ValidationError(
                    "Ops! Please ensure all functional manager's rating at current assessment section is at least Ordinary"
                )
            if self.mapped('potential_assessment_section_line_ids').filtered(
                lambda line: line.name == "Functional Appraiser" and line.assessment_type == False):
                raise ValidationError(
                    "Ops! Please ensure all  functional manager's rating at potential assessment section is at least Low potential"
                )

        elif self.state == "reviewer_rating":
            if self.mapped('current_assessment_section_line_ids').filtered(
                lambda line: line.name == "Functional Reviewer" and line.assessment_type == False):
                raise ValidationError(
                    "Ops! Please ensure all reviewer's rating at current assessment section is at least "
                ) 
            if self.mapped('potential_assessment_section_line_ids').filtered(
                lambda line: line.name == "Functional Reviewer" and line.assessment_type == False):
                raise ValidationError(
                    "Ops! Please ensure all reviewer's rating at potential assessment section is at least Low potential"
                )
            
    # def check_potential_assessment_section_lines(self):
    #     if self.state == "admin_rating":
    #         if self.mapped('potential_assessment_section_line_ids').filtered(
    #             lambda line: line.administrative_supervisor_rating < 1):
    #             raise ValidationError(
    #                 "Ops! Please ensure all administrative supervisor's rating on potential assessment section is at least 1"
    #             )
    #         if self.mapped('potential_assessment_section_line_ids').filtered(
    #             lambda line: line.administrative_supervisor_rating < 1):
    #             raise ValidationError(
    #                 "Ops! Please ensure all administrative supervisor's rating on potential assessment section is at least 1"
    #             )
    #     elif self.state == "functional_rating":
    #         if self.mapped('potential_assessment_section_line_ids').filtered(
    #             lambda line: line.functional_supervisor_rating < 1):
    #             raise ValidationError(
    #                 "Ops! Please ensure all functional manager's rating on potential assessment section is at least 1"
    #             )

    #     elif self.state == "reviewer_rating":
    #         if self.mapped('potential_assessment_section_line_ids').filtered(
    #             lambda line: line.reviewer_rating < 1):
    #             raise ValidationError(
    #                 "Ops! Please ensure all reviewer's rating on potential assessment section is at least 1"
    #             ) 
        
    def _get_group_users(self):
        group_obj = self.env['res.groups']
        hr_administrator = self.env.ref('hr.group_hr_manager').id
        pms_manager = self.env.ref('hr_pms.group_pms_manager_id').id
        pms_officer = self.env.ref('hr_pms.group_pms_officer_id').id
        hr_administrator_user = group_obj.browse([hr_administrator])
        pms_manager_user = group_obj.browse([pms_manager])
        pms_officer_user = group_obj.browse([pms_officer])

        hr_admin = hr_administrator_user.mapped('users') if hr_administrator_user else False
        pms_mgr = pms_manager_user.mapped('users') if pms_manager_user else False
        pms_off = pms_officer_user.mapped('users') if pms_officer_user else False
        return hr_admin, pms_mgr, pms_off
    
    def submit_mail_notification(self): 
        subject = "Appraisal Notification"
        department_manager = self.employee_id.parent_id or self.employee_id.parent_id
        supervisor = self.employee_id.administrative_supervisor_id
        reviewer_id = self.employee_id.reviewer_id
        hr_admin, pms_mgr, pms_off = self._get_group_users()
        hr_emails = [rec.login for rec in hr_admin]
        pms_mgr_emails = [rec.login for rec in pms_mgr]
        pms_off_emails = [rec.login for rec in hr_admin]
        hr_logins = hr_emails + pms_mgr_emails + pms_off_emails
        if not hr_logins:
            raise ValidationError('Please ensure there is a user with HR addmin settings')
        if self.state in ['draft']:
            if department_manager and department_manager.work_email:
                msg = """Dear {}, <br/>
                I wish to notify you that my appraisal has been submitted to you for rating(s) \
                <br/>Kindly {} to proceed with the ratings <br/>\
                Yours Faithfully<br/>{}<br/>Department: ({})""".format(
                    department_manager.name,
                    self.get_url(self.id, self._name),
                    self.env.user.name,
                    self.employee_id.department_id.name,
                    )
                email_to = department_manager.work_email
                email_cc = [
                    supervisor.work_email, 
                    reviewer_id.work_email,
                ]
            else:
                raise ValidationError(
                    'Please ensure that employee / department \
                    manager has an email address')
        elif self.state in ['rating']:
            msg = """HR, <br/>
                I wish to notify you that an appraisal for {} \
                has been submitted for HR processing\
                <br/>Kindly {} to review the appraisal<br/>\
                Yours Faithfully<br/>{}<br/>""".format(
                    self.employee_id.name,
                    self.get_url(self.id, self._name),
                    self.env.user.name,
                    )
            email_to = ','.join(hr_logins)
            email_cc = [
                    supervisor.work_email, 
                    reviewer_id.work_email,
                ]
        elif self.state in ['wating_approval']:
            msg = """HR, <br/>
                I wish to notify you that an appraisal for {} has been completed.\
                <br/>Kindly {} to review the appraisal. <br/> \
                For further Inquiry, contact HR Department<br/>\
                Yours Faithfully<br/>{}<br/>""".format(
                    self.employee_id.name,
                    self.get_url(self.id, self._name),
                    self.env.user.name,
                    )
            email_to = self.employee_id.work_email
            email_cc = [
                    supervisor.work_email, 
                    reviewer_id.work_email,
                    department_manager.work_email
                ]
        else:
            msg = "-"
            email_to = department_manager.work_email
            email_cc = [
                    supervisor.work_email, 
                    reviewer_id.work_email,
                ]
        self.action_notify(
            subject, 
            msg, 
            email_to, 
            email_cc)
        
    def get_email_from(self):
        email_from = ""
        if self.state in ["goal_setting_draft", 'hyr_draft']:
            email_from = self.employee_id.work_email
        if self.state in ["gs_fa", "hyr_functional_rating", "functional_rating"]:
            email_from = self.manager_id.work_email
        if self.state == "admin_rating":
            email_from = self.administrative_supervisor_id.work_email
        if self.state == "reviewer_rating":
            email_from = self.reviewer_id.work_email
        return email_from
        
    def action_notify(self, subject, msg, email_to, email_cc):
        sender_email_from = self.env.user.email
        email_from = sender_email_from or self.get_email_from()
        if email_to and email_from:
            email_ccs = list(filter(bool, email_cc))
            reciepients = (','.join(items for items in email_ccs)) if email_ccs else False
            mail_data = { 
                    'email_from': f'"Layer3" <notifications@layer3.com.ng>',
                    # 'email_from': f'"Appraisal Notification" <{email_from}>',
                    'subject': subject,
                    'email_to': email_to,
                    'reply_to': email_from,
                    'email_cc': reciepients,
                    'body_html': msg,
                    # 'state': 'sent'
                }
            mail_id = self.env['mail.mail'].sudo().create(mail_data)
            # mail_id.action_send_and_close()
            # self.env['mail.mail'].sudo().send(mail_id)
            # self.message_post(body=msg)
    
    def get_url(self, id, name):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_id = self.env.ref('hr_pms.action_pms_appraisee_view_id')
        base_url += f'/odoo/action-{action_id.id}/{id}'
        # base_url += '/web#id=%d&view_type=form&model=%s' % (id, name)
        return "<a href={}> </b>Click<a/>. ".format(base_url)

    def action_send_reminder(self):
        msg = """Dear Sir/Madam, <br/> 
            I wish to remind you of the appraisal(s) currently on your desk. <br/>
            Please kindly review and do the needful.<br/>
            Regards<br/>
            HR Administrator <br/><br/>
            Should you require any additional information, please contact ICT support for help.<br/>
            <a href='https://odoo.layer3.ng' target="_blank">Click ICT Support link</a><br/>"""
        subject = "Appraisal Reminder"
        email_to = self.employee_id.work_email or self.administrative_supervisor_id.work_email or self.manager_id.work_email if self.state in ['draft', 'done', 'reviewer_rating'] else \
            self.administrative_supervisor_id.work_email if self.state == "admin_rating" else \
            self.manager_id.work_email if self.state == "functional_rating" else self.reviewer_id.work_email if self.state == "reviewer_rating" else self.employee_id.work_email
        email_cc = self.employee_id.work_email
        # self.action_notify(subject, msg, email_to, email_cc)
        self.mail_sending(subject, msg, email_to, email_cc)

    def mail_sending(self, subject, msg_body, email_to, email_cc):
        email_from = self.write_uid.company_id.email or self.env.user.email
        mail_data = {
                # 'email_from': f'"Appraisal Notification" <{email_from}>',
                'email_from': f'"LAYER3" <notifications@layer3.com.ng>',
                'subject': subject,
                'email_to': email_to,
                'reply_to': False,
                'email_cc': email_cc, # emails if self.users_followers else [],
                'body_html': msg_body
            }
        if email_from and email_to:
            mail_id = self.env['mail.mail'].sudo().create(mail_data)
            self.env['mail.mail'].sudo().send(mail_id)
            # mail_id.action_send_and_close()

    def mass_send_reminder(self):
        rec_ids = self.env.context.get('active_ids', [])
        for record in rec_ids:
            rec = self.env['pms.appraisee'].browse([record])
            msg = """Dear Sir/Madam, <br/> 
                I wish to remind you of the appraisal(s) currently on your desk. <br/>
                Please kindly rate and submit before the submission deadline.
                You can choose to ignore if necessary process has been done. <br/>
                Regards<br/> 
                HR Administrator<br/>
                Should you require any additional information, please contact ICT support for help.<br/>
                <a href='/apps' target="_blank">Click ICT Support link</a>"""
                
            subject = "Appraisal Reminder"
            email_to = rec.employee_id.work_email or rec.administrative_supervisor_id.work_email or rec.manager_id.work_email if rec.state in ['draft', 'done', 'reviewer_rating'] else \
                rec.administrative_supervisor_id.work_email if self.state == "admin_rating" else \
                rec.manager_id.work_email if rec.state == "functional_rating" else rec.reviewer_id.work_email if rec.state == "reviewer_rating" else rec.employee_id.work_email
            email_cc = rec.employee_id.work_email
            # rec.action_notify(subject, msg, email_to, email_cc)
            self.mail_sending(subject, msg, email_to, email_cc)

    def bulk_copy_appraisal(self):
        rec_ids = self.env.context.get('active_ids', [])
        for record in rec_ids:
            rec = self.env['pms.appraisee'].browse([record])
            if rec.state not in ['draft', 'goal_setting_draft']:
                raise UserError('You cannot duplicate this record !!!')
            else:
                rec.copy()
                rec.lock_fields = True

    def update_instruction(self):
        rec_ids = self.env.context.get('active_ids', [])
        for record in rec_ids:
            rec = self.env['pms.appraisee'].browse([record])
            rec.write({'instruction_html': rec.env.ref('hr_pms.pms_instruction_1').description})

    def post_normalisation_upload_action(self):
        rec_ids = self.env.context.get('active_ids', [])
        return {
              'name': 'Post Normalisation Upload',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'pms.post_normalisation.wizard',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_appraisal_ids': rec_ids,
                #   'default_date': fields.Datetime.now(),
                #   'default_direct_employee_id': self.employee_id.id,
                #   'default_resp':self.env.uid,
              },
        }

    
    def send_mail_notification(self, msg):
        subject = "Appraisal Notification"
        administrative_supervisor = self.employee_id.administrative_supervisor_id
        reviewer_id = self.employee_id.reviewer_id
        # doing this to avoid making calls that will impact optimization
        department_manager = self.employee_id.parent_id
        if self.state == "goal_setting_draft":
            email_to = department_manager.work_email
            email_cc = [
            department_manager.work_email,
            administrative_supervisor.work_email,
        ]
        elif self.state == "gs_fa":
            email_to = self.employee_id.work_email
            email_cc = [
            department_manager.work_email,
            administrative_supervisor.work_email,
        ]
        elif self.state == "hyr_draft":
            email_to = administrative_supervisor.work_email if self.administrative_supervisor_id.work_email else department_manager.work_email
            email_cc = [
            department_manager.work_email,
            administrative_supervisor.work_email,
        ]
        elif self.state == "hyr_admin_rating":
            email_to = department_manager.work_email
            email_cc = [
                department_manager.work_email,
                self.employee_id.work_email
                ]
        elif self.state == "hyr_functional_rating":
            email_to = self.employee_id.work_email
            email_cc = [
                department_manager.work_email,
                administrative_supervisor.work_email,
                ]
            
        elif self.state == "draft":
            email_to = administrative_supervisor.work_email if self.administrative_supervisor_id.work_email else department_manager.work_email
            email_cc = [
            department_manager.work_email,
            reviewer_id.work_email, 
            administrative_supervisor.work_email,
        ]
        elif self.state == "admin_rating":
            email_to = department_manager.work_email
            email_cc = [
                department_manager.work_email,
                self.employee_id.work_email
                ]
        elif self.state == "functional_rating":
            email_to = reviewer_id.work_email
            email_cc = [
                department_manager.work_email,
                self.employee_id.work_email,
                administrative_supervisor.work_email,
                ]
        elif self.state == "reviewer_rating":
            email_to = self.employee_id.work_email,
            email_cc = [
                department_manager.work_email,
                administrative_supervisor.work_email,
                ]
        else:
            email_to = department_manager.work_email,
            email_cc = [
                department_manager.work_email,
                administrative_supervisor.work_email,
                ]
        self.action_notify(subject, msg, email_to, email_cc)

    def validate_weightage(self):
        kra_line = self.sudo().pms_department_id.mapped('section_line_ids').filtered(
                    lambda res: res.type_of_section == "KRA")
        if kra_line:
            max_line_number = kra_line[0].max_line_number
            min_line_number = kra_line[0].min_line_number
            min_limit = 5
            max_limit = 7
            if max_line_number > 0:
                max_limit = max_line_number
                min_limit = min_line_number
            else:
                category_kra_line = self.sudo().pms_department_id.hr_category_id.sudo().mapped('section_ids').filtered(
                    lambda res: res.type_of_section == "KRA")
                min_category_line_number = category_kra_line[0].min_line_number if category_kra_line and category_kra_line[0].max_line_number > 0 else min_limit
                max_category_line_number = category_kra_line[0].max_line_number if category_kra_line and category_kra_line[0].max_line_number > 0 else max_limit
                max_limit = max_category_line_number
                min_limit = min_category_line_number
            
            type_kra_section_ids = self.hyr_kra_section_line_ids.ids if self.type_of_pms == 'hyr' else self.kra_section_line_ids.ids
            if len(type_kra_section_ids) not in range(min_limit, max_limit + 1): # not in [5, 6, limit]:
                raise ValidationError("""Please ensure the number of KRA / Achievement section is within the range of {} to {} line(s)""".format(int(min_limit), int(max_limit)))
        type_kra_section_line = 'hyr_kra_section_line_ids' if self.state == 'hyr' else 'kra_section_line_ids'
        # sum_weightage = sum([weight.appraisee_weightage for weight in self.mapped(type_kra_section_line)])
        # if sum_weightage != 100 and self.type_of_pms == 'fyr':
        #     value_diff = 100 - sum_weightage 
        #     needed_value_msg = f'''You need to add {value_diff}%''' if value_diff > 0 else f'''You need to deduct {abs(value_diff)}%'''
        #     raise ValidationError(
        #         f"""Please ensure the sum of KRA weight by Appraisee is equal to 100 %.\n {needed_value_msg} weightage to complete it"""
        #         )
        # weightage_with_zero = self.mapped(type_kra_section_line).filtered(lambda self: self.appraisee_weightage < 1)
        # if weightage_with_zero and self.type_of_pms == 'fyr':
        #     raise ValidationError(
        #         """Please ensure that each line weightage is above 0. Either delete the extra line or add a weight on it"""
        #         )
        self_rating_with_zero = self.mapped(type_kra_section_line).filtered(lambda self: self.self_rating < 1)
        if self_rating_with_zero and self.type_of_pms == 'fyr':
            raise ValidationError(
                """Please ensure that each line's self rating is above 0. Either delete the line or add a self rating"""
                )
        
    def validate_deadline(self):
        appraisee_deadline = self.sudo().pms_department_id.hr_category_id.online_deadline_date
        deadline = self.sudo().pms_department_id.hr_category_id.deadline
        if appraisee_deadline and fields.Date.today() > appraisee_deadline:
            raise ValidationError('Your deadline for submission has exceeded !!!')
        if deadline and fields.Date.today() > deadline:
            raise ValidationError('You have exceeded deadline for the submission of your appraisal')

    def validate_hyr_rating(self):
        hyr_lines = self.mapped('hyr_kra_section_line_ids')
        validity_msg = []
        msg = """
        Please fill progress status and comments of all KRA lines. 
        Also ensure the revise weightage is not less than 5"""
        if self.state == "hyr_admin_rating":
            non_rated_aa_hyr_lines = hyr_lines.filtered(lambda hyr: hyr.hyr_aa_rating == False)
            if non_rated_aa_hyr_lines:
                validity_msg.append(msg)
            if self.supervisor_comment == "":
                validity_msg.append("""Please Ensure you provide supervisor's comment""")
        if self.state == "hyr_functional_rating":
            non_rated_fa_hyr_lines = hyr_lines.filtered(lambda hyr: hyr.hyr_fa_rating == False and hyr.acceptance_status != "Dropped") # or hyr.revise_weightage < 5 and hyr.acceptance_status != "Dropped")
            if non_rated_fa_hyr_lines:
                validity_msg.append(msg)
            if self.manager_comment == "":
                validity_msg.append("""Please Ensure you provide manager's comment""")
            # sum_reverse_weightage_weightage = sum([weight.reverse_weightage for weight in self.mapped('hyr_kra_section_line_ids')])
            weightage = sum([weight.revise_weightage for weight in self.mapped('hyr_kra_section_line_ids')])
            if weightage != 100:
                value_diff = 100 - weightage 
                needed_value_msg = f'''You need to add {value_diff}%''' if value_diff > 0 else f'''You need to deduct {abs(value_diff)}%'''
                raise ValidationError(
                    f"""Ensure KRA weight by FA is equal to 100 %.\n {needed_value_msg} weightage to complete it"""
                    )
            # if sum_reverse_weightage_weightage != 100:
            #     value_diff = 100 - sum_reverse_weightage_weightage 
            #     needed_value_msg = f'''You need to add {value_diff}%''' if value_diff > 0 else f'''You need to deduct {abs(value_diff)}%'''
            #     raise ValidationError(
            #         f"""Reverse KRA weight was tampered. Please ensure the sum of reverse KRA weight by FA is equal to 100 %.\n {needed_value_msg} weightage to complete it"""
            #         )
        if validity_msg:
            error_msg = '\n'.join(validity_msg)
            raise ValidationError(error_msg)
        
    def validate_kra_setting(self):
        if self.state in ["goal_setting_draft"]:
            weightage = sum([
                weight.weightage for weight in self.mapped(
                'goal_setting_section_line_ids'
                )])
            if weightage != 100:
                value_diff = 100 - weightage 
                needed_value_msg = f'''You need to add {value_diff}%''' if value_diff > 0 else f'''You need to deduct {abs(value_diff)}%'''
                raise ValidationError(
                    f"""Ensure KRAs weight with acceptance status is 'YES' is equal to 100 %.\n {needed_value_msg} weightage to complete it"""
                    )
        elif self.state in ["gs_fa"]:
            weightage = sum([
                weight.weightage for weight in self.mapped(
                'goal_setting_section_line_ids'
                ).filtered(
                lambda self: self.acceptance_status == "yes"
                )])
            if weightage != 100:
                value_diff = 100 - weightage 
                needed_value_msg = f'''
                You need to add {value_diff}%''' if value_diff > 0 else f'''You need to deduct {abs(value_diff)}%'''
                raise ValidationError(
                    f"""Ensure KRAs weight with acceptance status is 'YES' is equal to 100 %.\n {needed_value_msg} weightage to complete it"""
                    )
            
        elif self.state == "hyr_draft":
            weightage = sum([weight.revise_weightage for weight in self.mapped('hyr_kra_section_line_ids').filtered(lambda self: self.acceptance_status in ["Revised", "Accepted"])])
            if weightage != 100:
                value_diff = 100 - weightage 
                needed_value_msg = f'''You need to add {value_diff}%''' if value_diff > 0 else f'''You need to deduct {abs(value_diff)}%'''
                raise ValidationError(
                    f"""Ensure KRAs weight with acceptance status is 'Accepted' is equal to 100 %.\n {needed_value_msg} weightage to complete it"""
                    )
            
    def overall_validate_weightage(self):
        kra_line = self.sudo().pms_department_id.mapped('section_line_ids').filtered(
                    lambda res: res.type_of_section == "KRA")
        if kra_line:
            max_line_number = kra_line[0].max_line_number
            min_line_number = kra_line[0].min_line_number
            min_limit = 5
            max_limit = 7
            if max_line_number > 0:
                max_limit = max_line_number
                min_limit = min_line_number
            else:
                category_kra_line = self.sudo().pms_department_id.hr_category_id.sudo().mapped('section_ids').filtered(
                    lambda res: res.type_of_section == "KRA")
                min_category_line_number = category_kra_line[0].min_line_number if category_kra_line and category_kra_line[0].max_line_number > 0 else min_limit
                max_category_line_number = category_kra_line[0].max_line_number if category_kra_line and category_kra_line[0].max_line_number > 0 else max_limit
                max_limit = max_category_line_number
                min_limit = min_category_line_number
            type_kra_section_ids = self.goal_setting_section_line_ids.ids if self.type_of_pms == 'gs' else self.hyr_kra_section_line_ids.ids if self.type_of_pms == 'hyr' else self.kra_section_line_ids.ids
            if len(type_kra_section_ids) not in range(min_limit, max_limit + 1): # not in [5, 6, limit]:
                raise ValidationError("""Please ensure the number of KRA / Achievement section is within the range of {} to {} line(s)""".format(int(min_limit), int(max_limit)))

    def check_employee_right(self):
        self.ensure_one()
        if not self.employee_id.user_id.id == self.env.uid:
            raise ValidationError("Sorry!!! You are not allowed to submit this record")
    
    # def check_manager_right(self):
    #     self.ensure_one()
    #     if not self.manager_id.user_id.id == self.env.uid:
    #         raise ValidationError("Sorry!!! Only the employee manager is allowed to submit this record")
        
    def goal_setting_button_submit(self):
        self.lock_fields = False
        self.validate_deadline()
        self.overall_validate_weightage()
        self.validate_kra_setting()
        self.check_employee_right()
        msg = """Dear {}, <br/> 
        I wish to notify you that my PMS Goal Settings {} \
        has been submitted for approval.\
        <br/>Kindly {} to review <br/>\
        Yours Faithfully<br/>{}<br/>HR Department ({})""".format(
            self.manager_id.name or self.employee_id.parent_id.name,
            self.employee_id.name,
            self.get_url(self.department_id.id, self._name),
            self.env.user.name,
            self.department_id.name,
            )
        # self.generate_hyr_kra_lines()
        self.send_mail_notification(msg)
        self.write({
                'state': 'gs_fa',
                'submitted_date': fields.Date.today(),
                'manager_id': self.employee_id.parent_id.id,
            })
        
    def manager_submit_goal_setting_button(self):
        self.lock_fields = False
        self.validate_deadline()
        self.overall_validate_weightage()
        self.validate_kra_setting()
        self.check_employer_manager()
        msg = """Dear {}, <br/> 
        I wish to notify you that an employee PMS Goal Settings {} \
        has been submitted for review.\
        <br/>Kindly {} to review <br/>\
        Yours Faithfully<br/>{}<br/>HR Department ({})""".format(
            self.manager_id.name or self.employee_id.parent_id.name,
            self.employee_id.name,
            self.get_url(self.department_id.id, self._name),
            self.env.user.name,
            self.department_id.name,
            )
        self.generate_hyr_kra_lines()
        self.send_mail_notification(msg)
        self.write({
                'name': f'MID Year Review for {self.employee_id.name}', 
                'state': 'hyr_draft',
                'submitted_date': fields.Date.today(),
                'type_of_pms': 'hyr',
            })
        
    def generate_hyr_kra_lines(self):
        """Generates HYR Section lines"""
        self.hyr_kra_section_line_ids = False #.unlink()
        self.write({
            'state': 'hyr_draft',
            'type_of_pms': 'hyr',
            'pms_year_id': self.pms_year_id.id, #self.env.ref('hr_pms.pms_year_2023_md').id,
            'hyr_kra_section_line_ids': [(0, 0, {
                'hyr_kra_section_id': self.id,
                'name': hyr_line.name,
                'pms_uom': hyr_line.pms_uom, 
                'weightage': hyr_line.weightage,
                'revise_weightage': hyr_line.weightage if hyr_line.acceptance_status == 'yes' else 0,
                'target': hyr_line.target,
                'revise_target': hyr_line.target,
                'enable_line_edit': 'no',
                'acceptance_status': 'Dropped' if hyr_line.acceptance_status == 'no' else 'Accepted',
                }) for hyr_line in self.goal_setting_section_line_ids],
        })

    def check_review_period(self):
        """args: state is either 'hyr_draft' or 'draft' """
        allow_mid_year_review = self.pms_department_id.sudo().hr_category_id.allow_mid_year_review   
        allow_annual_review_submission = self.pms_department_id.sudo().hr_category_id.allow_annual_review_submission
        if self.state == "hyr_draft" and not allow_mid_year_review:
            raise ValidationError("Mid year Review is not yet open for submission now. Try Later")
        elif self.state == "draft" and not allow_annual_review_submission:
            raise ValidationError("Full Appraisal is not yet open for submission now. Try Later")
            
    def hyr_button_submit(self):
        # send notification
        self.check_review_period()
        self.lock_fields = False
        self.validate_deadline()
        self.validate_weightage()
        self.validate_kra_setting()
        admin_or_functional_user = self.administrative_supervisor_id.name or self.manager_id.name
        msg = """Dear {}, <br/> 
        I wish to notify you that an appraisal for {} \
        has been submitted for review.\
        <br/>Kindly {} to review <br/>\
        Yours Faithfully<br/>{}<br/>HR Department ({})""".format(
            admin_or_functional_user,
            self.employee_id.name,
            self.get_url(self.department_id.id, self._name),
            self.env.user.name,
            self.department_id.name,
            )
        self.send_mail_notification(msg)
        self.write({
            'state': 'hyr_functional_rating',
            'submitted_date': fields.Date.today(),
            'manager_id': self.employee_id.parent_id.id,
            'type_of_pms': 'hyr'
        })

    def hyr_button_admin_supervisor_rating(self): 
        self.validate_hyr_rating()
        if not self.employee_id.parent_id:
            raise ValidationError(
                'Ops ! please ensure that a manager is assigned to the employee'
                )
        if self.employee_id.administrative_supervisor_id and self.env.user.id != self.administrative_supervisor_id.user_id.id:
            raise ValidationError(
                "Ops ! You are not entitled to submit this rating because you are not the employee's administrative supervisor"
                )
        msg = """Dear {}, <br/> 
        I wish to notify you that an appraisal for {} \
        has been submitted for functional manager's review.\
        <br/>Kindly {} to review <br/>\
        Yours Faithfully<br/>{}<br/>HR Department ({})""".format(
            self.employee_id.parent_id.name,
            self.employee_id.name,
            self.get_url(self.department_id.id, self._name),
            self.env.user.name,
            self.administrative_supervisor_id.department_id.name,
            )
        
        self.send_mail_notification(msg)
        self.write({
                'state': 'hyr_functional_rating',
                'manager_id': self.employee_id.parent_id.id,
                'type_of_pms': 'hyr'
            })
        
    def hyr_button_functional_manager_rating(self):
        self.validate_hyr_rating()
        if self.employee_id.parent_id and self.env.user.id != self.employee_id.parent_id.user_id.id:
            raise ValidationError(
                "Ops ! You are not entitled to submit this rating because you are not the employee's functional manager"
                )
        msg = """Dear {}, <br/> 
        I wish to notify you that an appraisal for {} \
        has been submitted for reviewer's ratings.\
        <br/>Kindly {} to review <br/>\
        Yours Faithfully<br/>{}<br/> ({})""".format(
            self.employee_id.parent_id.name,
            self.employee_id.name,
            self.get_url(self.department_id.id, self._name),
            self.env.user.name,
            self.manager_id.department_id.name,
            )
        self.generate_kra_lines()
        self.send_mail_notification(msg)
         
    def generate_kra_lines(self):
        self.kra_section_line_ids = False #.unlink()
        self.write({
            'state': 'draft',
            'type_of_pms': 'fyr',
            'pms_year_id': self.pms_year_id.id, #self.env.ref('hr_pms.pms_year_2022_ap').id,
            'name': f'Appraisal - PMS for {self.employee_id.name}', 
            'kra_section_line_ids': [(0, 0, {
                'kra_section_id': self.id,
                'name': hyr_line.name,
                'section_avg_scale': self.dummy_kra_section_scale, # hyr_line.section_avg_scale,
                'weightage': hyr_line.revise_weightage,
                'appraisee_weightage': hyr_line.revise_weightage,
                'target': hyr_line.target,
                'self_rating': 0,
                'administrative_supervisor_rating': 0,
                'functional_supervisor_rating': 0,
                'hyr_fa_rating': hyr_line.hyr_fa_rating,
                'hyr_aa_rating': hyr_line.hyr_aa_rating,
                }) for hyr_line in self.mapped('hyr_kra_section_line_ids').filtered(lambda s: s.acceptance_status in ["Revised", "Accepted"])],
        })

    def button_submit(self):
        # send notification
        self.check_review_period()
        self.lock_fields = False
        self.validate_deadline()
        self.validate_weightage()
        admin_or_functional_user = self.administrative_supervisor_id.name or self.manager_id.name
        msg = """Dear {}, <br/> 
        I wish to notify you that an appraisal for {} \
        has been submitted for ratings.\
        <br/>Kindly {} to review <br/>\
        Yours Faithfully<br/>{}<br/>HR Department ({})""".format(
            admin_or_functional_user,
            self.employee_id.name,
            self.get_url(self.department_id.id, self._name),
            self.env.user.name,
            self.department_id.name,
            )
        self.send_mail_notification(msg)
        
        if self.employee_id.administrative_supervisor_id:
            self.write({
                'state': 'admin_rating',
                'submitted_date': fields.Date.today(),
                'administrative_supervisor_id': self.employee_id.administrative_supervisor_id.id,
            })
        else:
            self.write({
                'state': 'functional_rating',
                'submitted_date': fields.Date.today(),
                'manager_id': self.employee_id.parent_id.id,
            })
        self.compute_score()

    def back_forth_button_test(self):
        self.state = "hyr_draft"

    
    def button_admin_supervisor_rating(self): 
        msg = """Dear {}, <br/> 
        I wish to notify you that an appraisal for {} \
        has been submitted for functional manager's ratings.\
        <br/>Kindly {} to review <br/>\
        Yours Faithfully<br/>{}<br/>HR Department ({})""".format(
            self.employee_id.parent_id.name,
            self.employee_id.name,
            self.get_url(self.department_id.id, self._name),
            self.env.user.name,
            self.administrative_supervisor_id.department_id.name,
            )
        if not self.employee_id.parent_id:
            raise ValidationError(
                'Ops ! please ensure that a manager is assigned to the employee'
                )
        if self.employee_id.administrative_supervisor_id and self.env.user.id != self.administrative_supervisor_id.user_id.id:
            raise ValidationError(
                "Ops ! You are not entitled to submit this rating because you are not the employee's administrative supervisor"
                )
        self.check_kra_section_lines()
        self.check_fc_section_lines()
        self.check_lc_section_lines()
        self.check_current_potential_assessment_section_lines()
        # self.check_current_assessment_section_lines()
        # self.check_potential_assessment_section_lines()
        self.send_mail_notification(msg)
        self.write({
                'state': 'functional_rating',
                'manager_id': self.employee_id.parent_id.id,
            })
        # if self.supervisor_attachement_ids:
        #         self.supervisor_attachement_ids.write({'res_model': self._name, 'res_id': self.id})
        self.compute_score()

    def button_functional_manager_rating(self):
        sum_weightage = sum([weight.weightage for weight in self.mapped('kra_section_line_ids')])
        if sum_weightage != 100:
            value_diff = 100 - sum_weightage 
            needed_value_msg = f'''You need to add {value_diff}%''' if value_diff > 0 else f'''You need to deduct {abs(value_diff)}%'''
            raise ValidationError(
                f"""Please ensure the sum of KRA weight by Functional Appraiser is equal to 100 %.\n {needed_value_msg} weightage to complete it"""
                )
        
        if self.employee_id.parent_id and self.env.user.id != self.employee_id.parent_id.user_id.id:
            raise ValidationError(
                "Ops ! You are not entitled to submit this rating because you are not the employee's functional manager"
                )
        self.check_kra_section_lines()
        self.check_fc_section_lines()
        self.check_lc_section_lines()
        self.check_current_potential_assessment_section_lines()
        # self.check_current_assessment_section_lines()
        # self.check_potential_assessment_section_lines()
        msg = """Dear {}, <br/> 
        I wish to notify you that an appraisal for {} \
        has been submitted for reviewer's ratings.\
        <br/>Kindly {} to review <br/>\
        Yours Faithfully<br/>{}<br/> ({})""".format(
            self.employee_id.parent_id.name,
            self.employee_id.name,
            self.get_url(self.department_id.id, self._name),
            self.env.user.name,
            self.manager_id.department_id.name,
            )
        self.send_mail_notification(msg)
        self.write({
                'state': 'reviewer_rating' if self.employee_id.reviewer_id else 'done',
                'reviewer_id': self.employee_id.reviewer_id.id if self.employee_id.reviewer_id else False,
            })
        # if self.manager_attachement_ids:
        #         self.manager_attachement_ids.write({'res_model': self._name, 'res_id': self.id})
        self.compute_score()

    def button_reviewer_manager_rating(self):
        if self.employee_id.reviewer_id and self.env.user.id != self.employee_id.reviewer_id.user_id.id:
            raise ValidationError(
                "Ops ! You are not entitled to submit this rating because you are not the employee's reviewing manager"
                )
        self.check_fc_section_lines()
        self.check_lc_section_lines()
        self.check_current_potential_assessment_section_lines()
        msg = """Dear {}, <br/> 
        I wish to notify you that your appraisal has been reviewed successfully.<br/>\
        Kindly go to the 'Appraisees comment and Attachment Tab --> Select the perception on PMS options and then save.<br/>\
        Yours Faithfully<br/>{}<br/>HR Department ({})""".format(
            self.employee_id.name,
            self.env.user.name,
            self.reviewer_id.department_id.name,
            )
        self.send_mail_notification(msg)
        self.write({
                'state': 'done',
            })
        # if self.reviewer_attachement_ids:
        #         self.reviewer_attachement_ids.write({'res_model': self._name, 'res_id': self.id})
        self.compute_score()

    def _check_lines_if_appraisers_have_rated(self):
        kra_section_line_ids = self.mapped('kra_section_line_ids').filtered(lambda s: s.administrative_supervisor_rating > 0 or s.functional_supervisor_rating > 0)
        if self.employee_id and self.env.user.id != self.employee_id.user_id.id:
            raise ValidationError(
                "Ops ! You are not entitled to withdraw the employee's appraisal"
                )
        if kra_section_line_ids:
            raise ValidationError('You cannot withdraw this document because appraisers has started ratings on it')
        
    
    def button_withdraw(self):
        self._check_lines_if_appraisers_have_rated()
        self.write({
                'state':'draft',
            })
        
    def button_set_to_draft(self):
        self.write({
                'state':'draft',
            })
    
    def validate_reviewer_commenter(self, vals):
        old_comment = vals.get('reviewer_comment')
        if old_comment and self.state == 'reviewer_rating':
            if self.employee_id.reviewer_id and self.env.user.id != self.employee_id.reviewer_id.user_id.id:
                raise UserError("Ops ! You are not entitled to add a review comment because you are not the employee's reviewer")
        
    def unlink(self):
        sys_admin = self.env.user.has_group("base.group_system")
        for delete in self: # .filtered(lambda delete: delete.state in ['Sent','Approve2', 'Approve']):
            assessed_user = delete.create_uid.id == delete.env.uid or sys_admin
            if delete.state not in ['goal_setting_draft', 'draft']:
                # if not assessed_user: 
                raise ValidationError(_('You cannot delete a appraisal which is not in draft state.'))
        return super(PMS_Appraisee, self).unlink()

    def write(self, vals): 
        self.validate_reviewer_commenter(vals)
        res = super().write(vals)
         
    def _get_non_draft_pms(self):
        pms = self.env['pms.appraisee'].search_count([('state', '!=', 'draft')])
        return int(pms) if pms else 0
    
    def _get_overdue_pms(self):
        submitted_pms = self.env['pms.appraisee'].search(
            [('state', 'in', ['admin_rating', 'functional_rating'])])
        total_overdue = 0
        if submitted_pms:
            # dd = (submitted_pms[0].submitted_date - submitted_pms[0].create_date).days
            # raise ValidationError(dd)
            total_overdue = len([rec for rec in submitted_pms if (rec.submitted_date - rec.create_date).days > 2])
        return total_overdue
    
    def _get_completed_pms(self):
        pms = self.env['pms.appraisee'].search_count([('state', 'in', ['done', 'signed'])])
        return int(pms) if pms else 0
    
    def _get_perception_pms(self, perception): 
        pms = self.env['pms.appraisee'].search_count([('appraisee_satisfaction', 'in', perception)])
        return int(pms) if pms else 0
    
    def _get_reviewer_pms(self):
        pms = self.env['pms.appraisee'].search_count([('state', '=', 'reviewer_rating')])
        return int(pms) if pms else 0
    
    def _get_draft_pms(self):
        pms = self.env['pms.appraisee'].search_count([('state', '=', 'draft')])
        return int(pms) if pms else 0
    
    def _getpms_not_generated(self):
        pms = self.env['pms.appraisee'].search([])
        employees = [rec.id for rec in self.env['hr.employee'].search([])]
        pms_employee_ids = [rec.employee_id.id for rec in pms]
        number_of_intersections = []
        for rec in employees:
            if rec not in pms_employee_ids:
                number_of_intersections.append(rec)
        return len(number_of_intersections)

    @api.model
    def get_dashboard_details(self):
        return {
            '_get_non_draft_pms': self._get_non_draft_pms(),
            '_get_overdue_pms': self._get_overdue_pms(),
            '_get_completed_pms': self._get_completed_pms(),
            '_get_perception_agreed_pms': self._get_perception_pms(['fully_agreed','largely_agreed','partially_agreed']),
            '_get_perception_disagreed_pms': self._get_perception_pms(['totally_disagreed', 'largely_disagreed']),
            '_get_reviewer_pms': self._get_reviewer_pms(),
            '_getpms_not_generated': self._getpms_not_generated(),
            '_get_draft_pms': self._get_draft_pms(),
        }
    
    def overdue_pms(self):
        submitted_pms = self.env['pms.appraisee'].search(
            [('state', 'in', ['admin_rating', 'functional_rating'])])
        total_overdue_ids = [0]
        if submitted_pms:
            total_overdue_ids = [rec.id for rec in submitted_pms if (rec.submitted_date - rec.create_date).days > 2]
        return total_overdue_ids
    
    def compute_current_user(self):
        for rec in self:
            if rec.employee_id.user_id.id == self.env.user.id and rec.state not in ['draft','done', 'signed']:
                rec.is_current_user = True
            else:
                rec.is_current_user = False

    def compute_functional_appraiser(self):
        if self.manager_id and self.manager_id.user_id.id == self.env.user.id:
            self.is_functional_appraiser = True 
        else:
            self.is_functional_appraiser = False 

    def check_employer_manager(self):
        if self.env.uid not in [self.employee_id.parent_id.user_id.id, self.employee_id.reviewer_id.user_id.id]:
            raise ValidationError("You are not responsible to do this operation")
        
    def _get_appraisal_return_state(self):
        if self.state == 'gs_fa':
            self.state = 'goal_setting_draft'
            self.type_of_pms = 'gs'
        elif self.state == 'hyr_admin_rating':
            self.state = 'hyr_draft' 
            self.type_of_pms = 'hyr'
        elif self.state == 'hyr_functional_rating':
            self.state = 'hyr_draft'
            self.type_of_pms = 'hyr'

        elif self.state == 'draft':
            self.state = 'hyr_functional_rating'
            self.type_of_pms = 'fyr'

        elif self.state == 'hyr_draft':
            self.state = 'goal_setting_draft'
            self.type_of_pms = 'gs'

        elif self.state == 'functional_rating':
            self.state = 'draft'
            self.type_of_pms = "fyr"

        elif self.state == 'admin_rating':
            self.state = 'draft'
            self.type_of_pms = "fyr"

        elif self.state == 'reviewer_rating':
            self.state = 'functional_rating'
            self.type_of_pms = "fyr"

       
        
    def return_appraisal(self):
        self.check_employer_manager()
        return {
              'name': 'Reason for Return',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'pms.back',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_record_id': self.id,
                  'default_date': fields.Datetime.now(),
                  'default_direct_employee_id': self.employee_id.id,
                  'default_resp':self.env.uid,
              },
        }

    def return_appraisal_directly(self):
        self._get_appraisal_return_state()
        msg_body = "Dear Sir/Madam, </br> We wish to notify you that {} appraisal with reference <br/>{} has been returned with reason(s) below; \
             <br/>HR Administrator<br/>\
             Should you require any additional information, please contact ICT support for help.<br/>\
             <a href='notifications@layer3.com.ng'>Click ICT Support link</a>".format(self.employee_id.name, self.name)
        self.mail_sending("Appraisal Rejection", msg_body, self.employee_id.work_email, [self.employee_id.parent_id.work_email, self.employee_id.administrative_supervisor_id.work_email])
    
    def button_goal_setting(self):
        return {
              'name': 'Goal Setting Excel Sheet',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'pms.goal_setting.wizard',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_pms_id': self.id,
                #   'default_date': fields.Datetime.now(),
                #   'default_direct_employee_id': self.employee_id.id,
                #   'default_resp':self.env.uid,
              },
        }


    @api.model
    def create_action(self, domain, title, is_overdue=False):
        domain = domain
        action_ref = 'hr_pms.action_pms_appraisal_view_id'
        search_view_ref = 'hr_pms.view_pms_appraisee_filter'
        action = self.env["ir.actions.actions"]._for_xml_id(action_ref)
        if title:
            action['display_name'] = title
        if search_view_ref:
            action['search_view_id'] = self.env.ref(search_view_ref).read()[0]
        action['views'] = [(False, view) for view in action['view_mode'].split(",")]
        if is_overdue:
            over_dues = self.overdue_pms()
            domain = f"[('id', 'in', {over_dues})]"
        action['domain'] = eval(domain)
        return {'action': action}

    @api.model
    def get_not_generated_employees(self, title):
        def _getpms_not_generated():
            pms = self.env['pms.appraisee'].search([])
            employees = [rec.id for rec in self.env['hr.employee'].search([])]
            pms_employee_ids = [rec.employee_id.id for rec in pms]
            number_of_intersections = []
            for rec in employees:
                if rec not in pms_employee_ids:
                    number_of_intersections.append(rec)
            # number_of_intersections = [emp if emp not in employees else None for emp in pms_employee_ids] # set(employees).intersection(pms_employee_ids)
            return number_of_intersections if number_of_intersections else [0]
        action_ref = 'hr.open_view_employee_list_my'
        search_view_ref = 'hr.view_employee_filter'
        action = self.env["ir.actions.actions"]._for_xml_id(action_ref)
        if title:
            action['display_name'] = title
        if search_view_ref:
            action['search_view_id'] = self.env.ref(search_view_ref).read()[0]
        action['views'] = [(False, view) for view in action['view_mode'].split(",")]
        domain = f"[('id', 'in', {_getpms_not_generated()})]"
        action['domain'] = eval(domain)
        return {'action': action}
    
    # @api.model
    # def create_action(self, action_ref, title, search_view_ref):
    #     action = self.env["ir.actions.actions"]._for_xml_id(action_ref)
    #     if title:
    #         action['display_name'] = title
    #     if search_view_ref:
    #         action['search_view_id'] = self.env.ref(search_view_ref).read()[0]
    #     action['views'] = [(False, view) for view in action['view_mode'].split(",")]
    #     action['domain'] = domain
    #     return {'action': action}


    
        