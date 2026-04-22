from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class UserRole(models.Model):
    _name = 'user.role'
    _description = 'User Role'
    _order = 'name'

    name = fields.Char(string='Role Name', required=True, index=True)
    description = fields.Text(string='Description', copy=False)
    
    group_ids = fields.Many2many(
        'res.groups', 
        'user_role_groups_rel', 
        'role_id', 
        'group_id',
        string='Security Groups',
        copy=True,
        help="These are the Odoo security groups this role will grant to users."
    )
    
    company_ids = fields.Many2many(
        'res.company', 
        'user_role_company_rel', 
        'role_id', 
        'company_id',
        string='Allowed Companies',
        copy=True,
        help="Users with this role will be approvers for memo stages in these companies only. Leave empty for all companies."
    )
    
    branch_ids = fields.Many2many(
        'multi.branch',
        'user_role_branch_rel',
        'role_id',
        'branch_id',
        string='Allowed Districts',
        copy=True,
        help="Users with this role will be approvers for memo stages in these branches only. Leave empty for all branches."
    )
    
    is_request_approver = fields.Boolean(
        string='Is Request Approver?',
        copy=True,
        help="Check this if this role designates the user as an approver in the ERP Request module."
    )
    
    user_ids = fields.Many2many(
        'res.users', 
        'user_role_users_rel', 
        'role_id', 
        'user_id',
        copy=True,
        string='Users with this Role'
    )
    
    users_count = fields.Integer(
        compute='_compute_users_count',
        string="Users Count",
        store=True
    )
    limit_to_user_context = fields.Boolean(
        string='Limit to User Context',
        copy=True,
        help="If checked, the user will only be assigned as an approver in their specific company and/or branch, ignoring the role's allowed companies/districts."
    )
    
    limit_to_role_context = fields.Boolean(
        string='Limit to Role Context',
        copy=True,
        help="If checked, the user will only be assigned as an approver in the role's allowed companies/districts. User's own companies/district will be ignored."
    )
    
    color = fields.Integer(string='Color Index', default=0,
                           help="Integer index used by many2many_tags to color the tag.")
    
    active = fields.Boolean(default=True)

    @api.depends('user_ids')
    def _compute_users_count(self):
        for role in self:
            role.users_count = len(role.user_ids)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Role name must be unique!')
    ]
    
    @api.constrains('limit_to_user_context', 'limit_to_role_context')
    def _check_context_limits(self):
        for role in self:
            if role.limit_to_user_context and role.limit_to_role_context:
                raise ValidationError(_('A role cannot have both "Limit to User Context" and "Limit to Role Context" enabled.'))
    
    def action_view_users(self):
        """Smart button action to view users with this role."""
        self.ensure_one()
        return {
            'name': _('Users with the "%s" Role') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.user_ids.ids)],
            'context': {'create': False}
        }
        
    def action_sync_role_users(self):
        role_ids = self.env.context.get('active_ids', [])
        roles = self.browse(role_ids)
        for role in roles:
            users = role.user_ids.filtered(lambda u: u.id != SUPERUSER_ID)
            if not users:
                _logger.info("action_sync_role_users: role %s has no assigned users", self.name)
                return {'warning': _('No users assigned to this role.')}
            _logger.info("action_sync_role_users: syncing %d users for role %s", len(users), self.name)
            for user in users:
                try:
                    user.sudo()._sync_permissions_from_roles()
                    user.sudo()._sync_approvals_from_roles()
                    _logger.info("action_sync_role_users: synced user %s (id=%s) for role %s", user.login, user.id, self.name)
                except Exception:
                    _logger.exception("action_sync_role_users: failed to sync user %s (id=%s) for role %s", user.login, user.id, self.name)
       
        return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': _('Success'),
            'message': _('Role users synchronized successfully.'),
            'type': 'success',
            'sticky': False,
        }
    }
    
    
    def copy(self, default=None):
        """Override copy to generate unique name for duplicated roles."""
        self.ensure_one()
        default = dict(default or {})
        
        if 'name' not in default:
            new_name = _("%s (copy)") % self.name
            
            existing = self.search([('name', '=', new_name)], limit=1)
            
            if existing:
                counter = 2
                while True:
                    new_name = _("%s (copy %s)") % (self.name, counter)
                    existing = self.search([('name', '=', new_name)], limit=1)
                    if not existing:
                        break
                    counter += 1
            
            default['name'] = new_name
        
        return super(UserRole, self).copy(default)

    
    def write(self, vals):
        """When role definition changes, sync all users who have this role."""
        users_to_sync_permissions = self.env['res.users']
        users_to_sync_approvals = self.env['res.users']
        newly_added_users = self.env['res.users']
        
        if 'group_ids' in vals or 'company_ids' in vals or 'user_ids' in vals:
            users_to_sync_permissions = self.user_ids
            
            if 'user_ids' in vals:
                for command in vals['user_ids']:
                    if command[0] == 3:  # Remove user
                        users_to_sync_permissions |= self.env['res.users'].browse(command[1])
                    elif command[0] == 4:  # Add user
                        new_user = self.env['res.users'].browse(command[1])
                        users_to_sync_permissions |= new_user
                        newly_added_users |= new_user
                    elif command[0] == 6:  # Replace all
                        new_user_ids = set(command[2])
                        current_user_ids = set(self.user_ids.ids)
                        removed_user_ids = current_user_ids - new_user_ids
                        added_user_ids = new_user_ids - current_user_ids
                        users_to_sync_permissions |= self.env['res.users'].browse(list(removed_user_ids))
                        added_users = self.env['res.users'].browse(list(added_user_ids))
                        users_to_sync_permissions |= added_users
                        newly_added_users |= added_users
            
        if any(field in vals for field in ['is_request_approver', 'company_ids', 'branch_ids', 'limit_to_user_context', 'limit_to_role_context', 'user_ids']):
            users_to_sync_approvals = self.user_ids
            
            if 'user_ids' in vals:
                for command in vals['user_ids']:
                    if command[0] == 3:
                        users_to_sync_approvals |= self.env['res.users'].browse(command[1])
                    elif command[0] == 4:
                        users_to_sync_approvals |= self.env['res.users'].browse(command[1])
                    elif command[0] == 6:
                        new_user_ids = set(command[2])
                        current_user_ids = set(self.user_ids.ids)
                        removed_user_ids = current_user_ids - new_user_ids
                        added_user_ids = new_user_ids - current_user_ids
                        users_to_sync_approvals |= self.env['res.users'].browse(list(removed_user_ids))
                        users_to_sync_approvals |= self.env['res.users'].browse(list(added_user_ids))
        
        res = super().write(vals)
        
        if users_to_sync_permissions:
            _logger.info("Role definition changed for %s. Syncing %d users.", 
                        self.mapped('name'), len(users_to_sync_permissions))
            
            ctx = {}
            if newly_added_users:
                ctx['newly_added_user_ids'] = newly_added_users.ids
                ctx['priority_role_id'] = self.id
            
            users_to_sync_permissions.with_context(**ctx)._sync_permissions_from_roles()
        
        if users_to_sync_approvals:
            _logger.info("Role approval settings changed for %s. Syncing approvals for %d users.", 
                        self.mapped('name'), len(users_to_sync_approvals))
            users_to_sync_approvals._sync_approvals_from_roles()
            
        return res
    
    

class RoleGroupOwnership(models.Model):
    """
    This is an internal model to track which groups are granted by roles.
    It prevents accidentally removing a group that was manually added
    or is provided by another role.
    """
    _name = 'user.role.group.ownership'
    _description = 'User Role Group Ownership'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    group_id = fields.Many2one('res.groups', required=True, ondelete='cascade', index=True)
    role_ids = fields.Many2many('user.role')

    _sql_constraints = [
        ('user_group_uniq', 'unique (user_id, group_id)', 
         'A user can only have one ownership record per group.')
    ]


class RoleApprovalOwnership(models.Model):
    """
    Track which memo stage approvals are granted by roles.
    Similar to RoleGroupOwnership but for memo approvals.
    """
    _name = 'user.role.approval.ownership'
    _description = 'User Role Approval Ownership'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    stage_id = fields.Many2one('memo.stage', required=True, ondelete='cascade', index=True)
    role_ids = fields.Many2many('user.role', string='Granting Roles')

    _sql_constraints = [
        ('user_stage_uniq', 'unique (user_id, stage_id)', 
         'A user can only have one ownership record per memo stage.')
    ]