from odoo import models, fields, api
from odoo import Command
from odoo.exceptions import ValidationError

class MemoConfigDuplicationWizard(models.TransientModel):
    _name = 'memo.config.duplication.wizard'

    name = fields.Char(string="Request Name")
    dept_ids = fields.Many2many('hr.department', string="Departments")
    dummy_memo_stage_ids = fields.Many2many('dummy.memo.stage', 'duplication_wizard_id')
    employees_follow_up_ids = fields.Many2many('hr.employee',
                                               'hr_employee_wizard_rel',
                                                'approvers_id',
                                                'config_wizard_id',
                                                string='Employees to Follow up')
    allowed_companies_ids = fields.Many2many('res.partner',
                                         'res_partner_wizard_rel'
                                         'allowed_companies_id',
                                         'res_partner_wizard_id', 
                                         string='Allowed Partners')
    
    company_ids = fields.Many2many(
        'res.company', 
        'res_confi_duplication_config_rel',
        'company_id',
        'memo_config_setting_id',
        string="For companies",
        help="""When you select a company, the system will 
        generate the configuration for each company set"""
        )
    send_to_initiator_on_refusal = fields.Boolean(string="Send to initiator",
                                      default=False, 
                                      help="Check if you want system to send straight to initiator upon refusal")
    allow_multi_vending_on_po = fields.Boolean(
        string="Allow Multi Vending", 
        default=True, 
        help="This only allow users to send PO request to multiple vendors")
    branch_ids = fields.Many2many(
        'multi.branch', 
        string='Districts / Branch(s)', 
        required=False)
    
    prefix_code = fields.Char(
        string='Prefix Code')
    
    receivable_account_id = fields.Many2one(
        "account.account", 
        string="Account Receivable"
        ) 
    payable_account_id = fields.Many2one(
        "account.account", 
        string="Account Payable"
        ) 
    advance_account_id = fields.Many2one(
        "account.account", 
        string="Advance Account"
        ) 
    expense_account_id = fields.Many2one(
        "account.account", 
        string="Expense Account"
        )

    @api.model
    def default_get(self, fields):
        res = super(MemoConfigDuplicationWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        if active_id:
            memo_config = self.env['memo.config'].browse(active_id)
            dummy_memo_stage_ids = []
            for stage in memo_config.stage_ids:
                dummy_memo_stage = self.env['dummy.memo.stage'].create({
                    'name': stage.name,
                    'sequence': stage.sequence,
                    'active': stage.active,
                    'approver_ids': stage.approver_ids,
                    'is_approved_stage': stage.is_approved_stage,
                    'main_stage_id': stage.id,
                    # 'require_waybill_detail': stage.require_waybill_detail,
                    # 'require_po_confirmation': stage.require_po_confirmation,
                    # 'require_so_confirmation': stage.require_so_confirmation,
                    # 'require_bill_payment': stage.require_bill_payment,
                    # 'require_waybill_detail': stage.require_waybill_detail,
                    # 'publish_on_dashboard': stage.publish_on_dashboard,
                })
                dummy_memo_stage_ids.append(dummy_memo_stage.id)
            res.update({
                'dummy_memo_stage_ids': [(6, 0, dummy_memo_stage_ids)], 
                'send_to_initiator_on_refusal': memo_config.send_to_initiator_on_refusal,
                'allow_multi_vending_on_po': memo_config.allow_multi_vending_on_po,
                'expense_account_id': memo_config.expense_account_id.id,
                'advance_account_id': memo_config.advance_account_id.id,
                'payable_account_id': memo_config.payable_account_id.id,
                'prefix_code': memo_config.prefix_code
                })
        return res

    def duplicate_memo_config(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            memo_config = self.env['memo.config'].browse(active_id)
            for comp in self.company_ids:
                company_districts = self.mapped('branch_ids').filtered(lambda co: co.company_id.id == comp.id)
                for cob in company_districts:
                    config_exist = self.env['memo.config'].search([
                        ('branch_id', '=', cob.id), 
                        ('company_id', '=', comp.id),
                        ('name', '=', memo_config.name),
                        ('memo_type', '=', memo_config.memo_type.id)], limit=1)
                    if config_exist:
                        raise ValidationError(f'Configuration for type {memo_config.memo_type.name} exist in company - {comp.name} and department {cob.name}')
                    stage_ids = []
                    new_config = self.env['memo.config'].create({
                    'name': f"{self.name} {memo_config.memo_type.name} - [{cob.name}]",
                    'branch_id': cob.id,
                    'memo_type': memo_config.memo_type.id,
                    'approver_ids': [(6, 0, self.employees_follow_up_ids.ids)],
                    'allowed_for_company_ids': self.allowed_companies_ids,
                    'company_id': comp.id,
                    'company_ids': [(4, comp.id)],
                    'prefix_code': self.prefix_code,
                    'expense_account_id': self.expense_account_id.id,
                    'advance_account_id': self.advance_account_id.id,
                    'payable_account_id': self.payable_account_id.id,
                    'allow_multi_vending_on_po': self.allow_multi_vending_on_po,
                    'send_to_initiator_on_refusal': self.send_to_initiator_on_refusal,
                    'receivable_account_id': self.receivable_account_id.id,
                    })
                    if self.dummy_memo_stage_ids:
                        for sequence, stage in enumerate(self.dummy_memo_stage_ids, 2000): 
                            # original_stage_obj = self.env['memo.stage'].browse(stage.main_stage_id)
                            new_stage = self.env['memo.stage'].create({
                                'name': stage.name,
                                'sequence': sequence,
                                'active': True,
                                'loaded_from_data': True,
                                'approver_ids': [(6, 0, stage.approver_ids.ids)],
                                'is_approved_stage': stage.is_approved_stage,
                                'memo_config_id': new_config.id,
                                # new implementation for stage duplication
                                'sub_stage_ids': [(4, stg.copy().id) for stg in stage.main_stage_id.sub_stage_ids],
                                'required_invoice_line': [(4, rinv.copy().id) for rinv in stage.main_stage_id.required_invoice_line],
                                'required_document_line': [(4, rdoc.copy().id) for rdoc in stage.main_stage_id.required_document_line],
                                'no_conditional_stage_id': stage.main_stage_id.no_conditional_stage_id.id,
                                'yes_conditional_stage_id': stage.main_stage_id.yes_conditional_stage_id.id,
                                'memo_has_condition': stage.main_stage_id.memo_has_condition,
                                'require_waybill_detail': stage.main_stage_id.require_waybill_detail,
                                'require_po_confirmation': stage.main_stage_id.require_po_confirmation,
                                'require_so_confirmation': stage.main_stage_id.require_so_confirmation,
                                'require_bill_payment': stage.main_stage_id.require_bill_payment,
                                'publish_on_dashboard': stage.main_stage_id.publish_on_dashboard,
                                'company_id': comp.id,
                            })
                            stage_ids.append(new_stage.id)
                        new_config.update({'stage_ids': [(6, 0, stage_ids)]})

class DummyMemoStage(models.TransientModel):
    _name = 'dummy.memo.stage'

    duplication_wizard_id = fields.Many2one('memo.config.duplication.wizard', string='Duplication Wizard')
    name = fields.Char(string="Stage Name")
    sequence = fields.Integer(string="Sequence")
    active = fields.Boolean(string="Active")
    approver_ids = fields.Many2many('hr.employee', 'employee_wizard_rel', 'employee_id', 'employee_wizard_id', string="Approvers")
    is_approved_stage = fields.Boolean(string="Is Approved Stage")
    main_stage_id = fields.Many2one('memo.stage', string="Main Stage")

