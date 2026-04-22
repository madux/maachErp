from odoo import models, fields, api,_, SUPERUSER_ID
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class MemoConfig(models.Model):
    _inherit = 'memo.config'
    
    def action_sync_approvers(self):
        """
        Synchronize all approvers for the selected memo configurations.
        This will trigger a full resync of all users who have roles mentioned
        in the approval_role_ids of the stages belonging to these configs.
        """
        config_ids = self.env.context.get('active_ids', [])
        configs = self.browse(config_ids)
        
        stages = self.env['memo.stage'].search([('memo_config_id', 'in', configs.ids)])
        
        roles = stages.mapped('approval_role_ids')
        
        if not roles:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No approval roles found in the selected configurations.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        users = roles.mapped('user_ids').filtered(lambda u: u.id != SUPERUSER_ID)
        
        if not users:
            _logger.info("action_sync_approvers: no users found with approval roles for configs %s", configs.mapped('name'))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No users assigned to the approval roles in these configurations.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        _logger.info("action_sync_approvers: syncing %d users for %d configs", len(users), len(configs))
        
        for user in users:
            try:
                user.sudo()._sync_approvals_from_roles()
                _logger.info("action_sync_approvers: synced user %s (id=%s)", user.login, user.id)
            except Exception:
                _logger.exception("action_sync_approvers: failed to sync user %s (id=%s)", user.login, user.id)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Approvers synchronized successfully for %d user(s).') % len(users),
                'type': 'success',
                'sticky': False,
            }
        }
    

class MemoStageInherit(models.Model):
    _inherit = 'memo.stage'

    approval_role_ids = fields.Many2many(
        "user.role",
        string="Approval Roles",
        help="Users having any of these roles can approve this stage."
    )
    
    

# class MemoSubStageLineInherit(models.Model):
#     _inherit = 'memo.sub.stage'

#     def responsible_approver_right(self):
#         user = self.env.user

#         direct_employee_approvers = self.approver_ids | \
#                                     self.sub_stage_id.approver_ids | \
#                                     self.sub_stage_id.memo_config_id.approver_ids
        
#         allowed_user_ids = set(direct_employee_approvers.mapped('user_id.id'))

#         required_roles = self.sub_stage_id.approval_role_ids
        
#         if required_roles:
#             role_based_users = self.env['res.users'].search([('role_ids', 'in', required_roles.ids)])
#             allowed_user_ids.update(role_based_users.ids)

#         if user.id not in allowed_user_ids:
#             raise ValidationError("You do not have the required role or are not a designated approver for this stage.")
        
#         return True



