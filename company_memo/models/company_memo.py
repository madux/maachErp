from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from bs4 import BeautifulSoup
from odoo.tools import consteq, plaintext2html
from odoo import http
import random
from lxml import etree
from bs4 import BeautifulSoup
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class Memo_Model(models.Model):
        
    _name = "memo.model"
    _description = "Internal Memo"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "name"
    _order = "id desc"
     
    
    @api.model
    def create(self, vals):
        code_seq = self.env["ir.sequence"].next_by_code("memo.model") or "REF"
        ms_config = self.env['memo.config'].browse([vals.get('memo_setting_id')])
        project_prefix = 'REF'
        dept_suffix = ''
        user_company = self.env.user.company_id
        if ms_config:
            project_prefix = (
                ms_config.prefix_code or
                ('PMT' if ms_config.memo_key == 'Payment'
                else 'ADV-EXP' if ms_config.memo_key == 'cash_advance'
                else 'EXP' if ms_config.memo_key == 'soe'
                else 'MR' if ms_config.memo_key == 'material_request'
                else 'PR' if ms_config.memo_key == 'procurement_request'
                else 'REF')
            )
            dept_suffix = ms_config.department_code or 'X'
        result = super(Memo_Model, self).create(vals)
        if self.attachment_ids:
            self.attachment_ids.write({'res_model': self._name, 'res_id': self.id})
        if self.invoice_ids:
            for rec in self.invoice_ids:
                rec.memo_id = self.id
        if hasattr(self.env['memo.model'], 'payment_ids'):
            for rec in self.payment_ids:
                rec.memo_reference = result.id
        
        current_month = datetime.now().strftime('%Y/%m')
        
        # result.code = vals['code'] if 'code' in vals and vals.get('code') not in ['', False, None] else f"{project_prefix}/{current_month}/{result.id}"
        result.code = vals['code'] if 'code' in vals and vals.get('code') not in ['', False, None] else f"{project_prefix}/{current_month}/{result.id}"
        return result
    
    def write(self, vals):
        result = super(Memo_Model, self).write(vals)
        
        # Auto-mark cash advance as retired when SOE reaches Done stage
        if 'state' in vals and vals.get('state') == 'Done':
            for rec in self:
                if rec.memo_type_key == 'soe' and rec.cash_advance_reference:
                    rec.cash_advance_reference.sudo().write({
                        'is_cash_advance_retired': True
                    })
                    _logger.info(f"Marked cash advance {rec.cash_advance_reference.code} as retired via SOE {rec.code}")
        
        return result
    
    def action_mark_retired_cash_advances(self):
        """
        Bulk action to mark all cash advances as retired if they have 
        a linked SOE that is in 'Done' state.
        This is for retroactively fixing cash advances that weren't marked retired.
        """
        # Find all cash advances that are not yet marked as retired
        cash_advances = self.env['memo.model'].sudo().search([
            ('memo_type_key', '=', 'cash_advance'),
            ('is_cash_advance_retired', '=', False),
            ('state', '=', 'Done')
        ])
        
        marked_count = 0
        for ca in cash_advances:
            linked_soe = self.env['memo.model'].sudo().search([
                ('cash_advance_reference', '=', ca.id),
                ('memo_type_key', '=', 'soe'),
                ('state', '=', 'Done')
            ], limit=1)
            
            if linked_soe:
                ca.write({'is_cash_advance_retired': True})
                marked_count += 1
                _logger.info(f"Bulk marked cash advance {ca.code} as retired (linked SOE: {linked_soe.code})")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cash Advance Retirement',
                'message': f'Marked {marked_count} cash advances as retired.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].sudo().read_group([
            ('res_model', '=', 'memo.model'), 
            ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for rec in self:
            rec.attachment_number = attachment.get(rec.id, 0)

    def action_get_attachment_view(self):
        action_ref = 'base.action_attachment'
        search_view_ref = 'base.view_attachment_search'
        action = self.env["ir.actions.act_window"].sudo()._for_xml_id(action_ref)
        action['display_name'] = "Documents"
        if search_view_ref:
            action['search_view_id'] = self.env.ref(search_view_ref).read()[0]
        action['views'] = [(False, view) for view in action['view_mode'].split(",")]
        action['context'] = {'default_res_model': 'memo.model', 'default_res_id': self.id}
        documents = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'memo.model'), ('res_id', 'in', [self.id])
            ])
        action['domain'] = [('id', 'in', documents.ids)]
        return action
    
    # default to current employee using the system 
    def _default_employee(self):
        return self.env.context.get('default_employee_id') or \
        self.env['hr.employee'].sudo().with_context(force_company=False).search([('user_id', '=', self.env.uid)], limit=1).id

    def _default_user(self):
        return self.env.context.get('default_user_id') or \
         self.env['res.users'].sudo().search([('id', '=', self.env.uid)], limit=1)
 
    # memo_type = fields.Selection(
    #     [
    #     ("Payment", "Payment"), 
    #     ("loan", "Loan"), 
    #     ("Internal", "Internal Memo"),
    #     ("employee_update", "Employee Update Request"),
    #     ("material_request", "Material request"),
    #     ("procurement_request", "Procurement Request"),
    #     ("vehicle_request", "Vehicle request"),
    #     ("leave_request", "Leave request"),
    #     ("server_access", "Server Access Request"), 
    #     ("cash_advance", "Cash Advance"),
    #     ("soe", "Statement of Expense"),
    #     ("recruitment_request", "Recruitment Request"),
    #     ], string="Request Type", required=True)
    memo_material_request_status = fields.Boolean('')
    memo_procurement_request_status = fields.Boolean('')
    memo_awaiting_procurement_request_status = fields.Boolean('')
    memo_soe_status = fields.Boolean('')
    memo_bagde_status = fields.Boolean('')
    # USED TO MIGRATE OLD ERP DATA SUCH AS CASH ADVANCE
    migrated_legacy_id = fields.Char('Migrated Regacy record ID')
    migrated_legacy_module = fields.Char('Migrated Request module')
    memo_bagde_undone = fields.Boolean('', default=True)
    branch_id = fields.Many2one('multi.branch', string='Branch', default=lambda self: self.env.user.branch_id.id)
    dummy_memo_types = fields.Many2many(
        'memo.type',
        'memo_model_type_rel',
        'memo_type_id', 
        'memo_id',
        string='Dummy Memo type',
        )
    
    dummy_memo_config_ids = fields.Many2many(
        'memo.config',
        'memo_config_memo_model_rel',
        'memo_id', 
        'memo_config',
        string='Dummy Memo settings',
        )
    
    def get_publish_memo_types(self):
        memo_configs = self.env['memo.config'].sudo().search([('active', '=', True)])
        memo_type_ids = [r.memo_type.id for r in memo_configs]
        return [('id', 'in', memo_type_ids)]
    
    memo_type = fields.Many2one(
        'memo.type',
        string='Request type',
        required=False,
        copy=True,
        domain=lambda self: self.get_publish_memo_types(),
        )
    memo_type_key = fields.Char('Request type key', readonly=True)
    name = fields.Char('Subject', size=400)
    requester_name = fields.Char('Legacy Request name')
    code = fields.Char('Code', readonly=True)
    employee_id = fields.Many2one('hr.employee', string = 'Employee', default =_default_employee) 
    direct_employee_id = fields.Many2one('hr.employee', string = 'Employee') 
    set_staff = fields.Many2one('hr.employee', string = 'Assigned to')
    demo_staff = fields.Integer(string='User',
                                default=lambda self: self.env['res.users'].sudo().search([
                                    ('id', '=', self.env.uid)], limit=1).id, compute="get_user_staff",)
        
    user_ids = fields.Many2one('res.users', string = 'Beneficiary', default =_default_user)
    dept_ids = fields.Many2one('hr.department', string ='Department', readonly = True, store =True, compute="employee_department",)
    description = fields.Char('Note')
    project_id = fields.Many2one('account.analytic.account', 'Project')
    vendor_id = fields.Many2one('res.partner', 'Vendor')
    amountfig = fields.Float('Budget Amount', store=True, default=1.0)
    request_total_amount = fields.Float(
        'Total Amount',
        compute="compute_total_request_amount",
        store=True, 
        default=0.0)
    request_total_soe_amount = fields.Float(
        'Total Amount',
        compute="compute_total_soe_request_amount",
        store=True, 
        default=0.0) 
    
    description_two = fields.Text('Reasons')
    phone = fields.Char('Phone', store=True, default=lambda self: self.env.user.employee_id.mobile_phone if self.env.user.employee_id else "")
    email = fields.Char('Email', related='employee_id.work_email')
    reason_back = fields.Char('Return Reason')
    file_upload = fields.Binary('File Upload')
    file_namex = fields.Char("FileName")
    stage_id = fields.Many2one(
        'memo.stage', 
        string='Stage', 
        store=True,
        domain=lambda self: self._get_related_stage(),
        )
    state = fields.Selection([('submit', 'Draft'),
                                ('Sent', 'Sent'),
                                ('Approve', 'Waiting For Payment / Confirmation'),
                                ('Approve2', 'Request Approved'),
                                ('Done', 'Completed'),
                                ('Refuse', 'Refused'),
                              ], string='Status', index=True, readonly=True,
                             copy=False, default='submit',
                             required=True,
                             store=True,
                             help='Request Report state')
    date = fields.Datetime('Request Date', default=fields.Datetime.now())
    invoice_id = fields.Many2one(
        'account.move', 
        string='Invoice', 
        store=True,
        domain="[('move_type', '=', 'in_invoice'), ('state', '!=', 'cancel')]"
        )
    move_id = fields.Many2one(
        'account.move', 
        string='Move', 
        store=True,
        readonly=True
        )
    soe_advance_reference = fields.Many2one(
        'memo.model',
        string='SOE ref.')
    cash_advance_reference = fields.Many2one(
        'memo.model', 
        'Cash Advance ref.')
    payment_reference = fields.Char(
        string="Payment Cash advance")
    payment_reference_id = fields.Many2one(
        'memo.model', 
        string="Payment Cash advance ID", 
        compute="compute_cash_advance_payment_reference")
    
    retirement_soe_id = fields.Many2one('memo.model', compute='_compute_retirement_soe_id', string="Retirement SOE")

    def _compute_retirement_soe_id(self):
        for rec in self:
            if rec.memo_type_key == 'cash_advance' and rec.is_cash_advance_retired:
                rec.retirement_soe_id = self.env['memo.model'].search([
                    ('cash_advance_reference', '=', rec.id),
                    ('memo_type_key', '=', 'soe'),
                    ('state', '=', 'Done')
                ], limit=1)
            else:
                rec.retirement_soe_id = False

    @api.constrains('state', 'memo_type_key')
    def check_cash_advance_limit(self):
        # for rec in self:
        if self.memo_type_key == 'cash_advance':# and self.state not in ['Refuse', 'submit']: 
            limit = self.employee_id.maximum_cash_advance_limit or 5
            if self.create_uid.id == self.env.user.id:
                # Count non-retired cash advances for this employee
                domain = [
                    ('employee_id', '=', self.employee_id.id),
                    ('memo_type_key', '=', 'cash_advance'),
                    ('is_cash_advance_retired', '=', False),
                    ('state', 'in', ['Approve', 'Done', 'Approve2']), 
                    ('id', '!=', self.id)
                ]
                count = self.env['memo.model'].search_count(domain)
                if count >= limit:
                    pass 
                    # raise ValidationError(f"You have reached the maximum limit of {limit} active (non-retired) cash advances. Please retire existing cash advances before requesting a new one.")
                
    payment_processing_company_id = fields.Many2one(
        'res.company',
        string='Processing Company',
        # compute='_compute_payment_processing_company',
        store=True,
        help="Company that will actually process the payment (may differ from memo company)"
    )
    
    payment_processing_branch_id = fields.Many2one(
        'multi.branch',
        string='Processing Branch',
        # compute='_compute_payment_processing_company',
        store=True,
    )
    
    processing_company_id = fields.Many2one(
        'res.company',
        string='Processing Company',
        help="""Company that will process this request type. 
            """
    )
    
    processing_branch_id = fields.Many2one(
        'multi.branch',
        string='Processing Branch',
        domain="[('company_id', '=', processing_company_id)]",
        help="Specific branch within the processing company"
    )
    
    stock_processing_company_id = fields.Many2one(
        'res.company',
        string='Stock Processing Company',
    )
    
    stock_processing_branch_id = fields.Many2one(
        'multi.branch',
        string='Stock Processing Branch',
    )
    
    
    
    @api.depends('memo_setting_id', 'stage_id', 'stage_id.approver_ids')
    def _compute_processing_company(self):
        for rec in self:
            if rec.memo_setting_id.requires_processing_district and rec.processing_branch_id:
                rec.processing_company_id = rec.processing_branch_id.company_id or rec.company_id
                continue 

            if rec.memo_setting_id.processing_company_id:
                rec.processing_company_id = rec.memo_setting_id.processing_company_id
                rec.processing_branch_id = rec.memo_setting_id.processing_branch_id
            elif rec.stage_id and rec.stage_id.is_approved_stage and rec.stage_id.approver_ids:
                approver = rec.stage_id.approver_ids[0]
                rec.processing_company_id = approver.company_id
                rec.processing_branch_id = approver.user_id.branch_id
            else:
                rec.processing_company_id = rec.company_id
                rec.processing_branch_id = rec.branch_id
    
    @api.depends('payment_reference')
    def compute_cash_advance_payment_reference(self):
        '''if cash advance reference, system computes and update with existing
        cash advance for reference purposes'''
        for rec in self:
            if rec.payment_reference:
                cash_advance = self.env['memo.model'].search([
                    ('code', '=ilike', rec.payment_reference),
                    ('employee_id', '=', rec.employee_id.id)
                    ], limit=1)
                rec.payment_reference_id = cash_advance and cash_advance.id
            else:
                rec.payment_reference_id = False
    
    user_owned_cash_advance_ids = fields.Many2many(
        'memo.model', 
        'user_owned_cash_advance_rel',
        'user_owned_cash_advance_id',
        'memo_id',
        compute='_compute_user_cash_advance', string="User owned cash advances", store=True)
    
    date_deadline = fields.Date('Deadline date')
    status_progress = fields.Float(string="Progress(%)", compute='_progress_state')
    users_followers = fields.Many2many('hr.employee', string='Add followers') #, default=_default_employee)
    res_users = fields.Many2many('res.users', string='Reviewers/Processors') #, default=_default_employee)
    comments = fields.Text('Comments', default="-")
    supervisor_comment = fields.Html('Supervisor Comments', default="")
    manager_comment = fields.Html('Manager Comments', default="")
    is_supervior = fields.Boolean(string='is supervisor', compute="compute_employee_supervisor")
    is_manager = fields.Boolean(string="is_manager", compute="compute_employee_supervisor")
    is_cash_advance_retired = fields.Boolean(
        string="Is cash Advanced Retired", 
        help="Used to determine if user has fully retired his cash advance"
        )
    # Fields for server request
    applicationChange = fields.Boolean(string="Application Change")
    datapatch = fields.Boolean(string="Data patch")
    enhancement = fields.Boolean(string="Enhancement")
    databaseChange = fields.Boolean(string="Database Change")
    osChange = fields.Boolean(string="OS Change")
    ids_on_os_and_db = fields.Boolean(string="IDS on OS and DB")
    versionUpgrade = fields.Boolean(string="version Upgrade")
    hardwareOption = fields.Boolean(string="hardware Option")
    otherChangeOption = fields.Boolean(string="Other Change")
    other_system_details = fields.Html(string="Specify Other reason")
    justification_reason = fields.Html(string="Justification Reason")
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='No. Attachments')
    approver_id = fields.Many2one('hr.employee', 'Approver')
    approver_ids = fields.Many2many(
        'hr.employee',
        'memo_model_employee_rel',
        'memo_id',
        'hr_employee_id',
        string='Approvers'
        )
    
    
    user_is_approver = fields.Boolean(string="User is approver", compute="compute_user_is_approver")
    is_request_completed = fields.Boolean(
        string="is request completed", 
        default=False,
        help="Used to determine if the request business flow is completed. Hides all action buttons if checked")
    is_supervisor_commented = fields.Boolean(
        string="Supervisor commented?", 
        help="Used to determine if supervisor has commented"
        )
    is_manager_approved = fields.Boolean(
        string="Manager Approved?", 
        help="Used to determine if manager has approved from the website portal"
        )
    # Loan fields
    loan_type = fields.Selection(
        [
            # ("fixed-annuity", "Fixed Annuity"),
            # ("fixed-annuity-begin", "Fixed Annuity Begin"),
            ("fixed-principal", "Fixed Principal"),
            ("interest", "Only interest"),
        ],
        required=False,
        help="Method of computation of the period annuity",
        readonly=True,
        states={"submit": [("readonly", False)]},
        default="fixed-principal",
    )
    loan_amount = fields.Monetary(
        currency_field="currency_id",
        required=False,
        readonly=True,
        states={"submit": [("readonly", False)]},
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id.id
    )
    currency_id = fields.Many2one(
        "res.currency", 
        default= lambda self: self.env.user.company_id.currency_id.id, 
        readonly=True,
    )
    conversion_rate = fields.Float(
        string="Conversion Rate",
        digits=(12, 6),
        help="Custom conversion rate to override the default currency rate.",
    ) 
    
    periods = fields.Integer(
        required=False,
        readonly=True,
        states={"submit": [("readonly", False)]},
        help="Number of periods that the loan will last",
        default=12,
    )
    method_period = fields.Integer(
        string="Period Length (years)",
        default=1,
        help="State here the time between 2 depreciations, in months",
        required=False,
        readonly=True,
        states={"submit": [("readonly", False)]},
    )
    start_date = fields.Date(
        help="Start of the moves",
        readonly=True,
        states={"submit": [("readonly", False)]},
        copy=False,
    )
    loan_reference = fields.Integer(string="Loan Ref")
    active = fields.Boolean('Active', default=True)

    product_ids = fields.One2many(
        'request.line', 
        'memo_id', 
        string ='Request Line',
    )
    # document_request_ids = fields.One2many(
    #     'document.request.line', 
    #     'memo_document_request_id', 
    #     string ='Document request Line',
    # )
    
    action_history_ids = fields.One2many(
        'memo.action.history', 
        'memo_id', 
        string='Approval/Action History',
        readonly=True
    )

    approved_by_ids = fields.Many2many(
        'hr.employee',
        'memo_approved_by_rel',
        'memo_id',
        'employee_id',
        string='Approved By',
        compute='_compute_action_users',
        store=True,
        help="Employees who approved this request"
    )

    @api.depends('action_history_ids.action')
    def _compute_action_users(self):
        """Compute employees who approved"""
        for rec in self:
            approved_history = rec.action_history_ids.filtered(
                lambda h: h.action == 'approved'
            )
            rec.approved_by_ids = approved_history.mapped('actor_id')

            
    
    def _log_action(self, action, comments='', next_stage=None):
        """
        Args:
            action: One of 'submitted', 'approved', 'rejected', 'returned', 'cancelled'
            comments: Optional comment text
            next_stage: The stage being moved to (if applicable)
        """
        current_employee = self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.uid)
        ], limit=1)
        
        if not current_employee:
            _logger.warning(f"No employee found for user {self.env.uid}")
            return False
        
        # Create history record
        history_vals = {
            'memo_id': self.id,
            'stage_id': self.stage_id.id,
            'actor_id': current_employee.id,
            'action': action,
            'action_date': fields.Datetime.now(),
            'comments': comments,
        }
        
        if next_stage:
            history_vals['next_stage_id'] = next_stage.id
            
        history_record = self.env['memo.action.history'].sudo().create(history_vals)
        
        # Post to chatter with clear formatting
        action_labels = {
            'submitted': ('📝', 'Submitted'),
            'approved': ('✅', 'Approved'),
            'rejected': ('❌', 'Rejected'),
            'returned': ('↩️', 'Returned'),
            'cancelled': ('🚫', 'Cancelled'),
        }
        
        icon, label = action_labels.get(action, ('•', action.title()))
        
        # Build chatter message
        message_parts = [
            f"<p><b>{icon} {label}</b></p>",
            f"<p><b>By:</b> {current_employee.name}</p>",
            f"<p><b>Stage:</b> {self.stage_id.name}</p>",
        ]
        
        if next_stage:
            message_parts.append(f"<p><b>Moving to:</b> {next_stage.name}</p>")
        
        if comments:
            message_parts.append(f"<p><b>Comments:</b></p><p>{comments}</p>")
        
        message_parts.append(f"<p><small><i>{fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i></small></p>")
        
        self.sudo().message_post(
            body="".join(message_parts),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        return history_record
            
    leave_start_date = fields.Datetime('Leave Start Date', default=fields.Date.today())
    leave_end_date = fields.Datetime('Leave End Date', default=fields.Date.today())
    request_date = fields.Datetime('Request Start Date')
    request_end_date = fields.Datetime('Request End Date')
    leave_type_id = fields.Many2one('hr.leave.type', string="Leave type")
    leave_Reliever = fields.Many2one(
        'hr.employee', 
        string="Leave Reliever",  
        )
    memo_setting_id = fields.Many2one(
        'memo.config', 
        string="Request type",  
        )
    
    def get_document_memo(self):
        document_memo_ids = self.env['memo.config'].sudo().search([('memo_type.is_document', '=', True)])
        return [('id', '=', document_memo_ids.ids)]
    
    document_memo_config_id = fields.Many2one(
        'memo.config', 
        string="Request Department Config", 
        domain= lambda self: self.get_document_memo() 
        )
    leave_duration = fields.Char(
        string="Duration",
        store=True,
        compute="get_leave_days_taken")
    
    @api.depends('leave_end_date')
    def get_leave_days_taken(self):
        for rec in self:
            if rec.leave_start_date and rec.leave_end_date:
                delta = rec.leave_end_date - rec.leave_start_date
                rec.leave_duration = delta.days + 1
            else:
                rec.leave_duration = 0
                
    def set_reliever_to_act_as_employee_on_leave(
        self, employee_on_leave_id, leave_reliever_id):
        '''
        kwargs: {employee_on_leave_id: the employee on leave, 'leave_reliever_id'}
        '''
        memo_config_ids = self.env['memo.config'].sudo().search([('company_ids', 'in', [self.employee_id.company_id.id])])
        employee_reliever_stages = []
        for config in memo_config_ids: #.mapped('company_ids').filtered(lambda c: c.employee_id.company_id.id == c.id):
            config_stage_ids = config.stage_ids
            for cs in config_stage_ids:
                st_approvers = cs.sudo().approver_ids.ids
                if employee_on_leave_id.id in st_approvers and \
                    leave_reliever_id.id not in st_approvers: 
                    # e.g Sopulu in ['sopulu', 'chris'] and \
                    # reliever as Chidi not in ['sopulu', 'chris']
                    '''[FIXME replace or add the reliever]'''
                    cs.sudo().update({
                        'approver_ids': [(4, leave_reliever_id.id)],
                    })
                    employee_reliever_stages.append(cs.id)
                    
        ## update a stage reference where reliever holds 
        # the approver position of the employee,
        # when employee returns, system cron should auto reset the reliever after employee
        # leave expires
        employee_on_leave = employee_on_leave_id.sudo()
        employee_reliever_stages += eval(employee_on_leave.leave_reliever_memo_stage_ids or '[]')
        employee_on_leave_id.sudo().update({
            'leave_reliever_memo_stage_ids': str(employee_reliever_stages),
            'leave_reliever': self.leave_Reliever.id
        })
    
    ###############3 RECRUITMENT ##### 
    job_id = fields.Many2one('hr.job', string='Requested Position',
                             states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     },
                             help='The Job Position you expected to get more hired.',
                             )
    job_tmp = fields.Char(string="Job Title",
                          size=256,
                          readonly=True,
                          states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     },)
    
    established_position = fields.Selection([('yes', 'Yes'),
                                ('no', 'No'),
                              ], string='Established Position', index=True,
                             copy=False,
                             readonly=True,
                             store=True,
                             states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     })
    recruitment_mode = fields.Selection([('Internal', 'Internal'),
                                ('External', 'External'),
                                ('Outsourced', 'Outsourced'),
                              ], string='Recruitment Mode', index=True,
                             copy=False,
                             readonly=True,
                             store=True,
                             states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     })
    requested_department_id = fields.Many2one('hr.department', string ='Requested Department for Recruitment') 
    qualification = fields.Char('Qualification')
    age_required = fields.Char('Required Age')
    years_of_experience = fields.Char('Years of Experience')
    expected_employees = fields.Integer('Expected Employees', default=1,
                                        help='Number of extra new employees to be expected via the recruitment request.',
                                        required=False,
                                        index=True,
                                        )
    recommended_by = fields.Many2one('hr.employee', string='Recommended by',
                                     states={
                                         'submit':[('readonly', False)],
                                     })
    date_expected = fields.Date('Expected Date',
                                states={
                                         'submit': [('required', True)],
                                         'submit':[('readonly', False)],
                                     }, index=True)

    closing_date = fields.Date('Closing Date',
                                states={
                                         'submit': [('required', True)],
                                         'submit':[('readonly', False)],
                                     }, index=True)
    
    invoice_ids = fields.Many2many(
        'account.move', 
        'memo_invoice_rel',
        'memo_invoice_id',
        'invoice_memo_id',
        string='Invoice', 
        store=True,
        domain="[('type', 'in', ['in_invoice', 'in_receipt']), ('state', '!=', 'cancel')]"
        ) 
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'memo_ir_attachment_rel',
        'memo_ir_attachment_id',
        'ir_attachment_memo_id',
        string='Attachment', 
        store=True,
        domain="[('res_model', '=', 'memo.model')]"
        )
    
    memo_sub_stage_ids = fields.Many2many(
        'memo.sub.stage', 
        'memo_sub_stage_rel',
        'memo_sub_stage_id',
        'memo_id',
        string='Sub Stages', 
        store=True,
        )
    
    internal_memo_option = fields.Selection(
        [
        ("none", ""),
        ("all", "All"), 
        ("selected", "Selected"),
        ], string="All / Selected")
    partner_ids = fields.Many2many(
        'res.partner', 
        'memo_res_partner_rel',
        'memo_res_partner_id',
        'memo_partner_id',
        string='Reciepients', 
        )
    has_sub_stage = fields.Boolean(
        'Has Sub stage', 
        default=False, 
        store=True,
        )
    # document_folder = fields.Many2one('documents.folder', string="Document folder")
    to_create_document = fields.Boolean(
        'Registered in Document Management',
        default=False,
        help="Used to create in Document Management")
    memo_category_id = fields.Many2one('memo.category', string="Category") 
    submitted_date = fields.Date(
        string="submitted date")
    computed_stage_ids = fields.Many2many('memo.stage', compute='_compute_stage_ids', store=True)
    stage_to_skip = fields.Many2one(
        'memo.stage', 
        string='Stage to skip', 
        store=True,
        help="Used to determine stage not to be included in this memo"
        )
    
    client_id = fields.Many2one('res.partner', 'Client')
    customer_id = fields.Many2one('res.partner', 'Client')
    
    po_ids = fields.Many2many('purchase.order', 
                              store=True)
    so_ids = fields.Many2many('sale.order', 
                              store=True)
    vehicle_trip_ids = fields.One2many(
        'memo.fleet',
        'memo_id',
        string="Fleets trips",
        store=True
        )
    
    job_id = fields.Many2one('hr.job', string='Requested Position',
                             states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     },
                             help='The Job Position you expected to get more hired.',
                             )
    job_tmp = fields.Char(string="Job Title",
                          size=256,
                          readonly=True,
                          states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     },)
    
    established_position = fields.Selection([('yes', 'Yes'),
                                ('no', 'No'),
                              ], string='Established Position', index=True,
                             copy=False,
                             readonly=True,
                             store=True,
                             states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     })
    recruitment_mode = fields.Selection([('Internal', 'Internal'),
                                ('External', 'External'),
                                ('Outsourced', 'Outsourced'),
                              ], string='Recruitment Mode', index=True,
                             copy=False,
                             readonly=True,
                             store=True,
                             states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     })
    requested_department_id = fields.Many2one('hr.department', string ='Requested Department for Recruitment') 
    qualification = fields.Char('Qualification')
    age_required = fields.Char('Required Age')
    years_of_experience = fields.Char('Years of Experience')
    expected_employees = fields.Integer('Expected Employees', default=1,
                                        help='Number of extra new employees to be expected via the recruitment request.',
                                        required=False,
                                        index=True,
                                        )
    recommended_by = fields.Many2one('hr.employee', string='Recommended by',
                                     states={
                                         'submit':[('readonly', False)],
                                     }, default=lambda self: self.env.user.employee_id.id if self.env.user.employee_id else None)
    date_expected = fields.Date('Expected Date',
                                states={
                                         'submit': [('required', True)],
                                         'submit':[('readonly', False)],
                                     }, index=True)
    
    bank_journal_id = fields.Many2one(
        'account.journal', 
        string='Journal',
        compute='_compute_default_journal',
        store=True,
        readonly=False,
        domain="[('type', 'in', ['bank','purchase', 'sale', 'general']), '|', ('company_id', '=', processing_company_id), ('company_id', '=', company_id)]"
    )
    
    @api.depends('stage_id', 'processing_company_id', 'processing_branch_id', 'company_id', 'branch_id')
    def _compute_default_journal(self):
        for rec in self:
            
            if rec.stage_id.is_approved_stage or not rec.bank_journal_id:
                
                company = rec.processing_company_id or rec.company_id
                branch = rec.processing_branch_id or rec.branch_id
                
                base_domain = [
                    ('company_id', '=', company.id),
                    ('type', 'in',  ['bank','purchase', 'sale', 'general']),
                ]
                
                journal = self.env['account.journal'].sudo().search(
                    base_domain + [('allowed_branch_ids', 'in', [branch.id])], 
                    limit=1
                )
                
                if not journal:
                    journal = self.env['account.journal'].sudo().search(base_domain, limit=1)
                    
                rec.bank_journal_id = journal.id
            else:
                # Keep existing value if not in approved stage (optional logic)
                # or just let it recompute every time.
                # To simply ensure it calculates, usually you just let the code above run without the 'if'.
                pass

    def validate_po_line(self):
        '''if the stage requires PO confirmation'''
        self.procurement_confirmation()
    
    def validate_so_line(self):
        '''if the stage requires so confirmation'''
        if self.memo_type_key == 'sale_request':
            self.sale_confirmation()
        
    def validate_necessary_components(self):
        '''check relevant fields necessary for different memo type'''
        request_list = ['Payment', 'material_request', 'procurement_request', 'procurement','cash_advance', 'soe', 'vehicle_request']
        if self.memo_type_key in request_list:
            if not self.product_ids:
                raise ValidationError("Please enter request lines")
        
        '''Check for lines without qty'''
        if self.memo_type_key in ['material_request', 'procurement_request', 'cash_advance']:
            for ln in self.product_ids:
                if not ln.omit_record:
                    if ln.quantity_available < 1:
                        raise UserError(f"{ln.product_id.name} must have product unit greater than 0")
                
        # if self.memo_type_key in ['soe']:
        #     for ln in self.product_ids:
        #         if ln.used_qty < 1 or ln.used_amount < 1:
        #             raise UserError(f"{ln.product_id.name} used Quantity and used amount must be greater than 0")
        
        invoice_list = ['Payment']
        if self.memo_type_key in invoice_list and not self.product_ids:
            raise ValidationError("Please enter invoice lines")

    # def procurement_confirmation(self):
    #     if self.stage_id.require_po_confirmation:
    #         if not self.po_ids:
    #             raise UserError("Please enter purchase order lines")
    #         else:
    #             po_without_lines = self.mapped('po_ids').filtered(
    #                 lambda tot: tot.amount_total < 1
    #             )
    #             if po_without_lines:
    #                 raise ValidationError("Please kindly ensure that all purchase order lines are added with price amount")

    #         po_without_confirmation = self.mapped('po_ids').filtered(
    #                 lambda st: st.state in ['draft', 'sent']
    #             )
    #         if po_without_confirmation:
    #             raise ValidationError(
    #                 """All POs must be confirmed at this stage. To avoid errors, 
    #                 Please kindly go through each PO to confirm them""")
    #     if self.stage_id.require_bill_payment: 
    #         '''Checks if the PO is expecting a picking count and there is no pickings '''
    #         without_picking_reciept = self.mapped('po_ids').filtered(
    #                 lambda st: st.incoming_picking_count > 0 and not st.picking_ids
    #             )
    #         if without_picking_reciept:
    #             raise ValidationError('Please ensure all PO(s) has been recieved before Vendor Bill is generated')
    #         for po in self.mapped('po_ids'):
    #             if po.mapped('picking_ids').filtered(
    #                 lambda st: st.state != "done"
    #             ):
    #                 raise ValidationError("Please ensure all PO picking / receipts are marked done before vendor bill is generated")
    #         po_without_invoice_payment = self.mapped('po_ids').filtered(
    #                 lambda st: st.invoice_status not in ['invoiced']
    #             )
    #         if po_without_invoice_payment:
    #             raise ValidationError("Please kindly create and pay the bills for each PO lines")

    def procurement_confirmation(self):
        if self.stage_id.require_po_confirmation:
            selected = self.mapped('po_ids').filtered(
                    lambda st: st.selected
                )
            if not selected:
                raise UserError(
                    """Please select at least on PO to confirm""")
                
            if not self.po_ids:
                raise UserError("Please enter purchase order lines")
            else:
                po_without_lines = self.mapped('po_ids').filtered(
                    lambda tot: tot.amount_total < 1 and tot.selected
                )
                if po_without_lines:
                    raise UserError("Please kindly ensure that all purchase order lines are added with price amount")

            po_without_confirmation = self.mapped('po_ids').filtered(
                    lambda st: st.state in ['draft', 'sent'] and st.selected == True
                )
            if po_without_confirmation:
                raise UserError(
                    """All Selected POs must be confirmed at this stage. To avoid errors, 
                    Please kindly go through each PO to confirm them""")
        if self.stage_id.require_waybill_detail: 
            '''Checks if the PO is expecting a picking count and there is no pickings '''
            without_picking_reciept = self.mapped('po_ids').filtered(
                    lambda st: st.selected and st.incoming_picking_count > 0 and not st.picking_ids
                )
            if without_picking_reciept:
                raise UserError('Please ensure all PO(s) has been recieved before Vendor Bill is generated')
            for po in self.mapped('po_ids').filtered(
                    lambda st: st.selected):
                if po.mapped('picking_ids').filtered(
                    lambda st: st.state not in ["cancel", "done"]):
                    raise UserError(
                        """Please ensure all PO picking / receipts are marked done before vendor bill is generated \n 1) Please go under purchase order tab \n 2) Click view button \n. 3) Click on the Receive button. \n 4) On the new page click Validate. (If stock pickings are shown, ensure to either cancel or validate the records.)""")
        if self.stage_id.require_bill_payment: 
            po_without_invoice_payment = self.sudo().mapped('po_ids').filtered(
                    lambda st: st.selected and st.invoice_status not in ['invoiced']
                    # lambda st: not st.invoice_ids
                )
            if po_without_invoice_payment:
                raise UserError("Please kindly create and pay the bills for each PO lines")

    def sale_confirmation(self):
        if self.stage_id.require_so_confirmation:
            # selected = self.mapped('so_ids').filtered(
            #         lambda st: st.selected
            #     )
            # if not selected:
            #     raise UserError(
            #         """Please select at least on Sale order to confirm""")
                
            if not self.so_ids:
                raise UserError("Please enter sale order lines")
            else:
                so_without_lines = self.mapped('so_ids').filtered(
                    lambda tot: tot.amount_total < 1 and tot.selected
                )
                if so_without_lines:
                    raise UserError("Please kindly ensure that all sale order lines are added with price amount")

            so_without_confirmation = self.mapped('so_ids').filtered(
                    lambda st: st.state in ['draft', 'sent'] and st.selected == True
                )
            if so_without_confirmation:
                raise UserError(
                    """All Selected POs must be confirmed at this stage. To avoid errors, 
                    Please kindly go through each SO to confirm them""")
        # if self.stage_id.require_waybill_detail: 
        #     '''Checks if the PO is expecting a picking count and there is no pickings '''
        #     without_picking_reciept = self.mapped('po_ids').filtered(
        #             lambda st: st.selected and st.incoming_picking_count > 0 and not st.picking_ids
        #         )
        #     if without_picking_reciept:
        #         raise UserError('Please ensure all PO(s) has been recieved before Vendor Bill is generated')
        #     for po in self.mapped('po_ids').filtered(
        #             lambda st: st.selected):
        #         if po.mapped('picking_ids').filtered(
        #             lambda st: st.state not in ["cancel", "done"]):
        #             raise UserError(
        #                 """Please ensure all PO picking / receipts are marked done before vendor bill is generated \n 1) Please go under purchase order tab \n 2) Click view button \n. 3) Click on the Receive button. \n 4) On the new page click Validate. (If stock pickings are shown, ensure to either cancel or validate the records.)""")
        if self.stage_id.require_bill_payment: 
            so_without_invoice_payment = self.mapped('so_ids').filtered(
                    lambda st: st.selected and st.invoice_status not in ['invoiced']
                    # lambda st: not st.invoice_ids
                )
            if so_without_invoice_payment:
                raise UserError("Please kindly create and pay the bills for each SO lines")


    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = ['|', ('name', operator, name), ('code', operator, name)]
        return self.search(domain + args, limit=limit).name_get()
    
    # @api.model
    # def default_get(self, fields_list):
    #     defaults = super(Memo_Model, self).default_get(fields_list)
    #     if 'to_create_document' in self._context:
    #         val = self._context.get('to_create_document')
    #         if val == True:
    #             memo_document_key = self.env['memo.type'].search([('is_document', '=', True)], limit=1)
    #         defaults['memo_type'] = memo_document_key.id
            
    #     if 'is_doc_mgt_request' in self._context:
    #         val = self._context.get('is_doc_mgt_request')
    #         if val == True:
    #             doc_mgt_config = self.env['doc.mgt.config'].search([], limit=1)
    #             if doc_mgt_config and doc_mgt_config.memo_type_id:
    #                 memo_type_id = doc_mgt_config.memo_type_id.id
    #                 defaults['memo_type'] = memo_type_id
    #     return defaults
     
    def get_user_company_in_memo_companies(self, user_company_ids, memo_company_ids):
        _logger.info(f"User companies and memo companies {user_company_ids}, {memo_company_ids}")
        # return True
        for uc in user_company_ids:
            if uc in memo_company_ids:
                return True
            
    def get_user_configs(self):
        user = self.env.user
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)

        branch_ids = [employee.user_id.branch_id.id] + employee.user_id.branch_ids.ids
        company_ids = [employee.user_id.company_id.id] + employee.user_id.company_ids.ids
        
        memo_configs = self.env['memo.config'].sudo().search([
            ('active', '=', True),
            ('publish_to_public', '=', True), 
        ])

        for r in memo_configs:
            # Case 1: normal relationship — same branch/company
            is_related = (r.branch_id.id in branch_ids and r.company_id.id in company_ids) # or r.company_id.id in company_ids)

            # Case 2: inter-district or request but unrelated branch
            # is_inter_district_case = (
            #     (r.inter_district or r.inter_district_request)
            #     and (r.branch_id.id not in branch_ids)
            # )

            # # Keep if either is true; otherwise remove
            # if not (is_related or is_inter_district_case):
            if r.branch_id.id in branch_ids and r.company_id.id in company_ids:
                pass
            else:
                memo_configs -= r
        _logger.info(f" found configs---{memo_configs}")
        return memo_configs
            
    # def get_user_configs(self):
    #     # employee = self.env['hr.employee'].sudo().with_context(force_company=False).search(
    #     #     [('user_id', '=', self.env.uid)], limit=1)
    #     user = self.env.user
    #     employee = self.env['hr.employee'].sudo().search(
    #         [('user_id', '=', self.env.uid)], limit=1)
    #     memo_configs = self.env['memo.config'].sudo().search([
    #         ('active', '=', True),
    #         ('publish_to_public', '=', True),
    #         # ('department_id', '=', employee.department_id.id),
    #         ('branch_id', '=', employee.user_id.branch_id.id),
    #         ('company_id', '=', employee.user_id.company_id.id),
    #         ])
    #     _logger.info(f'THis is configs == > {memo_configs}')
    #     memo_setting_with_initiators_not_user = [] # [r.id for r in memo_configs if r.stage_ids and r.stage_ids[0].approver_ids and employee.id not in r.stage_ids[0].approver_ids.ids]
    #     for r in memo_configs:
    #         if r.stage_ids:
    #             initiation_stage = r.stage_ids[0]
    #             if initiation_stage.approver_ids and employee.id not in initiation_stage.approver_ids.ids:
    #                 memo_configs = memo_configs - r
    #     return memo_configs
    
    @api.model
    def default_get(self, fields):
        res = super(Memo_Model, self).default_get(fields)
        to_create_document = self.env.context.get('to_create_document')
        memo_document_key = self.env.ref('company_memo.mtype_doc_management_request')
        memo_document_key = memo_document_key.id if to_create_document else False
        
        #### 
        # memo_configs = self.env['memo.config'].search([
        #     ('active', '=', True),
        #     ])
        # user = self.env.user
        # user_branch_id = user.branch_id
        # top_user = self.env.is_admin() or self.env.user.has_group('ik_multi_branch.account_major_user')
        # default_user_branch_id = res.get('branch_id')
        # user_company = self.env.user.company_id.id
        # _logger.info(f"i am seeing configs ==> {configs} {[r.id for r in configs]}")
        # configs = [rec.memo_type.id for rec in memo_configs if user_branch_id.id in rec.branch_ids.ids and user_company in rec.allowed_for_company_ids.ids] 
        configs = self.get_user_configs()
        res.update({
            'memo_type': memo_document_key,
            # 'dummy_memo_types': [(6, 0, [memo_document_key] if memo_document_key else [rec.memo_key.id for rec in configs])], 
            'dummy_memo_config_ids': [(6, 0, [r.id for r in configs])],
        })
        return res
    
    @api.onchange('dummy_memo_config_ids')
    def _onchange_dummy_memo_config(self):
        _logger.info("Defaulting to memo configs")
        if self.dummy_memo_config_ids:
            return {
                'domain': {
                    'memo_setting_id': [('id', 'in', self.dummy_memo_config_ids.ids)]
                }
            }
            
    @api.onchange('memo_setting_id')
    def onchange_memo_setting_id(self):
        if self.memo_setting_id:
            ms = self.memo_setting_id.sudo()
            # raise UserError(f" poor Configuration:{ms.id} {ms} No  {ms.stage_ids}")
            
            has_invoice, has_po, has_so, has_transformer = self.check_po_config(ms)
    #                 memo_setting_stage = ms.stage_ids[0]
    #                 self.has_invoice = has_invoice
    #                 self.has_po = has_po
    #                 self.has_so = has_so
    #                 self.has_transformer = has_transformer
    #                 self.stage_id = memo_setting_stage.id if memo_setting_stage else False
    #                 self.memo_setting_id = ms.id
    #                 self.memo_type_key = self.memo_type.memo_key  
    #                 picking_id = self.get_default_picking_id()
    #                 self.picking_type_id = picking_id
    #                 self.requested_department_id = self.employee_id.department_id.id
    #                 self.users_followers = [
    #                     (4, self.sudo().employee_id.administrative_supervisor_id.id),
    #                     ] 
    
            if ms and ms.stage_ids:
                has_invoice, has_po, has_so, has_transformer = self.check_po_config(ms)
                memo_setting_stage = ms.stage_ids[0]
                self.has_invoice = has_invoice
                self.has_po = has_po
                self.has_so = has_so
                self.has_transformer = has_transformer
                picking_id = self.get_default_picking_id()
                self.picking_type_id = picking_id
                self.requested_department_id = self.employee_id.department_id.id
                
                self.stage_id = memo_setting_stage.id if memo_setting_stage else False
                self.memo_type_key = ms.memo_type.memo_key
                self.memo_type = ms.memo_type.id
                self.has_sub_stage = True if memo_setting_stage.sub_stage_ids else False
                self.users_followers = [
                    (4, self.sudo().employee_id.administrative_supervisor_id.id),
                    ]
                invoices, documents = self.generate_required_artifacts(self.stage_id, self, '')
                if invoices:
                    self.write({
                        'invoice_ids': [(6, 0, [iv]) for iv in invoices if iv] if invoices else False,
                        # 'attachment_ids': [(4, dc.id) for dc in documents if dc]
                        })
                if documents:
                    self.write({
                        'attachment_ids': [(6, 0, [dc]) for dc in documents if dc] if documents else False,
                        })
                # raise ValidationError(documents)
                # self.generate_sub_stage_artifacts(memo_setting_stage)
            else:
                self.memo_type = False
                self.stage_id = False
                self.memo_type_key = False
                self.has_sub_stage = False
                self.picking_type_id = False
                self.requested_department_id = False
                self.has_invoice = False
                self.has_po = False
                self.has_so = False
                self.has_transformer = False
                raise UserError("Configuration: No stages configured for the selected request")
        else:
            self.stage_id = False
    
    # @api.onchange('memo_setting_id')
    # def onchange_memo_setting_id(self):
    #     if self.memo_setting_id:
    #         try:
    #             ms = self.memo_setting_id
    #             if ms.stage_ids:
    #                 memo_setting_stage = ms.stage_ids[0]
    #                 self.stage_id = memo_setting_stage.id
    #                 self.memo_type_key = ms.memo_type.memo_key
    #                 self.memo_type = ms.memo_type
    #                 self.has_sub_stage = bool(memo_setting_stage.sub_stage_ids)

    #                 # Add followers (memory only)
    #                 if self.employee_id.administrative_supervisor_id:
    #                     self.users_followers = [
    #                         (4, self.employee_id.administrative_supervisor_id.id)
    #                     ]

    #                 # Generate artifacts but DO NOT write
    #                 invoices, documents = self.generate_required_artifacts(memo_setting_stage, self, 'context_data_if_needed')

    #                 self.invoice_ids = [(4, iv) for iv in invoices]
    #                 self.attachment_ids = [(4, dc) for dc in documents]

    #                 # Generate sub-stage artifacts (if this doesn't write)
    #                 self.generate_sub_stage_artifacts(memo_setting_stage)
    #             else:
    #                 self.memo_type = False
    #                 self.stage_id = False
    #                 self.memo_setting_id = False
    #                 self.memo_type_key = False
    #                 self.has_sub_stage = False
    #                 raise UserError("Configuration: No stages configured for the selected request")
    #         except Exception as e:
    #             raise ValidationError(e)
    #     else:
    #         self.stage_id = False
        
    @api.depends('stage_id.memo_config_id')
    def _compute_stage_ids(self):
        _logger.info('testing to default stages')
        for record in self:
            if record.stage_id.memo_config_id:
                record.computed_stage_ids = record.stage_id.memo_config_id.mapped('stage_ids').filtered(
                    lambda publish: publish.publish_on_dashboard
                ).ids
                # record.computed_stage_ids = [(6, 0, [1,3,4])]
            else:
                record.computed_stage_ids = False
                
    def compute_config_stages_from_website(self, memo_config_id):
        if memo_config_id:
            self.computed_stage_ids = memo_config_id.mapped('stage_ids').filtered(
                lambda publish: publish.publish_on_dashboard
            )
        else:
            self.computed_stage_ids = False
    
    @api.depends('memo_type')
    def _compute_user_cash_advance(self):
        cash_advance_ids = self.env['memo.model'].search([('create_uid', '=', self.env.uid)])
        for record in self:
            if cash_advance_ids:
                record.user_owned_cash_advance_ids = cash_advance_ids.ids
            else:
                record.user_owned_cash_advance_ids = False
                
    # @api.constrains('document_folder')
    # def check_next_reoccurance_constraint(self):
    #     if self.document_folder and self.document_folder.next_reoccurance_date:
    #         start = self.document_folder.next_reoccurance_date + relativedelta(days=-self.document_folder.submission_minimum_range)
    #         end = self.document_folder.next_reoccurance_date +  relativedelta(days=self.document_folder.submission_maximum_range)
    #         today_date = fields.Date.today()
    #         deadline_interval = (today_date >= start and today_date <= end)
    #         if not deadline_interval:
    #             raise ValidationError(f'''The document type is meant to be submitted from the period of {start} to {end}''')
    
    def send_memo_to_contacts(self):
        if not self.partner_ids:
            raise ValidationError('No partner is select, check to ensure your memo option is in "All or Selected"')
        view_id = self.env.ref('mail.email_compose_message_wizard_form')
        return {
                'name': 'Send memo Message',
                'view_type': 'form',
                'view_id': view_id.id,
                "view_mode": 'form',
                'res_model': 'mail.compose.message',
                'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': {
                        'default_partner_ids': self.partner_ids.ids,
                        'default_subject': self.name,
                        'default_attachment_ids': self.attachment_ids.ids,
                        'default_body_html': self.description,
                        'default_body': self.description,
                    },
            }

    def _get_related_stage(self):
        if self.memo_type:
            domain = [
                ('memo_type', '=', self.memo_type.id), 
                # ('department_id', '=', self.employee_id.department_id.id)
                ]
        else:
            domain=[('id', '=', 0)]
        return domain
    
    @api.depends('product_ids.retire_sub_total_amount')
    def compute_total_soe_request_amount(self):
        for rec in self:
            if rec.product_ids:
                amount = sum([re.retire_sub_total_amount for re in rec.mapped('product_ids')])
                # raise ValidationError(amount)
                rec.request_total_soe_amount = amount
    
    @api.depends('product_ids.sub_total_amount')
    def compute_total_request_amount(self):
        for rec in self:
            if rec.product_ids:
                amount = sum([re.sub_total_amount for re in rec.mapped('product_ids')])
                # raise ValidationError(amount)
                rec.request_total_amount = amount
                
    @api.onchange('invoice_ids')
    def get_amount(self):
        if self.invoice_ids:
            self.amountfig = sum([rec.amount_total for rec in self.invoice_ids])
            
    has_invoice = fields.Boolean(
        string='Has invoice line', 
        help="used to show invoice when there is an invoice setup in the memo_config_setting stages"
        )
    has_po = fields.Boolean(
        string='Has PO line', 
        help="used to show invoice when there is an PO setup in the memo_config_setting stages"
        )
    has_so = fields.Boolean(
        string='Has PO line', 
        help="used to show invoice when there is an PO setup in the memo_config_setting stages"
        )
    has_transformer = fields.Boolean(
        string='Has transformer line', 
        help="used to show invoice when there is an PO setup in the memo_config_setting stages"
        )
    
    def check_po_config(self, memo_setting):
        stages = memo_setting.mapped('stage_ids')
        has_invoice, has_po, has_so, has_transformer = False, False, False, False
        if memo_setting.has_transformer:
            has_transformer = True
        for st in stages:
            if st.required_invoice_line:
                has_invoice = True
            if st.require_po_confirmation:
                has_po = True 
            if st.require_po_confirmation:
                has_so = True 
        return has_invoice, has_po, has_so, has_transformer
    
    def portal_check_po_config(self, memo_setting):
        has_invoice, has_po, has_so, has_transformer = self.check_po_config(memo_setting)
        if has_po:
            self.has_po = has_po
    
    @api.onchange('document_memo_config_id')
    def get_document_memo_default_stage_id(self):
        """ Gives default stage_id """
        if self.document_memo_config_id:
            if self.document_memo_config_id.stage_ids:
                memo_setting_stage = self.document_memo_config_id.stage_ids[0]
                self.stage_id = memo_setting_stage.id if memo_setting_stage else False
                self.memo_setting_id = self.document_memo_config_id.id
                self.memo_type_key = self.memo_type.memo_key 
                self.requested_department_id = self.employee_id.department_id.id
                self.users_followers = [
                            (4, self.employee_id.administrative_supervisor_id.id),
                            ] 
            else:
                self.memo_type = False
                self.stage_id = False
                self.memo_setting_id = False
                self.memo_type_key = False
                self.requested_department_id = False
                msg = f"No stage configured for the select configuration. Please contact administrator"
                return {'warning': {
                            'title': "Validation",
                            'message':msg,
                        }
                }
        else:
            self.stage_id = False
            
    def get_default_picking_id(self):
        op_type = self.env['stock.picking.type'].sudo().search([
            '|', 
            ('company_id', '=', self.env.user.company_id.id),
            ('company_id', '=', self.company_id.id),
            ('code', '=', 'internal'),
            ], limit=1)
        return op_type.id if op_type else False 
         
    # @api.onchange('memo_type')
    # def get_default_stage_id(self):
    #     """ Gives default stage_id """
    #     if self.memo_type and not self.memo_type.is_document:
    #         Employee = self.env['hr.employee'].sudo().with_context(force_company=False)
    #         employee = Employee.search([('user_id', '=', self.env.uid)], limit=1)
    #         self.employee_id = employee.id
    #         if not employee.department_id:
    #             raise ValidationError("Contact Admin !!! Employee does not have a department assigned")
    #         if not self.res_users:
    #             department_id = employee.department_id
    #             ms = self.env['memo.config'].sudo().search([
    #                 ('memo_type', '=', self.memo_type.id),
    #                 # ('department_id', '=', department_id.id)
    #                ('branch_id', '=', employee.user_id.branch_id.id),
    #                 ('company_id', '=', employee.user_id.company_id.id),
    #                 ], limit=1)
    #             if ms:
    #                 has_invoice, has_po, has_so, has_transformer = self.check_po_config(ms)
    #                 memo_setting_stage = ms.stage_ids[0]
    #                 self.has_invoice = has_invoice
    #                 self.has_po = has_po
    #                 self.has_so = has_so
    #                 self.has_transformer = has_transformer
    #                 self.stage_id = memo_setting_stage.id if memo_setting_stage else False
    #                 self.memo_setting_id = ms.id
    #                 self.memo_type_key = self.memo_type.memo_key  
    #                 picking_id = self.get_default_picking_id()
    #                 self.picking_type_id = picking_id
    #                 self.requested_department_id = self.employee_id.department_id.id
    #                 self.users_followers = [
    #                     (4, self.sudo().employee_id.administrative_supervisor_id.id),
    #                     ] 
    #             else:
    #                 self.memo_type = False
    #                 self.stage_id = False
    #                 self.memo_setting_id = False
    #                 self.memo_type_key = False
    #                 self.requested_department_id = False
    #                 msg = f"No stage configured for your districts and selected company {self.env.user.company_id.name}. Please contact administrator"
    #                 return {'warning': {
    #                             'title': "Validation",
    #                             'message':msg,
    #                         }
    #                 }
    #     else:
    #         self.stage_id = False

    @api.depends('approver_id')
    def compute_user_is_approver(self):
        for rec in self:
            if rec.stage_id.is_approved_stage and self.env.user.id in [r.user_id.id for r in rec.sudo().stage_id.approver_ids]: 
                rec.user_is_approver = True
                if self.env.user.employee_id:
                    rec.users_followers = [(4, self.env.user.employee_id.id)]
            else:
                rec.user_is_approver = False
 
    @api.model
    def fields_view_get(
        self, 
        view_id='company_memo.memo_model_form_view_3', 
        view_type='form', 
        toolbar=False, 
        submenu=False):
        res = super(Memo_Model, self).fields_view_get(view_id=view_id,
                                                      view_type=view_type,
                                                      toolbar=toolbar,
                                                      submenu = submenu)
        doc = etree.XML(res['arch']) 
        for rec in self.res_users:
            if rec.id == self.env.uid:
                for node in doc.xpath("//field[@name='users_followers']"):
                    node.set('modifiers', '{"readonly": true}') 
                    
                for node in doc.xpath("//button[@name='return_memo']"):
                    node.set('modifiers', '{"invisible": true}')
        res['arch'] = etree.tostring(doc)
        return res

    @api.depends('set_staff')
    def get_user_staff(self):
        if self.set_staff:
            self.demo_staff = self.set_staff.user_id.id
        else:
            self.demo_staff = False
    
    @api.depends('employee_id')
    def employee_department(self):
        if self.employee_id:
            self.dept_ids = self.employee_id.department_id.id
        else:
            self.dept_ids = False
    
    @api.depends('employee_id')
    def compute_employee_supervisor(self):
        if self.employee_id:
            current_user = self.env.user
            if current_user.id == self.sudo().employee_id.administrative_supervisor_id.user_id.id:
                self.is_supervior = True
            else:
                self.is_supervior = False
            
            if current_user.id == self.sudo().employee_id.parent_id.user_id.id:
                self.is_manager = True
            else:
                self.is_manager = False
        else:
            self.is_supervior = False
            self.is_manager = False 

    def print_memo(self):
        report = self.env["ir.actions.report"].sudo().search(
            [('report_name', '=', 'company_memo.memomodel_print_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env.ref('company_memo.print_memo_model_report').report_action(self)
     
    def set_draft(self):
        if self.env.uid != self.sudo().employee_id.user_id.id:
            raise ValidationError(
                "You are not allowed to resend this because you are not the initiator"
                )
        for rec in self:
            if rec.memo_setting_id and rec.memo_setting_id.stage_ids:
                draft_stage = rec.memo_setting_id.stage_ids[0]
                # removing user to allow resubmission
                user_id = self.mapped('res_users').filtered(
                    lambda user: user.id == self.env.uid
                    )
                if user_id:
                    rec.res_users = [(3, user_id.id)]
                rec.write({
                    'state': "submit", 
                    'direct_employee_id': False, 
                    'stage_id': draft_stage.id
                    })
     
    def user_done_memo(self):
        for rec in self:
            rec.write({'state': "Done"})
     
    def Cancel(self):
        if self.env.uid not in [self.sudo().employee_id.user_id.id, self.create_uid.id]:
            raise ValidationError(
                'Sorry!!! you are not allowed to cancel a memo not initiated by you.'
                ) 
        if self.state not in ['Refuse', 'Sent']:
            raise ValidationError(
                'You cannot cancel a memo that is currently undergoing management approval'
                )
        for rec in self:
            
            rec._log_action(
                action='cancelled',
                comments='Request cancelled by initiator'
            )
            rec.sudo().write({
                'state': "submit", 
                'direct_employee_id': False, 
                'partner_id':False, 
                'set_staff': False,
                'users_followers': False, 
                'stage_id': self.memo_setting_id.stage_ids[0].id,
                }) 
            
    def get_internal_url(self, id):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        user = self.env.user
        
        is_portal = user.has_group('base.group_portal')
        
        if is_portal:
            path = "/my/request/view/{}".format(id)
        else:
            path = "/web#id={}&model=memo.model&view_type=form".format(id)
        
        url = base_url + path
        return url
            
    def get_url(self, id):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        user = self.env.user
        
        is_portal = user.has_group('base.group_portal')
    
        if is_portal:
            path = "/my/request/view/{}".format(id)
        else:
            path = "/my/request/view/{}".format(id) # "/web#id={}&model=memo.model&view_type=form".format(id)
        url = base_url + path
        return "<a href='{}'>Click</a>".format(url)
    
    """line 4 - 7 checks if the current user is the initiator of the memo, 
    if true, raises warning error else: it opens the wizard"""
    def validator(self, msg):
        if self.employee_id.user_id.id == self.env.user.id:
            raise ValidationError(
                "Sorry you are not allowed to reject /  return you own initiated memo"
                ) 

    def validate_memo_for_approval(self):
        item_lines = self.mapped('product_ids')
        type_required_items = ['material_request', 'procurement_request', 'vehicle_request']
        if self.memo_type.memo_key in type_required_items and self.state in ["Approve2"]:
            without_source_location_and_qty = item_lines.filtered(
                lambda sef: sef.source_location_id == False or sef.quantity_available < 1
                )
            if without_source_location_and_qty:
                raise ValidationError(
                     """Please ensure all request lines 
                     has a source location and quantity greater than 0"""
                     ) 
            
    def validate_compulsory_document(self):
        """Check if compulsory documents have uploaded"""  
        attachments = self.mapped('attachment_ids').filtered(
                    lambda iv: not iv.datas
                )
        if attachments:
            for count, doc in enumerate(attachments, 1):
                isn = doc.name.split('/')
                doc_name = isn[0] if isn else '-'
                matching_attachment = self.stage_id.mapped('required_document_line').filtered(
                    lambda dc: dc.name == doc_name
                )
                matching_stage_doc = matching_attachment and matching_attachment[0]
                if matching_stage_doc.compulsory and not doc.datas:
                    raise ValidationError(
                        f"""
                        Attachment with name '{doc.stage_document_name}' at line {count} does not have any data attached
                        """
                        )
                
    def validate_sub_stage(self):
        if self.memo_sub_stage_ids:
            for count, rec in enumerate(self.memo_sub_stage_ids, 1):
                if not rec.sub_stage_done:
                    raise ValidationError(f"""There are unfinished sub task at line {count} that requires completion before moving to the next stage""")
    
    def validate_invoice_line(self):
        '''Check all invoice in draft and check if 
        the current stage that matches it is compulsory
        if compulsory, system validates it'''
        invoice_ids = self.mapped('invoice_ids').filtered(
                    lambda iv: iv.state in ['draft']
                )
        if invoice_ids:
            for count, inv in enumerate(invoice_ids, 1):
                isn = inv.stage_invoice_name.split('/') if inv.stage_invoice_name else False
                inv_stage_name = isn[0] if isn else '-'
                matching_stage_invoice = self.stage_id.mapped('required_invoice_line').filtered(
                    lambda rinv: rinv.name == inv_stage_name
                )
                matching_stage_invoice = matching_stage_invoice and matching_stage_invoice[0]
                if matching_stage_invoice.compulsory:
                    if inv.payment_state not in ['paid', 'partial', 'in_payment']:
                        raise ValidationError(f"Invoice at line {count} must be posted and paid before proceeding")
                    invoice_line = inv.mapped('invoice_line_ids')
                    if not invoice_line:
                        raise ValidationError(f"Add at least one invoice billing line at line {count}")
                    invoice_line_without_price = inv.mapped('invoice_line_ids').filtered(
                        lambda s: s.price_unit <= 0
                        )
                    if invoice_line_without_price:
                        raise ValidationError(f"All invoice line must have a price amount greater than 0 at line {count}")
        
    def validate_soe_line(self):
        if self.memo_type.memo_key == "soe":
            soe_lines = self.mapped('product_ids')#.filtered(
            #     lambda s: s.to_retire == True)
            for r in soe_lines:
                if r.used_qty < 1 or r.used_amount < 1:
                        raise ValidationError(
                            'Each Request line item must have used qty and used amount greater than 0'
                    )
            # soe_line_not_cleared = self.mapped('product_ids').filtered(
            #     lambda s: s.to_retire == True)
            # for r in soe_line_not_cleared: 
            #     if r.used_qty < 0 or r.used_amount < 1:
            #         # if soe_line_not_cleared:
            #         raise ValidationError(
            #             'Each Request line item must have used qty and used amount greater than 0'
            #         )
            
    def build_po_line(self, order_id):
        '''args: order_id: the po_id already created'''
        po_ids = self.mapped('po_ids')
        request_lines = self.mapped('product_ids')
        po_products = []
        for po in po_ids:
            '''Filtered the products already added to po lines'''
            po_products.append(po.order_line.mapped('product_id'))
        exists = False
        for rq in request_lines:
            if not rq.product_id in po_products:
                orderlineval = {
                    'order_id': order_id.id,
                    'product_id': rq.product_id.id,
                    'product_uom_qty': rq.quantity_available,
                    'product_qty': rq.quantity_available,
                    'price_unit': rq.amount_total,
                }
                self.env['purchase.order.line'].create(orderlineval)
                exists = True
        if exists:
            self.update({'po_ids': [(4, order_id.id)]})
        else:
            order_id.button_cancel()
            order_id.unlink()
    
    def generate_po_from_request(self):
        if not self.user_in_stage_exists():
            raise ValidationError("You are not allowed to generate a PO lines. Kindly use request item tabs to request")
        if self.mapped('po_ids').filtered(
            lambda s: s.selected and s.state not in ['draft', 'sent', 'cancel']):
            raise UserError("You cannot generate PO again")
        vals = {
                'date_order': fields.Date.today(),
                'origin': self.code,
                'memo_id': self.id,
                'memo_type_key': self.memo_type_key,
                'memo_type': self.memo_type.id,
                'partner_id': 1 or 2,
            }
        po_id = self.env['purchase.order'].sudo().create(vals)
        if self.memo_setting_id.allow_multi_vending_on_po:
            self.build_multiple_vendor_line(po_id)
        else:
            self.build_po_line(po_id)
        view_id = self.env.ref('purchase.purchase_order_form').id
        ret = {
            'name': "Purchase Order",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'purchase.order',
            'res_id': po_id.id,
            'type': 'ir.actions.act_window', 
            'target': 'new',
            }
        return ret

    def generate_so_from_request(self):
        if not self.user_in_stage_exists():
            raise ValidationError("You are not allowed to generate a SO lines. Kindly use request item tabs to request")
        if self.mapped('so_ids').filtered(
            lambda s: s.selected and s.state not in ['draft', 'sent', 'cancel']):
            raise UserError("You cannot generate SO again")
        vals = {
                'date_order': fields.Date.today(),
                'origin': self.code,
                'memo_id': self.id,
                'memo_type_key': self.memo_type_key,
                'memo_type': self.memo_type.id,
                'partner_id': 1 or 2,
            }
        so_id = self.env['sale.order'].sudo().create(vals)
        
        self.build_so_line(so_id)
        view_id = self.env.ref('purchase.purchase_order_form').id
        ret = {
            'name': "Purchase Order",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'purchase.order',
            'res_id': so_id.id,
            'type': 'ir.actions.act_window', 
            'target': 'new',
            }
        return ret
    
    def build_multiple_vendor_line(self, order_id):
        request_lines = self.mapped('product_ids')
        exists = False
        for rq in request_lines:
            if not rq.product_id:
                raise UserError(f"No product id selected at request line")
            orderlineval = {
                'order_id': order_id.id,
                'name': rq.description or rq.product_id and rq.product_id.name,
                'product_id': rq.product_id and rq.product_id.id,
                'product_uom_qty': rq.quantity_available,
                'product_qty': rq.quantity_available,
                'price_unit': rq.amount_total,
                # 'tax_ids': [(6, 0, self.taxes_id.ids)] if not self.product_id.categ_id.sum_up_total or self.added_tax_ids else False,
                # 'added_tax_ids': [(6, 0, rq.product_id.categ_id.added_tax_ids.ids)],
            }
            po_line = self.env['purchase.order.line'].create(orderlineval)
        self.update({'po_ids': [(4, order_id.id)]})
    
    def user_in_stage_exists(self):
        user_in_stage_approvers = self.env.uid in [rec.user_id.id for rec in self.sudo().stage_id.approver_ids]
        if user_in_stage_approvers:
            return True
        else:
            return False
        
    def forward_memo(self):
        self.validate_necessary_components()
        self.validate_po_line()
        self.validate_so_line()
        self.validate_compulsory_document()
        self.validate_sub_stage()
        self.validate_invoice_line()
        self.validate_soe_line()
        if self.to_create_document:
            pass 
            attach_document_ids = self.env['ir.attachment'].sudo().search([
                    ('res_id', '=', self.id), 
                    ('res_model', '=', self._name)
                ])
            if not attach_document_ids:
                pass 
                # if not self.document_request_ids:
                #     raise ValidationError("Please kindly attach documents since this is a document submission request")
        if self.memo_type.memo_key == "Payment" and self.mapped('invoice_ids').filtered(
            lambda s: s.mapped('invoice_line_ids').filtered(
                lambda x: x.price_unit <= 0)):
            raise ValidationError("All invoice line must have a price amount greater than 0") 
        computed_approvers = [r.user_id.id for r in self.sudo().stage_id.approver_ids]
        manager_id = False
        if self.sudo().memo_setting_id.stage_ids.ids.index(self.sudo().stage_id.id) in [0, 1]:
            """checks if the stage is at draft and manager can approve if not configured"""
            manager_id = self.sudo().employee_id.parent_id.id or self.sudo().employee_id.administrative_supervisor_id.id
            computed_approvers.append(manager_id)
        if self.sudo().stage_id.approver_ids and self.env.user.id not in computed_approvers:
            raise ValidationError(
                """You are not allowed to Forward / Approve this record !!! \n Contact sys admin to add you as approver"""
                )
        if self.memo_type.memo_key == "Payment" and self.request_total_amount <= 0:
            raise ValidationError("Payment amount must be greater than 0.0")
        elif self.memo_type.memo_key == "material_request":
            if not self.product_ids:
                raise ValidationError("Please add request line") 
            if not self.mapped('product_ids').filtered(lambda s: not s.omit_record):
                raise ValidationError("Please add request line without omitted box checked") 
        
        
        
        # elif self.memo_type.memo_key == "soe":
        #     if self.mapped('product_ids').filtered(lambda x: x.used_qty < 1 and x.used_amount > 1)
        #     raise ValidationError("Please add request line") 
        view_id = self.env.ref('company_memo.memo_model_forward_wizard')
        condition_stages = [self.stage_id.yes_conditional_stage_id.id, self.stage_id.no_conditional_stage_id.id] or []
        approver_ids = self.sudo().stage_id.approver_ids
        approver_ids = manager_id if manager_id else approver_ids and approver_ids[0].id if approver_ids else False
        # raise ValidationError(self.env['hr.employee'].browse(approver_ids).name)
        return {
                'name': 'Forward Memo',
                'view_type': 'form',
                'view_id': view_id.id,
                'view_mode': 'form',
                'res_model': 'memo.foward',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_memo_record': self.id,
                    'default_resp': self.env.uid,
                    'default_direct_employee_id': approver_ids,
                    'default_dummy_conditional_stage_ids': [(6, 0, condition_stages)],
                    'default_has_conditional_stage': True if self.stage_id.memo_has_condition else False,
                    'default_stage_id': self.stage_id.id,
                },
            }
    """The wizard action passes the employee whom the memo was director to this function."""
    def get_initial_stage(self, config_id):
        memo_settings = self.env['memo.config'].sudo().search([
            ('id', '=', config_id),
            # ('memo_type', '=', memo_type),
            # ('department_id', '=', department_id)
            ], limit=1) or self.memo_setting_id if not self.to_create_document else self.document_memo_config_id # if self.document_memo_config_id else self.helpdesk_memo_config_id

        if memo_settings and memo_settings.stage_ids:
            initial_stage_id = memo_settings.stage_ids[0]
        else:
            initial_stage_id= self.env.ref('company_memo.memo_initial_stage')
        return initial_stage_id

    # def get_next_stage_artifact(self, current_stage_id, from_website=False):
    #     """
    #     args: from_website: used to decide if the record is 
    #     generated from the website or from odoo internal use
    #     """
    #     approver_ids = [] 
    #     document_memo_config_id = self.document_memo_config_id #hasattr(self.env['memo.model'], 'document_memo_config_id')
    #     helpdesk_memo_config_id = hasattr(self.env['memo.model'], 'helpdesk_memo_config_id')
    #     memo_settings = self.document_memo_config_id if self.document_memo_config_id and self.to_create_document \
    #         else self.helpdesk_memo_config_id if helpdesk_memo_config_id \
    #             else self.memo_setting_id 
    #     memo_setting_stages = memo_settings.mapped('stage_ids').filtered(
    #         lambda skp: skp.id != self.stage_to_skip.id
    #     )
    #     _logger.info(f'Found stages are ==> {self.memo_setting_id} --  {memo_settings} and {memo_setting_stages.ids}')
    #     if memo_settings and current_stage_id:
    #         mstages = memo_settings.stage_ids # [3,6,8,9]
    #         manager_can_approve = False
    #         last_stage = mstages[-1] if mstages else False # 'e.g 9'
    #         if last_stage and last_stage.id != current_stage_id.id:
    #             current_stage_index = memo_setting_stages.ids.index(current_stage_id.id)
    #             # if current_stage_index in [0, 1]: # Check here very well
    #             if current_stage_index == 0:
    #                 manager_can_approve = True
    #             next_stage_id = memo_setting_stages.ids[current_stage_index + 1] # to get the next stage
    #         else:
    #             next_stage_id = self.stage_id.id
    #         next_stage_record = self.env['memo.stage'].sudo().browse([next_stage_id])
    #         if next_stage_record:
    #             approver_ids = next_stage_record.approver_ids.ids
    #             if manager_can_approve:
    #                 manager_id = self.sudo().employee_id.parent_id.id or self.sudo().employee_id.administrative_supervisor_id.id
    #                 approver_ids.append(manager_id) 
    #         return approver_ids, next_stage_record.id
    #     else:
    #         if not from_website:
    #             raise ValidationError(
    #                 "Please ensure to configure the Memo type for the employee department"
    #                 )
    #         else:
    #             return False, False
    def get_next_stage_artifact(self, current_stage_id, from_website=False):
        """
        args: from_website: used to decide if the record is
        current_stage_id =stageObj, returns stage_id.id
        generated from the website or from odoo internal use
        """
        approver_ids = [] 
        
        memo_settings = self.memo_setting_id
        
        if self.to_create_document and self.document_memo_config_id:
            memo_settings = self.document_memo_config_id
            
        elif hasattr(self, 'helpdesk_memo_config_id') and self.helpdesk_memo_config_id:
             memo_settings = self.helpdesk_memo_config_id
        
        memo_setting_stages = memo_settings.mapped('stage_ids').filtered(
            lambda skp: skp.id != self.stage_to_skip.id
        )
        
        _logger.info(f'Found stages are ==> {self.memo_setting_id} --  {memo_settings} and {memo_setting_stages.ids}')
        
        if memo_settings and current_stage_id:
            mstages = memo_settings.stage_ids # [3,6,8,9]
            manager_can_approve = False
            last_stage = mstages[-1] if mstages else False 
            
            if last_stage and last_stage.id != current_stage_id.id:
                if current_stage_id.id in memo_setting_stages.ids:
                    current_stage_index = memo_setting_stages.ids.index(current_stage_id.id)
                else:
                    current_stage_index = 0

                # if current_stage_index in [0, 1]: # Check here very well
                if current_stage_index == 0:
                    manager_can_approve = True
                
                if current_stage_index + 1 < len(memo_setting_stages):
                    next_stage_id = memo_setting_stages.ids[current_stage_index + 1] 
                else:
                    next_stage_id = current_stage_id.id
            else:
                next_stage_id = self.stage_id.id
            
            next_stage_record = self.env['memo.stage'].sudo().browse([next_stage_id])
            
            if next_stage_record:
                approver_ids = next_stage_record.approver_ids.ids
                if manager_can_approve:
                    if self.sudo().employee_id.parent_id:
                        approver_ids.append(self.sudo().employee_id.parent_id.id)
                    elif self.sudo().employee_id.administrative_supervisor_id:
                        approver_ids.append(self.sudo().employee_id.administrative_supervisor_id.id)
            
            return approver_ids, next_stage_record.id
        else:
            if not from_website:
                raise ValidationError(
                    "Please ensure to configure the Memo type for the employee department"
                    )
            else:
                return False, False
    
    def build_po_line(self, order_id):
        '''args: order_id: the po_id already created'''
        po_ids = self.mapped('po_ids')
        request_lines = self.mapped('product_ids')
        po_products = []
        for po in po_ids:
            '''Filtered the products already added to po lines'''
            po_products.append(po.order_line.mapped('product_id'))
        exists = False
        for rq in request_lines:
            if not rq.product_id in po_products:
                orderlineval = {
                    'order_id': order_id.id,
                    'product_id': rq.product_id.id,
                    'product_uom_qty': rq.quantity_available,
                    'product_qty': rq.quantity_available,
                    'price_unit': rq.amount_total,
                }
                self.env['purchase.order.line'].create(orderlineval)
                exists = True
        if exists:
            self.update({'po_ids': [(4, order_id.id)]})
        else:
            order_id.button_cancel()
            order_id.unlink()
            
    def build_so_line(self, order_id):
        '''args: order_id: the so_id already created'''
        so_ids = self.mapped('so_ids')
        request_lines = self.mapped('product_ids')
        so_products = []
        for so in so_ids:
            '''Filtered the products already added to po lines'''
            so_products.append(so.order_line.mapped('product_id'))
        exists = False
        for rq in request_lines:
            if not rq.product_id in so_products:
                orderlineval = {
                    'order_id': order_id.id,
                    'product_id': rq.product_id.id,
                    'product_uom_qty': rq.quantity_available if rq.quantity_available > 0 else 1,
                    'price_unit': rq.amount_total,
                }
                self.env['sale.order.line'].create(orderlineval)
                exists = True
        if exists:
            self.update({'so_ids': [(4, order_id.id)]})
        else:
            order_id.action_cancel()
            order_id.unlink()

    def generate_sub_stage_artifacts(self, stage_id):
        sub_stage_ids = stage_id.sub_stage_ids
        self.has_sub_stage = True if stage_id.sub_stage_ids else False
        _logger.info('TRYY93')
        self.sudo().write({
                'memo_sub_stage_ids': [(3, exist_stage.id) for exist_stage in self.memo_sub_stage_ids],
                })
        if sub_stage_ids:
            for stg in sub_stage_ids:
                sub_stage = self.env['memo.sub.stage'].sudo().create({
                    'name': stg.name,
                    'memo_id': self.id,
                    'sub_stage_id': stg.id,
                    'approver_ids': stg.approver_ids.ids,
                    'description': stg.description,
                })
                invoices, documents = self.generate_required_artifacts(stg, sub_stage, '')
                sub_stage.sudo().write({
                'invoice_ids': [(4, iv) for iv in invoices],
                'attachment_ids': [(4, dc) for dc in documents]
                })
                
                self.sudo().write({
                'memo_sub_stage_ids': [(4, sub_stage.id)],
                })

    def function_generate_attachment(self, **kwargs):
        attachment_name, report_binary, mimetype,document_name, compulsory = kwargs.get('attachment_name'),\
            kwargs.get('report_binary'), kwargs.get('mimetype'), kwargs.get('document_name'), \
            kwargs.get('compulsory')
        code = kwargs.get('code')
        attachObj = self.env['ir.attachment']
        attachid = attachObj.search([('stage_document_name', '=', document_name),('code', '=', code)], limit=1) # recasting this means you must recast this line above
        if not attachid:
            attachid = attachObj.create({
                'name': attachment_name,
                # 'type': 'binary',
                'datas': report_binary,
                'store_fname': attachment_name,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': mimetype,
                'stage_document_name': document_name,
                'stage_document_required': compulsory,
                'code': code,
                'memo_id': self.id,
            })
        return attachid
    
    def function_generate_move_entries(self, **kwargs):
        """Check if the user is enlisted as the approver for memo type
        if approver is an account officer, system generates move and open the exact record"""
        # purchase payment journal
        movetype = kwargs.get('movetype')
        purchase_journal_id = self.env['account.journal'].sudo().search(
        [('type', '=', 'purchase'),
            # ('code', '=', 'BILL')
            ], limit=1)
        sale_journal_id = self.env['account.journal'].sudo().search(
        [('type', '=', 'sale'), ('code', '=', 'INV')], limit=1)
        journal_id = purchase_journal_id if movetype == 'in_invoice' else sale_journal_id
        if not journal_id:
            raise ValidationError(
                "No journal configured for accounting, kindly contact admin to create one."
                )
        invoice_name = kwargs.get('invoice_name') or "-"
        invoice_required = kwargs.get('invoice_required')
        account_move = self.env['account.move'].sudo()
        # Please be careful not to remove this name below, 
        # name = f"EXP-P/{invoice_name}/{kwargs.get('code')}"
        prefix = 'P000001' if movetype == 'in_invoice' else 'S000001'
        suffix = '100' if self.memo_type_key in ['import_process', 'export_process'] else '200'
        domain = ('move_type', '=', 'in_invoice') if movetype == 'in_invoice' else ('move_type', '=', 'out_invoice')
        last_invoice = self.env['account.move'].sudo().search(
            [('name', 'ilike', prefix), domain], 
            order="create_date desc", 
            limit=1
            )
        
        if last_invoice:
            lastinv = last_invoice.name.split('-')
            suffix = int(lastinv[1]) + 1 if len(lastinv) > 1 else suffix
        prefix_code = f"{prefix}-{suffix}"  
        name = prefix_code
        inv = account_move.search([('name', '=', name)], limit=1) # recasting this means you must recast this line above
        if not inv:
            partner_id = self.client_id or self.employee_id.user_id.partner_id or self.create_uid.partner_id
            inv = account_move.create({ 
                'memo_id': self.id,
                'ref': name, #f'{prefix_code}-{self.code}',
                'origin': self.code,
                'partner_id': partner_id.id,
                'company_id': self.env.user.company_id.id,
                'currency_id': self.env.user.company_id.currency_id.id,
                # Do not set default name to account move name, because it
                'name': name,
                'move_type': movetype,
                'invoice_date': fields.Date.today(),
                'date': fields.Date.today(),
                'journal_id': journal_id.id,
                'stage_invoice_name': invoice_name or '',
                'stage_invoice_required': invoice_required if invoice_required else False,
            })
        return inv
    
    # def confirm_document_to_repo(self):
    #     """check if attachments are completed"""
    #     submittedby = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
    #     for count, rec in enumerate(self.document_request_ids, 1):
    #         if rec.attachment_ids or rec.document_documents_ids:
    #             pass 
    #         else:
    #             raise ValidationError(f"""Please ensure requested attachments / documents are uploaded""")
            
    #         if rec.attachment_ids:
    #             no_request_attachment = rec.mapped('attachment_ids').filtered(lambda att: not att.datas)
    #             if no_request_attachment:
    #                 raise ValidationError(f"""Please ensure document request lines at line {count} - attachments are uploaded""")
    #             for att in rec.mapped('attachment_ids'):
    #                 vals = {
    #                     # 'folder_id': rec.request_to_document_folder.id,
    #                     'attachment_id': att.id,
    #                     # 'attachment_name': att.name,
    #                     'memo_id': self.id,
    #                     'datas': att.datas,
    #                     'res_id': self.id,
    #                     'res_model': 'memo.model',
    #                     # 'favourited_ids': [(6, 0, [r.user_id.id for r in self.users_followers])],
    #                     'is_shared': True,
    #                     'submitted_by': submittedby.id,
    #                     'submitted_date': fields.Date.today(),
                        
    #                 }
    #                 self.env['documents.document'].create(vals)
    #         if rec.document_documents_ids:
    #             for doc in rec.document_documents_ids:
                    
    #                 # rec.request_to_document_folder.sudo().write({
    #                 #     'document_ids': [(6, 0, [doc.id])] 
    #                 # })
    #                 doc.copy({
    #                     'department_id': self.sudo().employee_id.department_id.id,
    #                     'partner_id': self.sudo().employee_id.user_id.partner_id.id, 
    #                     'folder_id': rec.request_to_document_folder.id,
    #                     # 'attachment_id': doc.attachment_id.id,
    #                     'datas': doc.datas,
    #                 })
    #     self.confirm_memo(self.employee_id, "")
        
    def generate_required_artifacts(self, stage_id, obj, code=''):
        """This generate invoice lines from the configure stage"""
        stage_invoice_line = stage_id.mapped('required_invoice_line')
        stage_document_line = stage_id.mapped('required_document_line')
        invoices, documents= [], []
        _logger.info('TRY1')
        if stage_invoice_line:
            # if not self.client_id:
            #     raise ValidationError("This stage has a default invoice line setup.\n Client / Partner must be selected before invoice validation")
            for stage_inv in stage_invoice_line:
                already_existing_stage_invoice_line = obj.mapped('invoice_ids').filtered(
                    lambda exist: exist.stage_invoice_name == stage_inv.name and exist.state not in ['posted'])
                if not already_existing_stage_invoice_line:
                    movetype = 'in_invoice' if stage_inv.move_type == 'vendor' else 'out_invoice'
                    invid = self.function_generate_move_entries(
                        invoice_name = f"{stage_inv.name}/{self.id}/{self.stage_id.id}", invoice_required=stage_inv.compulsory, code=code, movetype=movetype)
                    
                    invoices.append(invid.id)

        if stage_document_line:
            _logger.info('TRY2')
            
            for stage_doc in stage_document_line:
                already_existing_stage_document_line = obj.mapped('attachment_ids').filtered(
                    lambda exist: exist.stage_document_name == stage_doc.name)
                if not already_existing_stage_document_line:
                    doc_name = f"EXP-P/{stage_doc.name}/{code}"
                    # ref = str(self.id)[] if str(self.id).startswith('NewId') else self.id
                    docid = self.function_generate_attachment(
                        attachment_name=stage_doc.name, 
                        report_binary = False, 
                        mimetype = False,
                        document_name = f"{stage_doc.name}-{self.id}-{stage_id.id}", 
                        compulsory=stage_doc.compulsory,
                        code=code
                        )
                    documents.append(docid.id)
                    
        return invoices, documents
    
    def update_status_badge(self):
        self.memo_bagde_undone = False #'Retired'
        if self.memo_type_key in ['material_request']:
            self.memo_material_request_status = True #'Issued'
        elif self.memo_type_key in ['procurement_request']:
            pending_receipts = self.mapped('po_ids').filtered(lambda x: x.receipt_status == 'pending')
            if pending_receipts:
                self.memo_awaiting_procurement_request_status = True 
                self.memo_procurement_request_status = False 

            else:
                self.memo_awaiting_procurement_request_status = False 
                # raise ValidationError('B')
                self.memo_procurement_request_status = True 

        elif self.memo_type_key in ['soe']:
            self.memo_soe_status = True #'Retired'
        else:
            self.memo_bagde_status = True #'Completed'

    def enable_edit_mode(self):
        self.edit_mode = True 
        for edit in self.product_ids:
            edit.edit_mode = True 
            
    def update_final_state_and_approver(self, from_website=False, default_stage=False, assigned_to=False):
        if from_website:
            # if from website args: prevents the update of stages and approvers 
            manager_id = self.sudo().employee_id.parent_id.id or self.sudo().employee_id.administrative_supervisor_id.id
            self.set_staff=manager_id if manager_id else self.sudo().stage_id.approver_ids[0].id  
        else:
            # updating the next stage
            approver_ids = self.get_next_stage_artifact(self.stage_id)[0] 
            next_stage_id= default_stage or self.get_next_stage_artifact(self.stage_id)[1] 
            _logger.info('TESTINGxxx 002')
            self.stage_id = next_stage_id
            invoices, documents = self.generate_required_artifacts(self.stage_id, self, self.code)
            self.sudo().write({
                'invoice_ids': [(4, iv) for iv in invoices],
                'attachment_ids': [(4, dc) for dc in documents]
                })
            _logger.info('TRYY11')
            
            self.generate_sub_stage_artifacts(self.sudo().stage_id)
            # determining the stage to update the already existing state used to hide or display some components
           
            if self.sudo().stage_id:
                _logger.info('TRYY3')
                if self.stage_id.is_approved_stage:
                    if self.memo_type_key in ['material_request']: 
                        # for now open material request location to set location of your stock move 
                        _logger.info('TRY3')
                        self.enable_edit_mode()
                        _logger.info('TRY4')
                    if self.memo_type.memo_key in ["Payment", 'loan', 'cash_advance', 'soe']:
                        self.state = "Approve"
                    else:
                        _logger.info('TRY4')
                        self.state = "Approve2"
                # important: users_followers must be required in for them to see the records.
                _logger.info('TRY5')
                if self.sudo().stage_id.approver_ids:
                    self.sudo().update({
                        'users_followers': [(4, appr.id) for appr in self.sudo().stage_id.approver_ids],
                        'set_staff': assigned_to if assigned_to else self.sudo().stage_id.approver_ids[0].id # FIXME To be reviewed
                        })
            _logger.info('TRY6')
            if self.memo_setting_id and self.memo_setting_id.stage_ids:
                ms = self.memo_setting_id.stage_ids
                last_stage = ms[-1]
                '''if id of next stage is the same with the id of the last stage of memo setting stages, 
                write stage to done'''
                _logger.info('TRY7')
                
                random_memo_approver_ids = [rec.id for rec in self.sudo().memo_setting_id.approver_ids if rec]
                if last_stage.id == next_stage_id:
                    employee_user_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
                    _logger.info('TRY8')
                    approver_ids = last_stage.approver_id.ids or random_memo_approver_ids
                    vals = {
                        'state': 'Done',
                        'approver_id': employee_user_id.id if employee_user_id else False
                        }
                    if approver_ids:
                        vals.update({
                            'approver_ids': [(4, appr) for appr in approver_ids],
                            })
                    _logger.info('TRY10')
                    
                    self.sudo().write(vals)
            _logger.info('SSGGOV 002')
                    
    def lock_artifacts_from_modification(self):
        attachments = self.mapped('attachment_ids')
        invoices = self.mapped('invoice_ids')
        for att in attachments:
            att.is_locked = True

        for inv in invoices:
            inv.is_locked = True
        
        if self.memo_sub_stage_ids:
            for sub in self.memo_sub_stage_ids:
                attachments = sub.mapped('attachment_ids')
                invoices = sub.mapped('invoice_ids')
                for subatt in attachments:
                    subatt.is_locked = True

                for subinv in invoices:
                    subinv.is_locked = True
                
    def confirm_memo(self, employee, comments, from_website=False, default_stage_id=False): 
        """default_stage_id: int"""
        type = "loan request" if self.memo_type.memo_key == "loan" else "memo"
        
        is_initial_submission = not self.action_history_ids and self.state == 'submit'
        current_user_is_approver = self.env.uid in [
            r.user_id.id for r in self.sudo().stage_id.approver_ids
        ]
        
        self.lock_artifacts_from_modification() # first locks already generated artifacts to avoid further modification
        if default_stage_id:
            next_stage = self.env['memo.stage'].browse(default_stage_id)
        else:
            _, next_stage_id = self.get_next_stage_artifact(self.stage_id, from_website)
            next_stage = self.env['memo.stage'].browse(next_stage_id)
        
        if is_initial_submission:
            action_type = 'submitted'
        elif current_user_is_approver:
            action_type = 'approved'
        else:
            action_type = 'approved'
        
        self._log_action(
            action=action_type,
            comments=comments,
            next_stage=next_stage
        )
        
        Beneficiary = self.employee_id.name # or self.user_ids.name
        body_msg = f"""Dear sir / Madam, \n \
        <br/>I wish to notify you that a {type} with description, {self.name},<br/>  
        from {Beneficiary} (Department: {self.sudo().employee_id.department_id.name or "-"})<br/> 
        was sent to you for review / approval. <br/> <br/>Kindly {self.get_url(self.id)}
        <br/> Yours Faithfully<br/>{self.env.user.name}""" 
        self.direct_employee_id = False 
        if default_stage_id:
            # first set the stage id and then update
            self.update_final_state_and_approver(from_website, default_stage_id)
        else:
            self.update_final_state_and_approver(from_website, False, employee.id)
        self.mail_sending_direct(body_msg, employee)
        body = "%s for %s initiated by %s, moved by- ; %s and sent to %s" %(
            type,
            self.name,
            Beneficiary,
            self.env.user.name,
            employee
            )
        body_main = body + "\n with the comments: %s" %(comments)
        self.follower_messages(body_main)
        self.message_subscribe(partner_ids=[rec.user_id.partner_id.id for rec in self.users_followers])
        self.portal_check_po_config(self.memo_setting_id)
    

    def mail_sending_direct(self, body_msg, email_to=False): 
        subject = "ERP Request Notification"
        email_from = self.env.user.email
        follower_list = [item2.work_email for item2 in self.users_followers if item2.work_email]
        stage_followers_list = [
            appr.work_email for appr in self.stage_id.memo_config_id.approver_ids if appr.work_email
            ] if self.stage_id.memo_config_id.approver_ids else []
        email_list = follower_list + stage_followers_list
        approver_emails = [eml.work_email for eml in self.stage_id.approver_ids if eml.work_email]
        if email_to and email_to.work_email:
            approver_emails.append(email_to.work_email)
            # approver_emails = approver_emails + [email_to.work_email]
        mail_to = (','.join(approver_emails))
        emails = (','.join(elist for elist in email_list))
        mail_data = {
                'email_from': email_from,
                'subject': subject,
                'email_to': mail_to,
                'reply_to': email_from,
                'email_cc': emails,
                'body_html': body_msg
            }
        mail_id = self.env['mail.mail'].sudo().create(mail_data)
        self.env['mail.mail'].sudo().send(mail_id)
    
    def _get_group_users(self):
        followers = []
        account_id = self.env.ref('company_memo.mainmemo_account')
        acc_group = self.env['res.groups'].sudo().search([('id', '=', account_id.id)], limit=1)
        for users in acc_group.users:
            employee = self.env['hr.employee'].sudo().search([('user_id', '=', users.id)])
            for rex in employee:
                followers.append(rex.id)
        return self.write({'users_followers': [(4, follow) for follow in followers]})
    
    def determine_if_user_is_config_approver(self):
        """
            This determines if the user is responsible to approve the memo as a Purchase Officer
            This will open up the procurement application to proceed with the respective record
        """
        memo_settings = self.env['memo.config'].sudo().search([
            ('id', '=', self.memo_setting_id.id)
            ], limit=1)
        memo_approver_ids = memo_settings.approver_ids
        user = self.env.user
        emloyee = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        is_approver_stage = memo_settings.mapped('stage_ids').filtered(lambda aps: aps.is_approved_stage)
        approver_stage_ids = is_approver_stage[0]
        approvers= []
        if approver_stage_ids:
            approvers = approver_stage_ids.approver_ids.ids
        if emloyee and emloyee.id in [emp.id for emp in memo_approver_ids] \
            or self.env.uid in [r.user_id.id for r in self.stage_id.approver_ids] or \
                emloyee.id in approvers:
            return True
        else:
            return False

    def complete_memo_transactions(self): # Always available to Some specific groups
        body = "ERP REQUEST COMPLETION NOTIFICATION: -Approved By ;\n %s on %s" %(self.env.user.name,fields.Date.today())
        body_msg = f"""Dear {self.sudo().employee_id.name}, 
        <br/>I wish to notify you that a {type} with description, '{self.name}',\
        from {self.sudo().employee_id.department_id.name or self.user_ids.name} \
        department have been Confirmed by {self.env.user.name}.<br/>\
        Respective authority should take note. \
        <br/>Kindly {self.get_url(self.id)} <br/>\
        Yours Faithfully<br/>{self.env.user.name}"""
        return self.generate_memo_artifacts(body_msg, body)

    def check_supervisor_comment(self):
        if self.memo_type.memo_key == "server_access":
            if self.sudo().employee_id.administrative_supervisor_id and not self.supervisor_comment:
                raise ValidationError(
                    """Please Inform the employee's supervisor to comment on this before approving 
                    """)
            elif not self.sudo().employee_id.administrative_supervisor_id and not self.manager_comment:
                raise ValidationError(
                    """Please Inform the employee's Manager to comment on this before approving 
                    """)
                    
    def user_approve_memo(self): # Always available to Some specific groups
        return self.approve_memo()

    def approve_memo(self): # Always available to Some specific groups
        ''' check if supervisor has commented on the memo if it is server access'''
        self.check_supervisor_comment()
        self.validate_necessary_components()
        self.validate_po_line()
        self.validate_so_line()
        self.validate_compulsory_document()
        self.validate_sub_stage()
        '''Determine if current user has access to approve'''
        is_config_approver = self.determine_if_user_is_config_approver()
        if self.env.uid == self.sudo().employee_id.user_id.id and not is_config_approver:
            raise ValidationError(
                """You are not Permitted to approve a Payment Memo. 
                Forward it to the authorized Person""")
        if self.env.uid not in [r.user_id.id for r in self.sudo().stage_id.approver_ids]:
            raise ValidationError(
                """You are not Permitted to approve this Memo. Contact the authorized Person"""
                )
        '''Request notication hardcorded'''
        body = "REQUEST APPROVE NOTIFICATION: -Approved By ;\n %s on %s" %(self.env.user.name,fields.Date.today())
        type = "request"
        body_msg = f"""Dear {self.sudo().employee_id.name}, <br/>I wish to notify you that a {type} with description, '{self.name}',\
                from {self.sudo().employee_id.department_id.name or self.user_ids.name} department have been approved by {self.env.user.name}.<br/>\
                Respective authority should take note. \
                <br/>Kindly {self.get_url(self.id)} <br/>\
                Yours Faithfully<br/>{self.env.user.name}"""
        users = self.env['res.users'].sudo().browse([self.env.uid])
        '''Update the stage'''
        _logger.info('TESTING 001')

        self.update_final_state_and_approver()
        self.sudo().write({'res_users': [(4, users.id)]})
        '''Generate memo artificate'''
        return self.generate_memo_artifacts(body_msg, body)
  
    def generate_memo_artifacts(self, body_msg, body):
        _logger.info('TESTING 003')
        if self.memo_type.memo_key == "material_request":
            _logger.info('TESTING 004')
            return self.generate_stock_material_request(body_msg, body)
        elif self.memo_type.memo_key == "procurement_request":
            return self.generate_stock_procurement_request(body_msg, body)
        elif self.memo_type.memo_key == "sale_request":
            return self.generate_sale_request(body_msg, body)
        elif self.memo_type.memo_key == "vehicle_request":
            return self.generate_vehicle_request(body_msg) 
        elif self.memo_type.memo_key == "recruitment_request":
            self.generate_recruitment_request(body_msg) 
        elif self.memo_type.memo_key == "leave_request":
            self.generate_leave_request(body_msg, body)
        elif self.memo_type.memo_key == "cash_advance":
            return self.generate_move_entries()
        elif self.memo_type.memo_key == "soe":
            return self.generate_soe_entries()
        elif self.memo_type.memo_key == "server_access":
            self.update_memo_type_approver()
            self.mail_sending_direct(body_msg)
        elif self.memo_type.memo_key == "employee_update":
            return self.generate_employee_update_request()
        elif self.memo_type.memo_key == "Payment":
            return self.Register_Payment()
        else:
            document_message = "Also check related documentation on the document management system" if self.to_create_document else ""
            body_msg = f"""Dear sir / Madam, \n \
            <br/>I wish to notify you that a {type} with description, {self.name},<br/>  
            from {self.employee_id.name} (Department: {self.employee_id.department_id.name or "-"}) \
            was sent to you for review / approval. <br/> {document_message} <br/> <br/>
            Kindly {self.get_url(self.id)} \
            <br/> Yours Faithfully<br/>{self.env.user.name}"""
            self.state = "Done"
            self.update_final_state_and_approver()
            self.direct_employee_id = False
            # self.generate_document_management()
            self.mail_sending_direct(body_msg)

    def generate_employee_update_request(self, body_msg=False):
        employee_ids = [rec.employee_id.id for rec in self.employee_transfer_line_ids]
        return {
              'name': 'Employee Transfer',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'hr.employee.transfer',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_employee_ids': employee_ids,
                  'default_employee_transfer_lines': self.employee_transfer_line_ids.ids
              },
        }

    is_inter_district_transfer = fields.Boolean("Is inter district transfer")
    external_stock_picking_id = fields.Many2one('stock.picking', "External stock picking id")
    
    def validate_stock_location_lines(self):
        for count, ln in enumerate(self.product_ids, 1):
            if not ln.omit_record:
                if self.is_inter_district_transfer:
                    if not ln.sudo().source_location_id.company_id.id == self.source_location_id.company_id.id:
                        raise ValidationError(f"""Source Location at line {count} does not relate to company where this request is sourcing from. Kindly select location that relates to {self.company_id.name}""")
            
    def generate_internal_transfer(self):
        user = self.env.user
        lc_views = ['view', 'transit', 'inventory']
        tvi_locations = self.env['stock.location'].sudo().search([
            ('company_id', '=', user.company_id.id),
            ('usage', 'in', lc_views),
            ])
        if not self.sudo().dest_location_id or not self.sudo().source_location_id or not self.sudo().picking_type_id:
            raise ValidationError('Please enter the source or destination location and or operation type')
        if not self.is_inter_district_transfer:
            if not self.sudo().picking_type_id.company_id.id == self.company_id.id:
                raise ValidationError(f'Operation type does not relate to {self.company_id.name} where this request is sourcing from')
        # if not self.is_inter_district_transfer:
        
        destination_id = False 
        if not self.is_inter_district_transfer:
            if not self.sudo().source_location_id.company_id.id == self.company_id.id:
                raise ValidationError(f'Source Location does not relate to {self.company_id.name} where this request is sourcing from')
        
            if not self.sudo().dest_location_id.company_id.id == self.company_id.id:
                raise ValidationError(f'Destination location does not relate to the company {self.company_id.name} this request is directed to. If this is an inter district transfer. Kindly click on the is inter district checkbox. ')
            if self.sudo().picking_type_id.code in ['internal', 'outgoing'] and self.sudo().dest_location_id.usage not in ['internal']:
                raise ValidationError(f'Destination location must be internal locations')
            destination_id = self.sudo().dest_location_id
        else:
            if not tvi_locations: 
                '''Use tvi_locations as destination location'''
                raise ValidationError(f'No View, loss or transit location found as Destination location for inter district transfer.')
            destination_id = tvi_locations[0]
            if not self.sudo().dest_location_id.company_id.id == self.employee_id.company_id.id:
                raise ValidationError(f'''Destination location does not relate to the requesters' company {self.employee_id.company_id.name} this request is going to''')
            
            if self.sudo().picking_type_id.company_id.id == self.sudo().dest_location_id.company_id.id:
                raise ValidationError(f'''Picking type company should not be the same as destination location company''')
            if self.sudo().dest_location_id.company_id.id == self.sudo().source_location_id.company_id.id:
                raise ValidationError(f'''This is an inter company transfer, source location company and destination location cannot be the same''')
            if user.company_id.id == self.sudo().company_id.id:
                raise ValidationError(f'''You cannot approve the internal material request because you do not belong to company where it was originated''')
            
        for ln in self.product_ids:
            """
                Enforce to disallow stock move that has no products qty in the location
                if Omit checked, system should not trigger validation on omitted records"""
            if not ln.omit_record:
                ln.onchange_location_check_available_qty()
                self.validate_stock_location_lines()
        
        stock_picking_type_out = self.sudo().picking_type_id # self.env.ref('stock.picking_type_out')
        stock_picking = self.env['stock.picking'].sudo()
        existing_picking = stock_picking.search([('origin', '=', self.code)], limit=1)
        
        warehouse_location_id = self.env['stock.warehouse'].sudo().search([
            ('company_id', '=', self.company_id.id) 
        ], limit=1)
        if existing_picking and existing_picking.state in ['draft', 'cancel']:
            # existing_picking.unlink()
            existing_picking = False 
        if not existing_picking:
            vals = {
                'scheduled_date': fields.Date.today(),
                'picking_type_id': stock_picking_type_out.id,
                'location_id': self.source_location_id.id,
                'location_dest_id': destination_id.id,
                'branch_id': self.employee_id.user_id.branch_id.id,
                'origin': self.code,
                'memo_id': self.id,
                'is_inter_district_transfer': True if self.is_inter_district_transfer else False,
                'company_id': self.company_id.id or self.source_location_id.company_id.id,
                'partner_id': self.employee_id.user_id.partner_id.id,
                'move_ids_without_package': [(0, 0, {
                                'name': self.code,
                                'picking_type_id': stock_picking_type_out.id,
                                'location_id': mm.source_location_id.id or stock_picking_type_out.default_location_src_id.id or mm.source_location_id.id or warehouse_location_id.lot_stock_id.id,
                                'location_dest_id': destination_id,
                                'product_id': mm.sudo().product_id.id,
                                # 'product_id': mm.sudo().product_id.id,
                                'product_uom_qty': mm.quantity_available,
                                'quantity_done': mm.quantity_available,
                                'date_deadline': self.date_deadline,
                                'company_id': self.company_id.id or self.source_location_id.company_id.id,
                }) for mm in self.mapped('product_ids').filtered(lambda s: not s.omit_record)]
            }
            stock = stock_picking.sudo().create(vals)
            stock.company_id = self.company_id.id
            for r in stock.move_ids_without_package:
                r.company_id = self.company_id.id
        else:
            stock = existing_picking
        self.stock_picking_id = stock.id
        return stock
    
    def generate_internal_transfer_for_interdistrict(self):
        user = self.env.user
        lc_views = ['customer']
        tvi_locations = self.env['stock.location'].sudo().search([
            ('company_id', '=', user.company_id.id),
            ('usage', 'in', lc_views),
            ])
        if not self.sudo().dest_location_id or not self.sudo().source_location_id or not self.sudo().picking_type_id:
            raise ValidationError('Please enter the source or destination location and or operation type')
        
        destination_id = False 
        
        if self.is_inter_district_transfer:
            if not tvi_locations: 
                '''Use tvi_locations as destination location'''
                raise ValidationError(f'No customer location found as Destination location for inter district transfer.')
            destination_id = tvi_locations[0]
            if not self.sudo().dest_location_id.company_id.id == self.employee_id.company_id.id:
                raise ValidationError(f'''Destination location does not relate to the requesters' company {self.employee_id.company_id.name} this request is going to''')
            
            if self.sudo().picking_type_id.company_id.id == self.sudo().dest_location_id.company_id.id:
                raise ValidationError(f'''Picking type company should not be the same as destination location company''')
            if self.sudo().dest_location_id.company_id.id == self.sudo().source_location_id.company_id.id:
                raise ValidationError(f'''This is an inter company transfer, source location company and destination location cannot be the same''')
            
        for ln in self.product_ids:
            """
                Enforce to disallow stock move that has no products qty in the location
                if Omit checked, system should not trigger validation on omitted records"""
            if not ln.omit_record:
                ln.onchange_location_check_available_qty()
                self.validate_stock_location_lines()
        
        stock_picking_type_out = self.sudo().picking_type_id # self.env.ref('stock.picking_type_out')
        stock_picking = self.env['stock.picking'].sudo()
        existing_picking = stock_picking.search([('origin', '=', self.code)], limit=1)
        
        # warehouse_location_id = self.env['stock.warehouse'].sudo().search([
        #     ('company_id', '=', self.company_id.id) 
        # ], limit=1)
        if existing_picking and existing_picking.state in ['draft', 'cancel']:
            for r in existing_picking:
                existing_picking.unlink()
            existing_picking = False 
        # raise ValidationError(existing_picking)
        if not existing_picking:
            company_id = self.source_location_id.company_id or user.company_id 
            vals = {
                'scheduled_date': fields.Date.today(),
                'picking_type_id': stock_picking_type_out.id,
                'location_id': self.source_location_id.id,
                'location_dest_id': destination_id.id,
                'branch_id': self.env.user.branch_id.id,
                'origin': self.code,
                'memo_id': self.id,
                'is_inter_district_transfer': True if self.is_inter_district_transfer else False,
                'company_id': company_id.id,
                'partner_id': self.env.user.partner_id.id,
                'move_ids_without_package': [(0, 0, {
                                'name': self.code,
                                'picking_type_id': stock_picking_type_out.id,
                                'location_id': mm.source_location_id.id, # or stock_picking_type_out.default_location_src_id.id or mm.source_location_id.id or warehouse_location_id.lot_stock_id.id,
                                'location_dest_id': destination_id,
                                'product_id': self.generate_inter_move_product(mm.sudo().product_id, company_id),
                                # 'product_id': mm.sudo().product_id.id,
                                'product_uom_qty': mm.quantity_available,
                                'quantity_done': mm.quantity_available,
                                'date_deadline': self.date_deadline,
                                'company_id': company_id.id,
                }) for mm in self.mapped('product_ids').filtered(lambda s: not s.omit_record)]
            }
            stock = stock_picking.sudo().create(vals)
            stock.company_id = company_id.id
            for r in stock.move_ids_without_package:
                r.company_id = company_id.id
        else:
            stock = existing_picking
        self.stock_picking_id = stock.id
        return stock
    
    def get_approvers(self):
        ms = self.sudo().memo_setting_id.mapped('stage_ids').filtered(
            lambda s: s.is_approved_stage
        )
        if ms and ms.approver_ids:
            if self.env.user.id in [r.user_id.id for r in ms.sudo().approver_ids]:
                return True 
        return False 
    
    def view_generate_stock_material_request(self):
        return self.generate_stock_material_request()
    
    def generate_stock_material_request(self, body_msg="", body=""):
        _logger.info('TESTING 002')
        if not self.get_approvers():
            raise ValidationError('You are not allowed to validate this record')
        self.generate_external_internal_stock_material_request()
        # if not self.is_inter_district_transfer:
        #     stock = self.generate_internal_transfer()  # main / first entry for the requesting company
        # else:
        #     stock = self.generate_internal_transfer_for_interdistrict()
        #     self.generate_external_interdistrict_stock_material_request() # second entry for the requesting company
        
            
        self.update_memo_type_approver()
        if body_msg:
            self.mail_sending_direct(body_msg)
        # is_config_approver = self.determine_if_user_is_config_approver() or self.get_approvers()
        # if is_config_approver:
        # self.stock_picking_id = stock.id
        # raise ValidationError(f'{stock.name} and piv {self.stock_picking_id.id}')
        """Check if the user is enlisted as the approver for memo type"""
        view_id = self.env.ref('stock.view_picking_form').id
        ret = {
            'name': "Stock Request",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'stock.picking',
            'res_id': self.stock_picking_id.id,
            'type': 'ir.actions.act_window',
            'domain': [],
            'target': 'current'
            }
        return ret

    def generate_inter_move_product(self, product, company):
        if product:
            product_code = product.code
            ProductObj = self.env['product.product'].sudo()
            existing_product = ProductObj.search(
                ['|', 
                ('default_code', '=', product_code), 
                ('barcode', '=', product_code), 
                ('company_id', '=', company.id)
                ], limit=1  # Add limit for performance
            )
            
            if existing_product:
                return existing_product.id
            else:
                _logger.info('CREATING PRODUCT: %s', product.name)
                # Use the ORIGINAL product parameter, not the search result
                new_product = ProductObj.create({
                    'name': product.name,
                    'default_code': product.code,  # Use code instead of name
                    'barcode': product.code,       # Use code instead of name
                    'company_id': company.id,      # Set company_id
                })
                return new_product.id
        else:
            raise ValidationError("No product line found to process")
           
    def generate_external_internal_stock_material_request(self):
        user = self.env.user
        dest_location = self.sudo().dest_location_id
        if not dest_location:
            raise ValidationError('Please enter the source or destination location and or operation type')
        
        '''check if this is inter company transfer'''
        source_loc_id = False
        destination_loc_id = False 
        stock_picking = self.env['stock.picking'].sudo()
        if self.sudo().source_location_id.company_id.id != dest_location.company_id.id: # not in [self.company_id.id, self.source_location_id.company_id.id] and self.source_location_id.branch_id.id :
            '''this condition means that it is inter company transfer'''
            if self.sudo().picking_type_id.company_id.id != self.sudo().source_location_id.company_id.id:
                raise ValidationError("Your picking type company must be the same as source location company ")
            
            if self.sudo().picking_type_id.code not in ['outgoing']:
                '''ensure the picking type company is not the same as destination company'''
                raise ValidationError("Your picking type must be set as delivery orders ")
            
            if self.sudo().picking_type_id.company_id.id == dest_location.company_id.id:
                '''ensure the picking type company is not the same as destination company'''
                raise ValidationError("Your picking type company must not be the same as destination location company ")
            
            if self.sudo().source_location_id.id == dest_location.id:
                '''ensure the source is not the same as destination location'''
                raise ValidationError("Source location and destination location cannot be the same")
            
            '''Get external source location for inter company'''
            vendor_source_loc_id = self.env['stock.location'].search([('usage','=', 'supplier'), ('company_id','=', dest_location.company_id.id)], limit=1)
            if not vendor_source_loc_id:
                raise ValidationError(f"To create external move for inter company transfer, ensure {dest_location.company_id.name} has location set as vendor location")
            
            source_loc_id = vendor_source_loc_id # location of the issuing company e.g ekwulobia
            
            '''Get external destination location for inter company'''
            destination_loc_id = dest_location  # location of the recieving company e.g mainpower distribution
            
            '''Got stock picking for the external company move'''
            stock_picking_type_in = self.env['stock.picking.type'].sudo().search(
            [('code', '=', 'incoming'), ('company_id', '=', dest_location.company_id.id)], limit=1)
            
            stock_picking_type_out = self.env['stock.picking.type'].sudo().search(
            [('code', '=', 'outgoing'), ('company_id', '=', dest_location.company_id.id)], limit=1)
            
            if not (stock_picking_type_in):
                raise ValidationError(f'System can not find any receipt picking type set for {dest_location.company_id.name}')
            
            if not (stock_picking_type_out):
                raise ValidationError(f'System can not find any outgoing picking type set for {dest_location.company_id.name}')
            
            '''checks if an external move has be created earlier, if found and state is in draft and cancel, delete it and recreate'''
            ##########################################################
            existing_picking = False
            
            if self.external_stock_picking_id and self.external_stock_picking_id.state in ['draft', 'cancel']:
                self.sudo().external_stock_picking_id.unlink()
                existing_picking = False
                
            existing_picking = self.external_stock_picking_id
            if not existing_picking:
                company_id = destination_loc_id.company_id
                vals = {
                    'scheduled_date': fields.Date.today(),
                    'picking_type_id': stock_picking_type_in.id,
                    'location_id': vendor_source_loc_id.id,
                    'location_dest_id': destination_loc_id.id,
                    'branch_id': destination_loc_id.branch_id.id,
                    'origin': f"INTER-CO/{self.code}",
                    # 'memo_id': self.id,
                    'company_id': company_id.id,
                    # 'partner_id': self.employee_id.user_id.partner_id.id,
                    'is_inter_district_transfer': True,
                    'move_ids_without_package': [(0, 0, {
                                    'name': self.code,
                                    'picking_type_id': stock_picking_type_out.id,
                                    'location_id': vendor_source_loc_id.id or stock_picking_type_out.default_location_src_id.id,
                                    'location_dest_id': dest_location.id,
                                    'product_id': self.generate_inter_move_product(mm.sudo().product_id, company_id),
                                    'product_uom_qty': mm.quantity_available,
                                    'quantity_done': mm.quantity_available,
                                    'date_deadline': self.date_deadline,
                                    'company_id': company_id.id,
                                    
                    }) for mm in self.mapped('product_ids').filtered(lambda s: not s.omit_record)]
                }
                stock = stock_picking.with_context(default_company_id=company_id.id).sudo().create(vals)
                stock.company_id = company_id.id
                for r in stock.move_ids_without_package:
                    r.company_id = company_id.id
            else:
                stock = existing_picking
            self.external_stock_picking_id = stock.id 
            
            
            ##########################################################
            # this will also create internal stock transfer
            '''generate internal stock transfer'''
            '''Get customer delivery location for inter company'''
            customer_destination_loc_id = self.env['stock.location'].search([('usage','=', 'customer'), ('company_id','=', self.source_location_id.company_id.id)], limit=1)
            if not customer_destination_loc_id:
                raise ValidationError("To create move for inter company transfer, ensure you have a location with usage set as customer location")
            existing_picking = False
            if self.stock_picking_id and self.stock_picking_id.state in ['draft', 'cancel']:
                self.sudo().stock_picking_id.unlink()
            existing_picking = self.stock_picking_id
            
            if not existing_picking:
                company_id = self.source_location_id.company_id
                vals = {
                    'scheduled_date': fields.Date.today(),
                    'picking_type_id': self.picking_type_id.id,
                    'location_id': self.source_location_id.id,
                    'location_dest_id': customer_destination_loc_id.id,
                    'branch_id': self.source_location_id.branch_id.id,
                    'origin': f"{self.code}",
                    # 'memo_id': self.id,
                    'company_id': company_id.id,
                    # 'partner_id': self.employee_id.user_id.partner_id.id,
                    'is_inter_district_transfer': False,
                    'move_ids_without_package': [(0, 0, {
                                    'name': self.code,
                                    'picking_type_id': stock_picking_type_out.id,
                                    'location_id': self.source_location_id.id,
                                    'location_dest_id': customer_destination_loc_id.id,
                                    'product_id': self.generate_inter_move_product(mm.sudo().product_id, company_id),
                                    'product_uom_qty': mm.quantity_available,
                                    'quantity_done': mm.quantity_available,
                                    'date_deadline': self.date_deadline,
                                    'company_id': company_id.id,
                                    
                    }) for mm in self.mapped('product_ids').filtered(lambda s: not s.omit_record)]
                }
                existing_picking = stock_picking.with_context(default_company_id=company_id.id).sudo().create(vals)
                existing_picking.company_id = company_id.id
                for r in existing_picking.move_ids_without_package:
                    r.company_id = company_id.id
            else:
                existing_picking = existing_picking
            self.stock_picking_id = existing_picking.id
        
         # this is internal or inter district transfer
                
        else:  #elif self.sudo().source_location_id.company_id.id == dest_location.company_id.id: # this is internal or inter district transfer
            
            if self.sudo().source_location_id.branch_id.id != dest_location.branch_id.id:
                '''this condition means that it probably is an inter district transfer'''
                if self.sudo().picking_type_id.code not in ['outgoing']:
                    raise ValidationError("Your picking type must be set as delivery orders ")
                # if self.sudo().source_location_id.branch_id.id == dest_location.branch_id.id:
                #     '''ensure the source branch is not the same as destination location branch'''
                #     raise ValidationError("Source location district / branch and destination location  district / branch cannot be the same: This looks like an inter-district transfer")
                if self.sudo().source_location_id.company_id.id != dest_location.company_id.id:
                    '''ensure the source is the same as destination location'''
                    raise ValidationError("""
                        Source and destination location company must be the same: This looks like an inter-district transfer
                        """)
                
                if (self.sudo().picking_type_id.company_id.id not in [self.sudo().source_location_id.company_id.id, dest_location.company_id.id]):
                    '''Ensure the picking type company is the same as source and destination company'''
                    raise ValidationError("Your picking type company must be the same as source & destination location company ")
                 
            else:
                if self.sudo().picking_type_id.code not in ['internal']:
                    raise ValidationError("Your picking type must be set as internal transfer ")
                if self.sudo().source_location_id.usage != 'internal' or dest_location.usage != 'internal':
                    '''ensure source and destination type is set as internal for internal transfer.'''
                    raise ValidationError("""
                        Source and destination must be internal location.
                        """)
                    
            '''checks if an external move has be created earlier, if found and state is in draft and cancel, delete it and recreate'''
            existing_picking = False
            
            if self.stock_picking_id and self.stock_picking_id.state in ['draft', 'cancel']:
                self.sudo().stock_picking_id.unlink()
            existing_picking = self.stock_picking_id
            
            if not existing_picking:
                company_id = self.sudo().source_location_id.company_id
                vals = {
                    'scheduled_date': fields.Date.today(),
                    'picking_type_id': self.sudo().picking_type_id.id,
                    'location_id': self.sudo().source_location_id.id,
                    'location_dest_id': dest_location.id,
                    'branch_id': self.sudo().source_location_id.branch_id.id,
                    'origin': f"{self.code}",
                    # 'memo_id': self.id,
                    'company_id': company_id.id,
                    # 'partner_id': self.employee_id.user_id.partner_id.id,
                    'is_inter_district_transfer': True,
                    'move_ids_without_package': [(0, 0, {
                                    'name': self.code,
                                    'picking_type_id': self.sudo().picking_type_id.id,
                                    'location_id': self.sudo().source_location_id.id,
                                    'location_dest_id': dest_location.id,
                                    'product_id': self.generate_inter_move_product(mm.sudo().product_id, company_id),
                                    'product_uom_qty': mm.quantity_available,
                                    'quantity_done': mm.quantity_available,
                                    'date_deadline': self.date_deadline,
                                    'company_id': company_id.id,
                                    
                    }) for mm in self.mapped('product_ids').filtered(lambda s: not s.omit_record)]
                }
                stock = stock_picking.with_context(default_company_id=company_id.id).sudo().create(vals)
                stock.company_id = company_id.id
                for r in stock.move_ids_without_package:
                    r.company_id = company_id.id
            else:
                stock = existing_picking
            self.stock_picking_id = stock.id
            
            
            
    def generate_stock_procurement_request(self, body_msg, body):
        """
        Check po record if already create, popup the wizard, 
        else create pO and pop up the wizard
        """
        # stock_picking_type_in = self.env.ref('stock.picking_type_in')
        # purchase_obj = self.env['purchase.order']
        if not self.po_ids:
            raise ValidationError('''Please kindly click generate Purchase Order button from the purchase order tab
                '''
                )
        # existing_po = purchase_obj.search([('memo_id', '=', self.id)])
        # if not existing_po:

        #     vals = {
        #         'date_order': self.date,
        #         # 'picking_type_id': stock_picking_type_in.id,
        #         'origin': self.code,
        #         'memo_id': self.id,
        #         'partner_id': self.employee_id.user_id.partner_id.id,
        #         'order_line': [(0, 0, {
        #                         'product_id': mm.product_id.id,
        #                         'name': mm.description or f'{mm.product_id.name} Requistion',
        #                         'product_qty': mm.quantity_available,
        #                         'price_unit': mm.amount_total,
        #                         'date_planned': self.date,
        #         }) for mm in self.product_ids]
        #     }
        #     po = purchase_obj.create(vals)
        # else:
        #     po = existing_po
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)
        is_config_approver = self.determine_if_user_is_config_approver()
        self.update_status_badge()
        # if is_config_approver:
        #     """Check if the user is enlisted as the approver for memo type"""
        #     self.follower_messages(body)
        #     view_id = self.env.ref('purchase.purchase_order_form').id
        #     ret = {
        #         'name': "Purchase Order",
        #         'view_mode': 'form',
        #         'view_id': view_id,
        #         'view_type': 'form',
        #         'res_model': 'purchase.order',
        #         'res_id': po.id,
        #         'type': 'ir.actions.act_window',
        #         'domain': [],
        #         'target': 'new'
        #         }
        #     return ret
       
    def generate_sale_request(self, body_msg, body):
        if not self.so_ids:
            raise ValidationError('''Please kindly click generate sale Order button from the sale order tab
                '''
                )
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)
        is_config_approver = self.determine_if_user_is_config_approver()
        self.update_status_badge()
          
    def check_available_fleet_before_assignment(self, productid):
        available_fleet = self.env['product.product'].sudo().search([
                ('is_available', '=', True),
                ('id', '=', productid.id)
            ])
        if available_fleet:
            return True
        return False

    def check_driver_assignment(self):
        not_assigned_driver = self.mapped('product_ids').filtered(
            lambda d:not d.driver_assigned
            )
        if not_assigned_driver:
            raise ValidationError(
                "All vehicle request line must be assigned to a driver"
                )
            
    stock_picking_id = fields.Many2one(
        "stock.picking",
        string="Stock picking"
        )
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Operation type", 
        )
    edit_mode = fields.Boolean(
        string="Edit mode", 
        default=True,
        help="Allow some fields to be editable"
        )
    source_location_id = fields.Many2one("stock.location", string="Source Location")
    dest_location_id = fields.Many2one("stock.location", string="Destination Location")
    
    @api.onchange('dest_location_id')
    def on_change_of_destination_location(self):
        if self.dest_location_id:
            if not self.source_location_id:
                raise ValidationError("Please first select the source location")
            else:
                if self.dest_location_id.id == self.source_location_id.id:
                    self.source_location_id = False
                    raise ValidationError("Destination location and source location cannot be the same")
                # if self.is_inter_district_transfer:
                #     if self.dest_location_id.company_id.id != self.company_id.id:
                #         self.dest_location_id = False
                #         raise ValidationError("Destination location company must be the same as company since this is an inter company transfer")
                # else:
                #     if self.dest_location_id.company_id.id != self.company_id.id:
                #         self.dest_location_id = False
                #         raise ValidationError("Destination location company must be the same as company since this is an internal transfer")
            
            for des in self.product_ids:
                des.dest_location_id = self.dest_location_id.id
                
    @api.onchange('source_location_id')
    def on_change_of_source_location_id(self):
        if self.source_location_id:
            for des in self.product_ids:
                des.source_location_id = self.source_location_id.id
                 
    def generate_vehicle_request(self, body_msg):
        # generate fleet asset
        Fleet = self.env['memo.fleet'].sudo()
        self.vehicle_trip_ids = False
        fleet_trips, unavailable_fleets = [], []
        for count, line in enumerate(self.product_ids, 1):
            if not line.omit_record:
                self.check_driver_assignment()
                available = self.check_available_fleet_before_assignment(line.product_id)
                if available:
                    vals= {'memo_id': self.id,
                            'vehicle_assigned': line.product_id.id,
                            'driver_assigned': line.driver_assigned.id,
                            'source_location_id': line.distance_from,
                            'source_destination_id': line.distance_to,
                            'active': True,
                            'code': self.code + str(self.id) + str(count), # REF00701
                    }
                    if line.fleet_id:
                        fleet_id = line.fleet_id
                        line.fleet_id.update(vals)
                    else:
                        fleet_id = Fleet.create(vals)
                        line.update({
                            'fleet_id': fleet_id.id
                            })
                    self.vehicle_trip_ids = [(4, fleet_id.id)]
                    fleet_trips.append(fleet_id.id)
                else:
                    unavailable_fleets.append(line.product_id.vehicle_plate_number or line.product_id.name)
        unavail_fleets = '\n,'.join(unavailable_fleets)
        warning_message = f"""Warning : The requested fleets with name / Reg number are (is) not available: See below; {unavail_fleets} """ if unavail_fleets else '',
        self.state = 'Done'
        self.is_request_completed = True
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)
        if unavailable_fleets:
            dialog = self.env['memo.dialog'].sudo().create({
                'name': warning_message
            })
            return {
            'name': f"Warning:",
            'view_mode': 'form',
            # 'view_id': view_id,
            'view_type': 'form',
            'res_model': 'memo.dialog',
            'res_id': dialog.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
            }
        
    # def generate_leave_request(self, body_msg, body):
    #     leave = self.env['hr.leave'].sudo()
    #     vals = {
    #         'employee_id': self.employee_id.id,
    #         'request_date_from': self.leave_start_date,
    #         'request_date_to': self.leave_end_date,
    #         'date_from': self.leave_start_date,
    #         'date_to': self.leave_end_date,
    #         'name': BeautifulSoup(self.description or "Leave request", features="lxml").get_text(),
    #         'holiday_status_id': self.leave_type_id.id,
    #         'origin': self.code,
    #         'memo_id': self.id,
    #     }
    #     leave_id = leave.with_context(
    #                     tracking_disable=False,
    #                     mail_activity_automation_skip=False,
    #                     leave_fast_create=True,
    #                     leave_skip_state_check=True
    #                 ).create(vals)
    #     leave_id.action_approve()
    #     leave_id.action_validate()
    #     # update memo stages where the applicant exists with reliever
    #     self.set_reliever_to_act_as_employee_on_leave(
    #         self.sudo().employee_id,
    #         self.sudo().leave_Reliever,
    #     )
    #     self.state = 'Done'
    #     self.mail_sending_direct(body_msg)
    
    def generate_leave_request(self, body_msg, body):
        leave = self.env['hr.leave'].sudo()
        
        # --- FIX: Set explicit Start/End times ---
        # Odoo stores dates in UTC. 
        # For Nigeria (GMT+1): 
        # 07:00 UTC = 08:00 Local (Start of Work)
        # 16:00 UTC = 17:00 Local (End of Work)
        # This ensures the last day is counted fully.
        start_time = time(7, 0, 0) 
        end_time = time(16, 0, 0)
        
        # Combine the Date fields with the Time
        dt_from = datetime.combine(self.leave_start_date, start_time)
        dt_to = datetime.combine(self.leave_end_date, end_time)

        vals = {
            'employee_id': self.employee_id.id,
            'request_date_from': self.leave_start_date,
            'request_date_to': self.leave_end_date,
            
            'date_from': dt_from,
            'date_to': dt_to,
            
            'name': BeautifulSoup(self.description or "Leave request", features="lxml").get_text(),
            'holiday_status_id': self.leave_type_id.id,
            'origin': self.code,
            'memo_id': self.id,
        }
        
        leave_id = leave.with_context(
                        tracking_disable=False,
                        mail_activity_automation_skip=False,
                        leave_fast_create=True,
                        leave_skip_state_check=True
                    ).create(vals)
        
        leave_id._compute_number_of_days()
        
        leave_id.action_approve()
        leave_id.action_validate()
        
        self.set_reliever_to_act_as_employee_on_leave(
            self.sudo().employee_id,
            self.sudo().leave_Reliever,
        )
        
        self.state = 'Done'
        self.mail_sending_direct(body_msg)

    def generate_recruitment_request(self, body_msg=False):
        """
        Create HR job application ready for publication 
        """
        recruitment_request_obj = self.env['hr.job.recruitment.request'].sudo()
        existing_hrr = recruitment_request_obj.search([
            ('memo_id', '=', self.id),
            ], limit=1)
        if not existing_hrr:
            vals = {
                'job_tmp': self.job_tmp,
                'department_id': self.sudo().requested_department_id.id,
                'name': self.name,
                'memo_id': self.id,
                'recruitment_mode': self.recruitment_mode,
                'job_id': self.job_id.id,
                'user_id': self.employee_id.user_id.id,
                'user_to_approve_id': random.choice([r.user_id.id for r in self.sudo().stage_id.approver_ids]),
                'expected_employees': self.expected_employees,
                'recommended_by': self.sudo().recommended_by.user_id.id,
                'description': BeautifulSoup(self.description or "-", features="lxml").get_text(),
                'requirements': self.qualification,
                'age_required': self.age_required,
                'years_of_experience': self.years_of_experience,
                'state': 'accepted',
                'date_expected': self.date_expected,
                'date_accepted': fields.Date.today(),
                'date_confirmed': fields.Date.today(),
            }
            rr_id = recruitment_request_obj.create(vals)
        else:
            rr_id = existing_hrr
        self.update_memo_type_approver()
        if body_msg:
            self.mail_sending_direct(body_msg)
        self.state = 'Done'
        """Check if the user is enlisted as the approver for memo type"""
        view_id = self.env.ref('hr_cbt_portal_recruitment.hr_job_recruitment_request_form_view').id
        ret = {
            'name': "Recruitment request",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'hr.job.recruitment.request',
            'res_id': rr_id.id,
            'type': 'ir.actions.act_window',
            'domain': [],
            'target': 'current'
            }
        return ret

    def get_move_line_expense_account(self, pr, journal_id=False):
        '''pr: line'''
        account_id = None
        company_cash_advance_account_id = self.company_id.default_cash_advance_account_id
        account_id = company_cash_advance_account_id
            # else pr.product_id.property_account_expense_id \
            # if pr.product_id.property_account_expense_id else pr.product_id.categ_id.property_account_expense_categ_id
        # if journal_id and journal_id.default_account_id:
        #     account_id = journal_id.default_account_id
        if not account_id:
            raise ValidationError(f"No cash advance / asset account found for company {self.company_id.name} at {pr.product_id.name or pr.description} line . System admin should go to the company configuration and select the cash advance account...")
        return account_id
    
    def get_cashadvance_debit_account(self, pr, journal_id=False):
        '''pr: line'''
        account_id = None
        payment_company = self.processing_company_id or self.company_id or self.env.user.company_id
        company_expense_account_id = payment_company.default_cash_advance_account_id
        # account_id = company_expense_account_id # or journal_id and journal_id.default_account_id
        if not company_expense_account_id:
            raise ValidationError(f"No default cash advance account found for company {payment_company} at {pr.product_id.name or pr.description} line . System admin should go to the company configuration and set the cash advance account..")
        return company_expense_account_id.id if company_expense_account_id else None
    
    def get_cashadvance_credit_account(self, journal_id=False):
        '''pr: line'''
        account_id = None
        payment_company = self.processing_company_id or self.company_id
        company_expense_account_id = payment_company.default_bank_cash_account_id
        account_id = company_expense_account_id # or journal_id and journal_id.default_account_id
        if not account_id:
            raise ValidationError(f"{payment_company.name} does not have default bank account to use on credit line . System admin should go to the company configuration and set the default bank account or set the journal default account...")
        return account_id
    
    def get_soe_expense_account(self, pr, journal_id=False):
        '''pr: line'''
        account_id = None
        payment_company = self.sudo().processing_company_id or self.sudo().company_id
        company_expense_account_id = payment_company.account_default_debit_account_id
        account_id = company_expense_account_id or journal_id and journal_id.default_account_id
        if not account_id:
            raise ValidationError(f"No default expense account found for company {payment_company.name} at {pr.product_id.name or pr.description} line . System admin should go to the company configuration and set the default expense account or set the journal default expense account...")
        return account_id
    
    def get_soe_credit_account(self, journal_id=False):
        '''pr: line'''
        account_id = None
        payment_company = self.sudo().processing_company_id or self.sudo().company_id
        company_expense_account_id = payment_company.default_cash_advance_account_id
        account_id = company_expense_account_id or journal_id and journal_id.default_account_id
        if not account_id:
            raise ValidationError(f"No default cash advance found to use on credit lines for company {payment_company.name} . System admin should go to the company configuration and set the default cash advance account or set the journal default account...")
        return account_id
                    
    # def generate_move_entries(self):
    #     is_config_approver = self.determine_if_user_is_config_approver()
    #     if is_config_approver:
    #         """Check if the user is enlisted as the approver for memo type
    #         if approver is an account officer, system generates move and open the exact record"""
    #         view_id = self.env.ref('account.view_move_form').id
    #         journal_id = self.env['account.journal'].sudo().search(
    #          [('company_id', '=', self.company_id.id),
    #         '|',('type', '=', 'purchase'),
    #          ('code', '=', 'BILL'),
    #          ], limit=1)
    #         if not journal_id:
    #             raise UserError(f"""
    #                             You do have any journal set to the current company {self.company_id.name} 
    #                             with type in 'purchase' or journal code set as 'BILL'
    #                             """
    #                             )
    #         account_move = self.env['account.move'].sudo()
    #         inv = account_move.search([('memo_id', '=', self.id)], limit=1)
    #         if not inv:
    #             partner_id = self.vendor_id or self.client_id or self.sudo().employee_id.user_id.partner_id or self.create_uid.partner_id
    #             # partner_id = self.employee_id.user_id.partner_id
    #             inv = account_move.create({ 
    #                 'memo_id': self.id,
    #                 'ref': self.code,
    #                 'origin': self.code,
    #                 'partner_id': partner_id.id,
    #                 'company_id': self.company_id.id,
    #                 'currency_id': self.company_id.currency_id.id,
    #                 'branch_id': self.sudo().employee_id.user_id.branch_id and self.sudo().employee_id.user_id.branch_id.id,
    #                 # Do not set default name to account move name, because it
    #                 # is unique 
    #                 'name': f"{self.id}/ {self.code}",
    #                 'move_type': 'in_receipt',
    #                 'invoice_date': fields.Date.today(),
    #                 'invoice_date_due': fields.Date.today(),
    #                 'date': fields.Date.today(),
    #                 'journal_id': journal_id.id,
	# 			    'branch_id': self.employee_id.branch_id.id,
    #                 'invoice_line_ids': [(0, 0, {
    #                         'name': pr.product_id.name if pr.product_id else pr.description,
    #                         'ref': f'{self.code}: {pr.product_id.name or pr.description}',
    #                         'account_id': self.get_move_line_expense_account(pr, journal_id).id, # or journal_id.default_account_id.id,
    #                         # 'account_id': pr.product_id.property_account_expense_id.id or pr.product_id.categ_id.property_account_expense_categ_id.id if pr.product_id else journal_id.default_account_id.id,
    #                         # 'account_id': self.memo_setting_id.expense_account_id.id if self.memo_setting_id.expense_account_id else pr.product_id.property_account_expense_id.id or pr.product_id.categ_id.property_account_expense_categ_id.id if pr.product_id and pr.product_id.property_account_expense_id or pr.product_id.categ_id.property_account_expense_categ_id else journal_id.default_account_id.id,
    #                         'price_unit': pr.amount_total,
    #                         'quantity': pr.quantity_available,
    #                         'discount': 0.0,
    #                         'code': pr.code,
    #                         'company_id': self.company_id.id,
	# 			            'branch_id': self.employee_id.user_id.branch_id.id,
    #                         'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
    #                         'product_id': pr.product_id.id if pr.product_id else None,
    #                         'tax_ids': False,
    #                         'lock_fields_from_memo': False,
    #                 }) for pr in self.product_ids],
    #             })
    #         self.move_id = inv.id
    #         return self.record_to_open(
    #         "account.move", 
    #         view_id,
    #         inv.id,
    #         f"Journal Entry - {inv.name}"
    #         )
    #     else:
    #         raise ValidationError("Sorry! You are not allowed to validate cash advance payments. \n To resolve, go to the memo config and select the current user in the Employees to followup field")
    
    # TODO Take to easypayFix
    invoice_status = fields.Char(string="Account status", compute="compute_move_state")
    @api.depends('move_id')
    def compute_move_state(self):
        for rec in self:
            if rec.sudo().move_id:
                rec.invoice_status = rec.sudo().move_id.state
            else:
                rec.invoice_status = 'Not Posted'
                
    def generate_move_entries(self): 
        '''thi will generate cash advance move'''
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
            """Check if the user is enlisted as the approver for request type
            if approver is an account officer, system generates move and open the exact record"""
            
            payment_company = self.processing_company_id or self.company_id
            payment_branch = self.processing_branch_id or self.branch_id
            
            current_user_company = self.env.user.company_id
            
            _logger.info(
                f"Payment Processing Details:\n"
                f"  Request ID: {self.code}\n"
                f"  Request Company: {self.company_id.name}\n"
                f"  Payment Will Be In: {payment_company.name}\n"
                f"  Payment Branch: {payment_branch.name}\n"
                f"  Current User: {self.env.user.name}\n"
                f"  User Company: {current_user_company.name}"
            )
            
            view_id = self.env.ref('account.view_move_form').id
            journal_id = self.env['account.journal'].sudo().search(
            [
                ('company_id', '=', payment_company.id),
                # ('type', 'in', ['bank', 'general']),
                ('type', 'in', ['purchase']),
             ], limit=1) or self.journal_id
            if not journal_id:
                raise UserError(f"No purchase journal configured for company: {payment_company.name} Contact admin to setup before proceeding")
            account_move = self.env['account.move'].sudo()
            inv = account_move.search([('memo_id', '=', self.id)], limit=1)
            # delete the invoice to recreate if error
            if inv and inv.state in ['cancel', 'draft']:
                inv.unlink() # delete the invoice to recreate if error
                inv = False
            #### deleted the found invoice
            if not inv:
                partner_id = self.vendor_id or self.client_id or self.sudo().employee_id.user_id.partner_id or self.create_uid.partner_id
                rate_line = self.currency_id.rate_ids.filtered(
                lambda r: fields.Date.to_date(r.name) <= fields.Date.today()
                ).sorted(key=lambda r: r.name, reverse=True)[:1]
                
                inv = account_move.create({ 
                    'memo_id': self.id,
                    'ref': self.code,
                    'origin': self.code,
                    'hide_invoice_line': True,
                    'partner_id': partner_id.id,
                    'company_id': payment_company.id,
                    # 'currency_id': self.currency_id.id or payment_company.currency_id.id,
                    'currency_id': payment_company.currency_id.id,
                    'conversion_rate': self.conversion_rate if self.conversion_rate > 0 else rate_line.inverse_company_rate,
                    'branch_id': payment_branch.id,
                    # Do not set default name to account move name, because it
                    # is unique 
                    'name': f"{self.code}", # /{self.id}", # /{fields.Date.today().month}/{fields.Date.today().year}",
                    'move_type': 'in_invoice', #  if self.memo_type_key in ['procurement_request', 'procurement', 'cash_advance', 'payment', 'Payment'] else 'entry',
                    'invoice_date': fields.Date.today(),
                    'invoice_date_due': fields.Date.today(),
                    'date': fields.Date.today(),
                    'journal_id': journal_id.id,
				    # 'branch_id': self.employee_id.branch_id.id,
                    
                    'line_ids': [(0, 0, {
                            'name': pr.product_id.name if pr.product_id else pr.description,
                            'ref': f'{self.code}: {pr.product_id.name or pr.description}',
                            'price_unit': pr.amount_total,
                            'quantity': pr.quantity_available,
                            'account_id': self.get_cashadvance_debit_account(pr, journal_id), # or journal_id.default_account_id.id,
                            'debit': pr.sub_total_amount if pr.sub_total_amount > 0 else pr.amount_total * pr.quantity_available, 
                            'code': pr.code,
                            'tax_ids': pr.tax_ids.ids,
                    }) for pr in self.product_ids] + [(0, 0, {
                                                            'name': 'Credit Entry',
                                                            'account_id': self.get_cashadvance_credit_account(journal_id).id,
                                                            'credit': sum([r.sub_total_amount for r in self.product_ids]),
                                                            'debit': 0.00,
                                                            })],
                })
            else:
                if inv.state == ['posted', 'post']:
                    '''check if the related invoice entry has been posted 
                    but record hasnt been set to the done or final stage'''
                    ms = self.memo_setting_id
                    if ms.stage_ids and self.stage_id.id != ms.stage_ids[-1].id:
                        self.update_final_state_and_approver(False, False, False)
            container = {'records': inv}
            inv._sync_dynamic_lines(container)
            self.move_id = inv.id

            return self.record_to_open(
            "account.move", 
            view_id,
            inv.id,
            f"Journal Entry - {inv.name}"
            )
        else:
            raise ValidationError("Sorry! You are not allowed to validate cash advance payments. \n To resolve, go to the memo config and select the current user in the Employees to followup field")
    
    ## SOE FEATURES
    @api.onchange('cash_advance_reference')
    def onchange_cash_advance_reference(self):
        car = self.sudo().cash_advance_reference
        if self.sudo().cash_advance_reference:
            if self.env.user.id != self.sudo().cash_advance_reference.employee_id.user_id.id:
                raise ValidationError("""You cannot retire cash advance not initiated by you.""")
            if car.product_ids and car.mapped('product_ids').filtered(lambda x: not x.retired) and self.state in ['submit']: 
                # NEWC checked the state to ensure no retired product is changed
                self.product_ids = False
                self.product_ids = [(0, 0, {
                        'memo_id': self.id,
                        'memo_type': self.memo_type.id,
                        'memo_type_key': self.memo_type.memo_key,
                        'product_id': rec.product_id and rec.product_id.id, 
                        'quantity_available': rec.quantity_available,
                        'description': rec.description,
                        'request_line_id': rec.id,
                        'used_qty': rec.used_qty,
                        'amount_total': rec.amount_total,
                        'used_amount': rec.sub_total_amount,
                        'note': rec.note,
                        'code': rec.code,
                        'to_retire': True if not rec.retired else False,
                    }) for rec in car.mapped('product_ids').filtered(lambda s: not s.retired)]
                _logger.info(
                    f"SOE will retire to: {car.processing_company_id.name or car.company_id.name}"
                )
            else:
                raise ValidationError('you have already retired all the items in the selected cash advance reference')
    
    def update_cash_advance_lines_as_retired(self, request_lineid):
        '''this is done so as not to populate it when next user wants to retire other items'''
        request_line = self.env['request.line'].search([
            ('memo_id', '=', self.cash_advance_reference.id),
            ('id', '=', request_lineid)
            ], limit=1)
        if request_line:
             request_line.sudo().update({'retired': True})
        else:
            raise ValidationError(f"Request line with id {request_lineid} cannot be found to retire")

    def soe_invoice_to_generate(self):
        items = self.mapped('product_ids').filtered(
            lambda lm: (lm.sub_total_amount - lm.used_amount) 
        )
        return items 
            
    def set_cash_advance_as_retired(self):
        if self.cash_advance_reference:
            # if self.cash_advance_reference.mapped('product_ids').filtered(
            #     lambda pr: pr.retired == False):
            #     self.cash_advance_reference.is_cash_advance_retired = False 
            # else:
            self.cash_advance_reference.is_cash_advance_retired = True
            for ch in self.cash_advance_reference.mapped('product_ids'):
                ch.retired = True
    
    def generate_soe_entries(self):
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
            """Check if the user is enlisted as the approver for memo type
            if approver is an account officer, system generates move and open the exact record"""
            
            if not self.sudo().cash_advance_reference:
                raise ValidationError("No cash advance reference found for retirement")
            
            original_advance = self.sudo().cash_advance_reference
            payment_company = original_advance.processing_company_id or \
                            original_advance.company_id
            _logger.info(
                f"  SOE Processing:\n"
                f"  SOE Request: {self.code}\n"
                f"  SOE Company: {self.company_id.name}\n"
                f"  Original Advance: {original_advance.code}\n"
                f"  Original Company: {original_advance.company_id.name}\n"
                f"  Payment Company: {payment_company.name}\n"
                f"  Retiring to: {payment_company.name}"
            )
            
            view_id = self.env.ref('account.view_move_form').id
            journal_id = self.env['account.journal'].sudo().search(
            [
                ('company_id', '=', payment_company.id),
                ('type', 'in', ['bank', 'general']),
                # ('type', '=', 'general'),
            #  ('code', '=', 'INV')
             ], limit=1)
            if not journal_id:
                raise UserError(f"No Bank / Miscellaneous journal configured for company: {payment_company.name} Contact admin to setup before proceeding")
            account_move = self.env['account.move'].sudo()
            inv = account_move.search([('memo_id', '=', self.id)], limit=1)
            if inv and inv.state == 'cancel':
                inv.unlink()
                inv = False
            cashadvance_account_to_credit =original_advance.move_id.line_ids[0].account_id.id if original_advance.move_id.line_ids and original_advance.move_id.line_ids[0].account_id else False
            if not inv:
                partner_id = self.sudo().vendor_id or self.sudo().client_id or self.sudo().employee_id.user_id.partner_id
                inv = account_move.create({ 
                    'memo_id': self.id,
                    'ref': self.code,
                    'origin': self.code,
                    'partner_id': partner_id.id,
                    'branch_id': original_advance.processing_branch_id.id or original_advance.branch_id.id,
                    'company_id': payment_company.id,
                    'currency_id': payment_company.currency_id.id,
                    # Do not set default name to account move name, because it
                    # is unique 
                    'name': f"{self.id}/{self.code}",
                    # 'move_type': 'out_receipt',
                    'move_type': 'entry',
                    'invoice_date': fields.Date.today(),
                    'date': fields.Date.today(),
                    'journal_id': journal_id.id,
                    'line_ids': [(0, 0, {
                            'name': pr.product_id.name if pr.product_id else pr.description,
                            'ref': f'{self.code}: {pr.product_id.name or pr.description}',
                            'account_id': self.get_soe_expense_account(pr, journal_id).id, # or journal_id.default_account_id.id,
                            'debit': pr.retire_sub_total_amount,
                            'code': pr.code,
                    }) for pr in self.product_ids] + [(0, 0, {
                                                            'name': 'Cash Advance to Debit',
                                                            'account_id': cashadvance_account_to_credit or self.get_soe_credit_account(journal_id).id, # account of the cash advance reference used, CASH PACM, to be on debit
                                                            'credit': sum([r.retire_sub_total_amount for r in self.product_ids]),
                                                            'debit': 0.00,
                                                            })],
                })
                if self.product_ids_with_qty_to_return():
                    self.to_update_inventory_product = True
            self.move_id = inv.id
            return self.open_related_record_view(
                'account.move', 
                inv.id if inv.id else self.move_id.id ,
                view_id,
                "Journal Entry - {self.code}"
            )
            # return self.record_to_open(
            # "account.move", 
            # view_id,
            # inv.id,
            # f"Journal Entry - {inv.name}"
            # )
        else:
            raise ValidationError("Sorry! You are not allowed to validate cash advance payments. \n To resolve, go to the memo config and select the current user in the Employees to followup field")
        
    # def generate_soe_entries(self):
    #     is_config_approver = self.determine_if_user_is_config_approver()
    #     if is_config_approver:
    #         """Check if the user is enlisted as the approver for memo type
    #         if approver is an account officer, system generates move and open the exact record"""
    #         view_id = self.env.ref('account.view_move_form').id
    #         journal_id = self.env['account.journal'].search(
    #         [('type', '=', 'sale'),
    #         #  ('code', '=', 'INV')
    #          ], limit=1)
    #         account_move = self.env['account.move'].sudo()
    #         inv = account_move.search([('memo_id', '=', self.id)], limit=1)
    #         if not inv:
    #             partner_id = self.employee_id.user_id.partner_id
    #             inv = account_move.create({ 
    #                 'memo_id': self.id,
    #                 'ref': self.code,
    #                 'origin': self.code,
    #                 'partner_id': partner_id.id,
    #                 'company_id': self.env.user.company_id.id,
    #                 'currency_id': self.env.user.company_id.currency_id.id,
    #                 # Do not set default name to account move name, because it
    #                 # is unique 
    #                 'name': f"{self.id}/{self.code}",
    #                 'move_type': 'out_receipt',
    #                 'invoice_date': fields.Date.today(),
    #                 'date': fields.Date.today(),
    #                 'journal_id': journal_id.id,
    #                 'invoice_line_ids': [(0, 0, {
    #                         'name': pr.product_id.name if pr.product_id else pr.description,
    #                         'ref': f'{self.code}: {pr.product_id.name or pr.description}',
    #                         'account_id': pr.product_id.property_account_expense_id.id or pr.product_id.categ_id.property_account_expense_categ_id.id if pr.product_id else journal_id.default_account_id.id,
    #                         'price_unit': pr.used_amount,
    #                         'quantity': pr.used_qty,
    #                         'discount': 0.0,
    #                         'code': pr.code,
    #                         'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
    #                         'product_id': pr.product_id.id if pr.product_id else None,
    #                 }) for pr in self.product_ids],
    #             })
    #             if self.product_ids_with_qty_to_return():
    #                 self.to_update_inventory_product = True
    #         self.move_id = inv.id
    #         return self.record_to_open(
    #         "account.move", 
    #         view_id,
    #         inv.id,
    #         f"Journal Entry - {inv.name}"
    #         )
    #     else:
    #         raise ValidationError("Sorry! You are not allowed to validate cash advance payments. \n To resolve, go to the memo config and select the current user in the Employees to followup field")
    
    # def generate_soe_entries(self):
    #     
    #     # self.follower_messages(body)
    #     is_config_approver = self.determine_if_user_is_config_approver()
    #     if is_config_approver:
    #         self.write({
    #             'state': 'Approve2'
    #         })
            
    #         """Check if the user is enlisted as the approver for memo type
    #         if approver is an account officer, system generates move and open the exact record"""
    #         view_id = self.env.ref('account.view_move_form').id
    #         journal_id = self.env['account.journal'].search(
    #         [('type', '=', 'sale'),
    #          ('code', '=', 'INV')
    #          ], limit=1)
    #         # 5000 - 3000
    #         account_move = self.env['account.move'].sudo()
    #         inv = account_move.search([('memo_id', '=', self.id)], limit=1)
    #         if not inv:
    #             partner_id = self.employee_id.user_id.partner_id
    #             inv = account_move.create({ 
    #                 'memo_id': self.id,
    #                 'ref': self.code,
    #                 'origin': self.code,
    #                 'partner_id': partner_id.id,
    #                 'company_id': self.env.user.company_id.id,
    #                 'currency_id': self.env.user.company_id.currency_id.id,
    #                 # Do not set default name to account move name, because it
    #                 # is unique 
    #                 'name': f"SOE {self.code}",
    #                 'move_type': 'out_receipt',
    #                 'invoice_date': fields.Date.today(),
    #                 'date': fields.Date.today(),
    #                 'journal_id': journal_id.id, 
    #             })
    #             if self.product_ids_with_qty_to_return():
    #                 self.to_update_inventory_product = True

    #             for pr in self.mapped('product_ids').filtered(lambda x: x.to_retire):
    #                 balance_remaining = pr.sub_total_amount - pr.used_amount # e.g 5000 - 3000 = 2000
    #                 if balance_remaining > 0:
    #                     inv.invoice_line_ids = [(0, 0, {
    #                         'name': f"{pr.product_id.name or ''}: {self.code}" or f"{pr.description}",
    #                         'ref': f'{self.code}: {pr.product_id.name}',
    #                         'account_id': pr.product_id.property_account_income_id.id or pr.product_id.categ_id.property_account_income_categ_id.id if pr.product_id else journal_id.default_account_id.id,
    #                         'price_unit': pr.sub_total_amount - pr.used_amount, # pr.used_total: ensure the retiring balance is 0 if it is lesser,
    #                         'quantity': 1, # pr.used_qty,
    #                         'discount': 0.0,
    #                         'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
    #                         'product_id': pr.product_id.id if pr.product_id else None,
    #                     })]# if pr.sub_total_amount - pr.used_amount > 0 else False]
    #                     pr.update({'retired': True, 'to_retire': False}) # updating the Line as retired
    #                     _logger.info(f'req line id {pr.request_line_id}')
    #                     self.update_cash_advance_lines_as_retired(pr.request_line_id) # no longer pr.code

    #         if inv.amount_total > 0:
    #             return self.record_to_open(
    #                 "account.move", 
    #                 view_id,
    #                 inv.id,
    #                 f"Journal Entry SOE - {inv.name}"
    #                 ) 
    #         else:
    #             '''Set the retired to true if there is not amount difference to retire'''
    #             for rec in self.mapped('product_ids').filtered(lambda x: x.to_retire):
    #                 rec.update({'retired': True, 'to_retire': False}) # updating the Line as retired
    #                 _logger.info(f'req line id 2 {rec.request_line_id}')
    #                 self.update_cash_advance_lines_as_retired(rec.request_line_id)
    #             self.sudo().cash_advance_reference.soe_advance_reference = self.id
    #             self.is_request_completed = True
    #             self.sudo().update_final_state_and_approver()
    #             self.update_status_badge()
    #         self.set_cash_advance_as_retired()
         
    def record_to_open(self, model, view_id, res_id=False, name=False):
        obj = self.env[f'{model}'].sudo().search(['|','|', 
                                           ('origin', '=', self.code), 
                                           ('id', '=', self.move_id.id), 
                                           ('memo_id', '=', self.id)], limit=1)
        if obj:
            return self.open_related_record_view(
                model, 
                res_id if res_id else obj.id ,
                view_id,
                name if name else f"{obj.name}"
            )
        else:
            raise ValidationError("No related record found for the memo")

    to_update_inventory_product = fields.Boolean('Update Inventory product')
    def compute_used_quantity(self, req_qty, usedqty):
        amount_to_return = 0
        if usedqty < req_qty:
            amount_to_return = req_qty - usedqty
        return amount_to_return 
    
    def product_ids_with_qty_to_return(self): 
        product_ids_with_qty_to_return = self.mapped('product_ids').filtered(
                    lambda pr: pr.product_id and pr.product_id.detailed_type == "product" \
                        and pr.retired == True and self.compute_used_quantity(pr.quantity_available, pr.used_qty) > 0)
        return product_ids_with_qty_to_return
             
    def update_inventory_product_quantity(self):
        '''this will be used to raise a stock tranfer record. Once someone claimed he returned a 
         positive product (storable product) , 
         system should generate a stock picking to update the new product stock
         if product does not exist, To be asked for '''
        stock_picking_type_out = self.picking_type_id # self.env.ref('stock.picking_type_out')
        # stock_picking_type_out = self.env.ref('stock.picking_type_out')
        stock_picking = self.env['stock.picking']
        user = self.env.user
        warehouse_location_id = self.env['stock.warehouse'].sudo().search([
            ('company_id', '=', user.company_id.id) 
        ], limit=1)
        partner_location = self.env['stock.location'].sudo().search([
            ('company_id', '=', user.company_id.id),
            ('usage', '=', 'customer') 
        ], limit=1)
        if not partner_location:
            raise ValidationError(f"Contact system admin to set up customer location for the company: {user.company_id.name}")
        if not warehouse_location_id:
            raise ValidationError(f"Contact system admin to set up warehouse for the company: {user.company_id.name}")
        partner_location_id = partner_location.id or self.env.ref('stock.stock_location_customers')
        stock = self.env['stock.picking'].sudo().search(['|',('memo_id', '=', self.id), ('origin', '=', self.code)], limit=1)
        view_id = self.env.ref('stock.view_picking_form').id
        if not stock:
            '''Ensure request line items has positive products to return before generate stock move to inventory moves'''
            if self.product_ids_with_qty_to_return():
                vals = {
                    'scheduled_date': fields.Date.today(),
                    'picking_type_id': stock_picking_type_out.id,
                    'origin': self.code,
                    'partner_id': self.sudo().employee_id.user_id.partner_id.id,
                    'move_ids_without_package': [(0, 0, {
                                    'name': self.code, 
                                    'picking_type_id': stock_picking_type_out.id,
                                    'location_id': partner_location_id.id,
                                    'location_dest_id': mm.source_location_id.id or warehouse_location_id.lot_stock_id.id,
                                    'product_id': mm.product_id.id,
                                    'product_uom_qty': self.compute_used_quantity(mm.quantity_available, mm.used_qty),
                                    'date_deadline': self.date_deadline,
                    }) for mm in self.product_ids_with_qty_to_return()]
                }
                stock_picking.sudo().create(vals)
        return self.record_to_open(
                "stock.picking", 
                view_id,
                stock.id,
                f"Stock move for SOE {self.code} - {stock.name}"
                )
        
    def open_related_record_view(self, model, res_id, view_id, name="Record To approved", view_mode="form", domain=[]):
        ret = {
                'name': name,
                'view_mode': view_mode,
                'view_id': view_id,
                'view_type': view_mode,
                'res_model': model,
                'res_id': res_id,
                'type': 'ir.actions.act_window',
                'domain': domain,
                'target': 'current'
                }
        return ret

    def update_memo_type_approver(self):
        """update memo type approver"""
        memo_settings = self.memo_setting_id if not self.to_create_document else self.document_memo_config_id
        # or self.env['memo.config'].sudo().search([
        #         ('memo_type', '=', self.memo_type.id),
        #         ('department_id', '=', self.employee_id.department_id.id)
        #         ]) if not self.to_create_document else self.document_memo_config_id
        
        memo_approver_ids = memo_settings.approver_ids
        for appr in memo_approver_ids:
            self.sudo().write({
                'users_followers': [(4, appr.id)] 
            })
      
    def view_related_record(self):
        if self.env.uid not in [r.user_id.id for r in self.users_followers]:
            raise ValidationError("You are not responsible to view this")
        if self.memo_type.memo_key == "material_request":
            view_id = self.sudo().env.ref('stock.view_picking_form').id
            return self.record_to_open('stock.picking', view_id)
        
        if self.memo_type.memo_key in ["payment_request", "Payment"]:
            view_id = self.sudo().env.ref('account.view_move_form').id
            return self.record_to_open('account.move', view_id)
             
        elif self.memo_type.memo_key == "procurement_request":
            tree_view = self.env.ref('purchase.purchase_order_tree').id
            form_view = self.env.ref('purchase.purchase_order_form').id
            ret = {
                    'name': 'Procurement',
                    'view_mode': 'tree,form',
                    # 'view_id': view_id,
                    'view_type': 'tree',
                    'res_model': 'purchase.order',
                    'views': [(tree_view, 'tree'), (form_view, 'form')],
                    # 'res_id': res_id,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', [rec.id for rec in self.po_ids])],
                    'target': 'current'
                    }
            return ret
            # return self.record_to_open('purchase.order', view_id)
        elif self.memo_type.memo_key == "vehicle_request":
            pass 
        elif self.memo_type.memo_key == "leave_request":
            view_id = self.env.ref('hr_holidays.hr_leave_view_form').id
            return self.record_to_open('hr.leave', view_id)
        elif self.memo_type.memo_key in ["cash_advance", "soe"]:
            view_id = self.env.ref('account.view_move_form').id
            return self.record_to_open('account.move', view_id)
        else:
            pass

    def follower_messages(self, body):
        pass 
        # body= "RETURN NOTIFICATION;\n %s" %(self.reason_back)
        # body = body
        # records = self._get_followers()
        # followers = records
        # self.message_post(body=body)
        # self.message_post(body=body, 
        # subtype='mt_comment',message_type='notification',partner_ids=followers)
    
    def validate_account_invoices(self):
        if not self.invoice_ids:
            raise ValidationError("Please ensure the invoice lines are added")

        invalid_record = self.mapped('invoice_ids').filtered(lambda s: not s.partner_id or not s.journal_id) # 
        if invalid_record:
            raise ValidationError("Partner, Payment journal must be selected. Also ensure the status is in draft")
        
    def create_contact(self, **kwargs):
        if kwargs.get('name') and kwargs.get('email'):
            partner = self.env['res.partner'].sudo().search([('email', '=', kwargs.get('email'))], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': kwargs.get('name'),
                    'email': kwargs.get('email'),
                    'phone': kwargs.get('phone'),
                    'active': True,
                })
            return partner.id
        else:
            return None
        
    def action_post_and_vallidate_payment(self): # Register Payment
        self.validate_account_invoices()
        outbound_payment_method = self.env['account.payment.method'].sudo().search(
                [('code', '=', 'manual'), ('payment_type', '=', 'outbound')], limit=1)
        for count, rec in enumerate(self.invoice_ids, 1):
            if not rec.invoice_line_ids:
                raise ValidationError(
                    f'Invoice at line {count} does not have move lines'
                    )   
            else:
                if rec.payment_state == 'not_paid': 
                    if rec.state == 'draft':
                        rec.action_post()
        payment_method = 2
        journal_id = rec.journal_id # payment_journal_id
        if journal_id:
            payment_method = journal_id.outbound_payment_method_line_ids[0].id if \
                journal_id.outbound_payment_method_line_ids else outbound_payment_method.id \
                    if outbound_payment_method else payment_method
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=self.invoice_ids.ids).create({
                'group_payment': False,
                'payment_method_line_id': payment_method,
            })._create_payments()
        self.finalize_payment()

    def finalize_payment(self):
        if self.invoice_ids:
            allpaid_invoice = self.mapped('invoice_ids').filtered(lambda s: s.payment_state in ['paid', 'in_payment'])
            if allpaid_invoice:
                self.state = "Done"
        else:
            self.state = "Done"
 
    def get_payment_method_line_id(self, payment_type, journal_id):
            if journal_id:
                available_payment_method_lines = journal_id._get_available_payment_method_lines(payment_type)
            else:
                available_payment_method_lines = False
            # Select the first available one by default.
            if available_payment_method_lines:
                payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                payment_method_line_id = False
            return payment_method_line_id
            
    def validate_invoice_and_post_journal(
            self, journal_id, inv): 
            """To be used only when they request for automatic payment generation"""
            account_payment = self.env['account.payment'].sudo()
            outbound_payment_method = self.env['account.payment.method'].sudo().search(
                [('code', '=', 'manual'), ('payment_type', '=', 'outbound')], limit=1)
            payment_method = 2
            if journal_id:
                payment_method = journal_id.outbound_payment_method_line_ids[0].id if \
                    journal_id.outbound_payment_method_line_ids else outbound_payment_method.id \
                        if outbound_payment_method else payment_method
            payment_method_line_id = self.get_payment_method_line_id('outbound', journal_id)
            payment_vals = {
                'date': fields.Date.today(),
                'amount': inv.amount_total,
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'ref': inv.name,
                'move_id': inv.id,
                'journal_id': 8, #inv.payment_journal_id.id,
                'currency_id': inv.currency_id.id,
                'partner_id': inv.partner_id.id,
                'destination_account_id': inv.line_ids[1].account_id.id,
                'payment_method_line_id': payment_method, #payment_method_line_id.id if payment_method_line_id else payment_method,
            }
            payments = self.env['account.payment'].create(payment_vals)
            payments.action_post()

    def Register_Payment(self):
        if self.env.uid in [r.user_id.id for r in self.sudo().stage_id.approver_ids]:
            raise ValidationError(
                """You are not Permitted to approve this Memo. Contact the authorized Person
            """)
        view_id = self.env.ref('account.view_account_payment_form')
        if (self.memo_type.memo_key != "Payment"): # or (self.amountfig < 1):
            raise ValidationError("(1) Request type must be 'Payment'\n (2) Amount must be greater than one to proceed with payment")
        
        payment_company = self.processing_company_id or self.company_id
        account_payment_existing = self.env['account.payment'].search([
            ('memo_reference', '=', self.id)
            ], limit=1)
        computed_amount_total = sum([rec.amount_total for rec in self.product_ids]) if self.product_ids else 0
        vals = {
                'name':'Request Payment',
                'view_mode': 'form',
                'view_id': view_id.id,
                'view_type': 'form',
                'res_model': 'account.payment',
                'type': 'ir.actions.act_window',
                'target': 'current'
                }
        if not account_payment_existing:
            vals.update({
                'context': {
                        'default_amount': self.amountfig or computed_amount_total,
                        'default_payment_type': 'outbound',
                        'default_partner_id':self.vendor_id.id or self.client_id.id or self.sudo().employee_id.user_id.partner_id.id, 
                        'default_memo_reference': self.id,
                        'default_communication': self.name,
                        'default_currency_id': payment_company.currency_id.id or self.env.user.company_id.currency_id.id,
                        'default_company_id': payment_company.id,
                },
                'domain': [],
            })
        else:
            vals.update({
                'res_id': account_payment_existing.id
            })
        return vals

    def generate_loan_entries(self):
        if self.loan_reference:
            raise ValidationError("You have generated a loan already for this record")
        view_id = self.env.ref('account_loan.account_loan_form')
        if (self.memo_type.memo_key != "loan") or (self.loan_amount < 1):
            raise ValidationError("Check validation: \n (1) Memo type must be 'loan request'\n (2) Loan Amount must be greater than one to proceed with loan request")
        ret = {
            'name':'Generate loan request',
            'view_mode': 'form',
            'view_id': view_id.id,
            'view_type': 'form',
            'res_model': 'account.loan',
            'type': 'ir.actions.act_window',
            'domain': [],
            'context': {
                    'default_loan_type': self.loan_type,
                    'default_loan_amount': self.loan_amount,
                    'default_periods':self.periods or 12,  
                    'default_partner_id':self.employee_id.user_id.partner_id.id,  
                    'default_method_period':self.method_period,  
                    'default_rate': 15, 
                    'default_start_date':self.start_date, 
                    'default_name': self.code,
            },
            'target': 'current'
            }
        return ret

    def migrate_records(self):
        account_ref = self.env['account.payment'].sudo().search([])
        for rec in account_ref:
            memo_rec = self.env['memo.model'].search([('code', '=', rec.communication)])
            if memo_rec:
                memo_rec.state = "Done"

    """line 4 - 7 checks if the current user is the initiator of the memo, 
    if true, raises warning error else: it opens the wizard"""
        
    def return_validator(self):
        if self.env.user.id not in [r.user_id.id for r in self.sudo().stage_id.approver_ids]:
            raise ValidationError(
                """Sorry you are not allowed to reject /  return you own initiated memo"""
                )
        
    def return_memo(self):
        self.return_validator()
        default_sender = self.mapped('res_users')
        last_sender = self.env['hr.employee'].sudo().search([
            ('user_id', '=', default_sender[-1].id)]).id if default_sender else False
        return {
              'name': 'Reason for Return',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'memo.back',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_memo_record': self.id,
                  'default_date': self.date,
                  'default_direct_employee_id': last_sender,
                  'default_resp':self.env.uid,
              },
        }
    
    @api.depends('state')
    # Depending on any field change (ORM or Form), the function is triggered.
    def _progress_state(self):
        for order in self:
            if order.state in ["submit", "Refuse"]:
                order.status_progress = random.randint(0, 5)
            elif order.state == "Sent":
                order.status_progress = random.randint(20, 60)
            elif order.state == "Approve":
                order.status_progress = random.randint(71, 95)
            elif order.state == "Approve2":
                order.status_progress = random.randint(71, 98)
            elif order.state == "Done":
                order.status_progress = 100
            else:
                order.status_progress = random.randint(0, 1) # 100 / len(order.state)
    expiry_mail_sent = fields.Boolean(default=False, copy=False)

    @api.model
    def _cron_notify_server_request_followers(self):
        """
        System should check all requests end date expired, and send message
        to server admin or followers. 
        """
        expired_memos = self.env['memo.model'].sudo().search([
            ('request_end_date', '<', fields.Datetime.now()),
            ('expiry_mail_sent', '=', False),
            ('memo_type', '=', 'server_access'),
            ])
        for exp in expired_memos:
            if exp.memo_setting_id and exp.memo_setting_id.approver_ids:
                body_msg = f"""Dear Sir, \n \
                    <br/>I wish to notify you that a server access request with description, {exp.name},<br/>  
                    from {exp.employee_id.name} \
                    has now expired. <br/> <br/>Go to the request {self.get_url(exp.id)} \
                """
                exp.mail_sending_direct(body_msg)
                exp.expiry_mail_sent = True

    def unlink(self):
        for delete in self.filtered(lambda delete: delete.active == True and delete.state in ['Sent','Approve2', 'Approve']):
            raise ValidationError(_('You cannot delete a Memo which is in %s state.') % (delete.state,))
        return super(Memo_Model, self).unlink()
    
    @api.model
    def retrieve_dashboard(self):
        """ This function returns the values to populate the custom dashboard in
            the purchase order views.
        """
        result = {
            'all_to_send': 0,
            'all_waiting': 0,
            'all_late': 0,
            'my_to_send': 0,
            'my_waiting': 0,
            'my_late': 0,
            'all_avg_order_value': 0,
            'all_avg_days_to_purchase': 0,
            'all_total_last_7_days': 0,
            'all_sent_rfqs': 0,
        } 
        # easy counts
        mo = self.env['memo.model'].sudo()
        result['all_to_send'] = mo.search_count([('state', '=', 'draft')])
        result['my_to_send'] = mo.search_count([('state', '=', 'done')])
        return result
    
    def write(self, vals):
        old_length = len(self.users_followers)
        res = super(Memo_Model, self).write(vals)
        if 'users_followers' in vals and self.create_uid.id != self.env.uid:
            if len(self.users_followers) < old_length:
                raise ValidationError("Sorry you cannot remove followers")
        return res
    
    
class MemoActionHistory(models.Model):
    _name = 'memo.action.history'
    _description = 'Memo Action History'
    _order = 'action_date desc'
    
    memo_id = fields.Many2one('memo.model', required=True, ondelete='cascade', index=True)
    stage_id = fields.Many2one('memo.stage', string='Stage', required=True)
    actor_id = fields.Many2one('hr.employee', string='Actor', required=True)
    user_id = fields.Many2one('res.users', related='actor_id.user_id', store=True, index=True)
    action_date = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    action = fields.Selection([
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ], required=True, index=True)
    comments = fields.Text()
    next_stage_id = fields.Many2one('memo.stage', string='Moved To Stage')
    
    def name_get(self):
        result = []
        for rec in self:
            action_label = dict(self._fields['action'].selection).get(rec.action)
            name = f"{action_label} by {rec.actor_id.name} on {rec.action_date.strftime('%Y-%m-%d %H:%M')}"
            result.append((rec.id, name))
        return result
    