class MemoConfigDuplicationWizardInherit(models.TransientModel):
    _inherit = 'memo.config.duplication.wizard'

    @api.model
    def default_get(self, fields_list):
        """
        Extend default_get to populate approval_role_ids for dummy stages.
        """
        res = super(MemoConfigDuplicationWizardInherit, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if not active_id:
            return res

        memo_config = self.env['memo.config'].browse(active_id)
        if not memo_config.exists():
            return res

        dummy_stage_ids = []
        for stage in memo_config.stage_ids:
            dummy_stage = self.env['dummy.memo.stage'].create({
                'name': stage.name,
                'sequence': stage.sequence,
                'active': stage.active,
                'approver_ids': [(6, 0, stage.approver_ids.ids)],
                'approval_role_ids': [(6, 0, stage.approval_role_ids.ids)] if stage.approval_role_ids else False,
                'is_approved_stage': stage.is_approved_stage,
                'main_stage_id': stage.id,
            })
            dummy_stage_ids.append(dummy_stage.id)
        
        res.update({
            'dummy_memo_stage_ids': [(6, 0, dummy_stage_ids)],
            'send_to_initiator_on_refusal': memo_config.send_to_initiator_on_refusal,
            'allow_multi_vending_on_po': memo_config.allow_multi_vending_on_po,
            'expense_account_id': memo_config.expense_account_id.id if memo_config.expense_account_id else False,
            'advance_account_id': memo_config.advance_account_id.id if memo_config.advance_account_id else False,
            'payable_account_id': memo_config.payable_account_id.id if memo_config.payable_account_id else False,
        })
        
        return res
    
    def duplicate_memo_config(self):
        """
        Override to include approval_role_ids when creating new stages.
        """
        active_id = self.env.context.get('active_id')
        if not active_id:
            return
            
        memo_config = self.env['memo.config'].browse(active_id)
        
        for comp in self.company_ids:
            company_districts = self.mapped('branch_ids').filtered(lambda co: co.company_id.id == comp.id)
            for cob in company_districts:
                config_exist = self.env['memo.config'].search([
                    ('branch_id', '=', cob.id), 
                    ('company_id', '=', comp.id),
                    ('name', '=', f"{self.name} {memo_config.memo_type.name} - [{cob.name}]"),
                    ('memo_type', '=', memo_config.memo_type.id)
                ], limit=1)
                
                if config_exist:
                    raise ValidationError(
                        f'Configuration for type {memo_config.memo_type.name} exists in '
                        f'company - {comp.name} and branch {cob.name}'
                    )
                
                stage_ids = []
                new_config = self.env['memo.config'].create({
                    'name': self.name.strip() if self.name and self.name.strip() else f"{memo_config.memo_type.name} - [{cob.name}]",
                    'branch_id': cob.id,
                    'memo_type': memo_config.memo_type.id,
                    'approver_ids': [(6, 0, self.employees_follow_up_ids.ids)],
                    'allowed_for_company_ids': [(6, 0, self.allowed_companies_ids.ids)],
                    'company_id': comp.id,
                    'company_ids': [(4, comp.id)],
                    'prefix_code': self.prefix_code,
                    'expense_account_id': self.expense_account_id.id if self.expense_account_id else False,
                    'advance_account_id': self.advance_account_id.id if self.advance_account_id else False,
                    'payable_account_id': self.payable_account_id.id if self.payable_account_id else False,
                    'allow_multi_vending_on_po': self.allow_multi_vending_on_po,
                    'send_to_initiator_on_refusal': self.send_to_initiator_on_refusal,
                    'receivable_account_id': self.receivable_account_id.id if self.receivable_account_id else False,
                })
                
                if self.dummy_memo_stage_ids:
                    for sequence, stage in enumerate(self.dummy_memo_stage_ids, 2000):
                        new_stage = self.env['memo.stage'].create({
                            'name': stage.name,
                            'sequence': sequence,
                            'active': True,
                            'loaded_from_data': True,
                            'approver_ids': [(6, 0, stage.approver_ids.ids)],
                            'approval_role_ids': [(6, 0, stage.approval_role_ids.ids)] if stage.approval_role_ids else False,
                            'is_approved_stage': stage.is_approved_stage,
                            'memo_config_id': new_config.id,
                            'sub_stage_ids': [(4, stg.copy().id) for stg in stage.main_stage_id.sub_stage_ids],
                            'required_invoice_line': [(4, rinv.copy().id) for rinv in stage.main_stage_id.required_invoice_line],
                            'required_document_line': [(4, rdoc.copy().id) for rdoc in stage.main_stage_id.required_document_line],
                            'no_conditional_stage_id': stage.main_stage_id.no_conditional_stage_id.id if stage.main_stage_id.no_conditional_stage_id else False,
                            'yes_conditional_stage_id': stage.main_stage_id.yes_conditional_stage_id.id if stage.main_stage_id.yes_conditional_stage_id else False,
                            'memo_has_condition': stage.main_stage_id.memo_has_condition,
                            'require_waybill_detail': stage.main_stage_id.require_waybill_detail,
                            'require_po_confirmation': stage.main_stage_id.require_po_confirmation,
                            'require_so_confirmation': stage.main_stage_id.require_so_confirmation,
                            'require_bill_payment': stage.main_stage_id.require_bill_payment,
                            'publish_on_dashboard': stage.main_stage_id.publish_on_dashboard,
                            'company_id': comp.id,
                        })
                        stage_ids.append(new_stage.id)
                    
                    new_config.write({'stage_ids': [(6, 0, stage_ids)]})


class DummyMemoStageInherit(models.TransientModel):
    _inherit = 'dummy.memo.stage'

    approval_role_ids = fields.Many2many(
        'user.role',
        'dummy_memo_stage_role_rel',
        'dummy_stage_id',
        'role_id',
        string='Approval Roles',
        help="Roles that can approve this stage"
    )