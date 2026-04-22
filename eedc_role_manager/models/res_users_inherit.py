from odoo import models, fields, api, _, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    role_ids = fields.Many2many(
        'user.role', 
        'user_role_users_rel', 
        'user_id', 
        'role_id',
        string='Roles',
        copy=False
    )
    
    branch_ids = fields.Many2many(
        'multi.branch',
        'user_branch_rel',
        'user_id',
        'branch_id',
        string='Branches',
        help="User's assigned branches for approval context"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to sync roles after user creation."""
        users = super().create(vals_list)
        users_with_roles = users.filtered('role_ids')
        if users_with_roles:
            users_with_roles._sync_permissions_from_roles()
            users_with_roles._sync_approvals_from_roles()
        return users

   
    
    def write(self, vals):
        """Override write to sync roles and approvals when relevant fields change."""
        users_to_resync_approvals = None
        newly_added_roles = self.env['user.role']
        
        if 'role_ids' in vals:
            for command in vals['role_ids']:
                if command[0] == 4:
                    newly_added_roles |= self.env['user.role'].browse(command[1])
                elif command[0] == 6:
                    new_role_ids = set(command[2])
                    current_role_ids = set(self.role_ids.ids)
                    added_role_ids = new_role_ids - current_role_ids
                    newly_added_roles |= self.env['user.role'].browse(list(added_role_ids))
        
        if any(field in vals for field in ['role_ids', 'branch_ids', 'branch_id', 'company_id', 'company_ids']):
            users_to_resync_approvals = self
            
        res = super().write(vals)
        
        if 'role_ids' in vals:
            ctx = {}
            if newly_added_roles:
                portal_user = self.env.ref('base.group_portal', raise_if_not_found=False)
                portal_roles = newly_added_roles.filtered(lambda r: portal_user in r.group_ids) if portal_user else self.env['user.role']
                
                if portal_roles:
                    ctx['newly_added_user_ids'] = self.ids
                    ctx['priority_role_id'] = portal_roles[0].id
                    _logger.info("User %s: Adding Portal role %s, will trigger downgrade", 
                            self.mapped('name'), portal_roles[0].name)
            
            self.with_context(**ctx)._sync_permissions_from_roles()
            
        if users_to_resync_approvals:
            users_to_resync_approvals._sync_approvals_from_roles()
            
        return res

    
    
    def _sync_permissions_from_roles(self):
        """
        Synchronize groups and companies from roles.
        Priority: Newly added role wins in conflicts.
        """
        ownership_model = self.env['user.role.group.ownership']
        
        newly_added_user_ids = self.env.context.get('newly_added_user_ids', [])
        priority_role_id = self.env.context.get('priority_role_id')
        
        users_to_sync = self.filtered(lambda u: u.id != SUPERUSER_ID)
        for user in users_to_sync:
            internal_user = self.env.ref('base.group_user', raise_if_not_found=False)
            portal_user = self.env.ref('base.group_portal', raise_if_not_found=False)
            
            if not internal_user or not portal_user:
                desired_groups = user.role_ids.mapped('group_ids')
            else:
                internal_implying_groups = self._get_groups_implying_internal(internal_user)
                internal_check_set = internal_implying_groups | internal_user
                
                desired_groups = user.role_ids.mapped('group_ids')
                roles_to_remove = self.env['user.role']
                
                has_internal_in_roles = bool(desired_groups & internal_check_set)
                has_portal_in_roles = portal_user in desired_groups
                
                is_newly_added = user.id in newly_added_user_ids
                priority_role = self.env['user.role'].browse(priority_role_id) if priority_role_id else None
                
                portal_has_priority = False
                if is_newly_added and priority_role:
                    portal_has_priority = portal_user in priority_role.group_ids
                
                # === CONFLICT RESOLUTION ===
                
                if has_internal_in_roles and has_portal_in_roles:
                    if portal_has_priority:
                        internal_roles = user.role_ids.filtered(
                            lambda r: bool(r.group_ids & internal_check_set) and r.id != priority_role_id
                        )
                        roles_to_remove |= internal_roles
                        _logger.warning(
                            "User %s: Adding Portal role '%s'. Removing Internal roles: %s",
                            user.name, priority_role.name, internal_roles.mapped('name')
                        )
                        
                        groups_to_remove = internal_check_set & user.groups_id
                        if groups_to_remove:
                            user.sudo().write({
                                'groups_id': [(3, g.id) for g in groups_to_remove]
                            })
                    else:
                        portal_roles = user.role_ids.filtered(
                            lambda r: portal_user in r.group_ids and r.id != priority_role_id
                        )
                        roles_to_remove |= portal_roles
                        _logger.warning(
                            "User %s: Conflict - Internal wins. Removing Portal roles: %s",
                            user.name, portal_roles.mapped('name')
                        )
                
                elif has_internal_in_roles and not has_portal_in_roles:
                    if portal_user in user.groups_id:
                        user.sudo().write({'groups_id': [(3, portal_user.id)]})
                        _logger.info("User %s: Removed Portal group (Internal access granted)", user.name)
                
                elif has_portal_in_roles and not has_internal_in_roles:
                    pass
                
                if roles_to_remove:
                    user.sudo().write({'role_ids': [(3, r.id) for r in roles_to_remove]})
                    _logger.warning(
                        "User %s: Removed conflicting roles: %s",
                        user.name, roles_to_remove.mapped('name')
                    )
                    desired_groups = user.role_ids.mapped('group_ids')
                    
                final_has_internal = bool(desired_groups & internal_check_set)
                final_has_portal = portal_user in desired_groups

                if not final_has_internal and not final_has_portal:
                    desired_groups |= portal_user
                    _logger.info(
                        "User %s (%s): Defaulting to Portal group as no remaining role grants Internal or Portal access.",
                        user.login or user.name, user.id
                    )
            
            # === Normal group sync ===
            current_ownerships = ownership_model.search([('user_id', '=', user.id)])
            groups_managed_by_roles = current_ownerships.mapped('group_id')
            
            groups_to_add = desired_groups - user.groups_id
            if groups_to_add:
                user.sudo().write({'groups_id': [(4, group.id) for group in groups_to_add]})
            
            groups_to_remove = groups_managed_by_roles - desired_groups
            if groups_to_remove:
                user.sudo().write({'groups_id': [(3, group.id) for group in groups_to_remove]})
            
            current_ownerships.filtered(lambda own: own.group_id not in desired_groups).unlink()
            
            for group in desired_groups:
                ownership = ownership_model.search([
                    ('user_id', '=', user.id),
                    ('group_id', '=', group.id)
                ], limit=1)
                roles_granting_group = user.role_ids.filtered(lambda r: group in r.group_ids)
                if ownership:
                    ownership.sudo().write({'role_ids': [(6, 0, roles_granting_group.ids)]})
                else:
                    ownership_model.sudo().create({
                        'user_id': user.id,
                        'group_id': group.id,
                        'role_ids': [(6, 0, roles_granting_group.ids)]
                    })
            
            # === Company sync - ONLY for cross-scope roles ===
            # Roles with limit_to_user_context or limit_to_role_context should NOT grant company access
            cross_scope_roles = user.role_ids.filtered(
                lambda r: not r.limit_to_user_context and not r.limit_to_role_context
            )
            
            if cross_scope_roles:
                desired_companies = cross_scope_roles.mapped('company_ids')
                if desired_companies:
                    user.sudo().write({'company_ids': [(6, 0, desired_companies.ids)]})
                    if user.company_id not in desired_companies:
                        user.sudo().write({'company_id': desired_companies[0].id})
                    _logger.info(
                        "User %s: Updated company access from cross-scope roles: %s",
                        user.name, desired_companies.mapped('name')
                    )
            else:
                _logger.info(
                    "User %s: No cross-scope roles, skipping company assignment",
                    user.name
                )
        
        return True


    def _get_groups_implying_internal(self, internal_group):
        """
        Find all groups that imply internal_group (with cycle protection).
        """
        Groups = self.env['res.groups']
        to_visit = [internal_group.id]
        visited = set()
        result = self.env['res.groups']
        
        while to_visit:
            gid = to_visit.pop(0)
            if gid in visited:
                continue
            visited.add(gid)
            
            implying = Groups.search([('implied_ids', 'in', gid)])
            new_to_visit = implying.filtered(lambda g: g.id not in visited)
            result |= implying
            to_visit.extend(new_to_visit.ids)
        
        return result

    
    
    def _sync_approvals_from_roles(self):
        """
        Synchronize memo.stage approver lists based on user's roles, companies and branches.
        Includes automatic cleanup of stale ownership records from archived employees.
        """
        MemoStage = self.env['memo.stage']
        ownership_model = self.env['user.role.approval.ownership']
        
        # CLEANUP: Fix ownership records with stale employee references
        for user in self:
            current_employee = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
            
            if not current_employee:
                _logger.info(f"User {user.login} has no linked employee, skipping cleanup")
                continue
            
            # Find ownership records for this user that reference different employees
            stale_ownerships = ownership_model.sudo().search([
                ('user_id', '=', user.id),
                ('employee_id', '!=', current_employee.id)
            ])
            
            if stale_ownerships:
                _logger.warning(f"User {user.login}: Found {len(stale_ownerships)} ownership records with stale employee references")
                
                for stale_own in stale_ownerships:
                    old_employee = stale_own.employee_id
                    stage = stale_own.stage_id
                    
                    # Check if duplicate would exist with current employee
                    duplicate_check = ownership_model.sudo().search([
                        ('user_id', '=', user.id),
                        ('employee_id', '=', current_employee.id),
                        ('stage_id', '=', stage.id)
                    ], limit=1)
                    
                    if duplicate_check:
                        # Duplicate exists, just delete the stale one
                        _logger.info(f"Deleting stale ownership (stage: {stage.name}, old emp: {old_employee.name})")
                        
                        # Remove old employee from stage approvers if still there
                        if old_employee in stage.approver_ids:
                            stage.sudo().write({'approver_ids': [(3, old_employee.id)]})
                        
                        stale_own.sudo().unlink()
                    else:
                        # No duplicate, update to current employee
                        _logger.info(f"Updating ownership to current employee (stage: {stage.name}, {old_employee.name} -> {current_employee.name})")
                        
                        # Remove old employee from stage approvers
                        if old_employee in stage.approver_ids:
                            stage.sudo().write({'approver_ids': [(3, old_employee.id)]})
                        
                        # Update ownership record
                        stale_own.sudo().write({'employee_id': current_employee.id})
                        
                        # Add current employee to stage approvers if not there
                        if current_employee not in stage.approver_ids:
                            stage.sudo().write({'approver_ids': [(4, current_employee.id)]})
                
                _logger.info(f"Completed cleanup for user {user.login}")
        
        # Continue with normal sync
        employees = self.env['hr.employee'].search([('user_id', 'in', self.ids)])
        
        for employee in employees:
            user = employee.user_id
            _logger.info(f"Processing user: {user.name} with employee: {employee.name}")
            
            approval_roles = user.role_ids.filtered('is_request_approver')
            _logger.info(f"Approval roles: {approval_roles.mapped('name')} (IDs: {approval_roles.ids})")
            
            if not approval_roles:
                _logger.info(f"User {user.name} has no approval roles - removing from all stages")
                current_ownerships = ownership_model.search([
                    ('user_id', '=', user.id),
                    ('employee_id', '=', employee.id)
                ])
                stages_to_clean = current_ownerships.mapped('stage_id')
                
                for stage in stages_to_clean:
                    if employee in stage.approver_ids:
                        stage.write({'approver_ids': [(3, employee.id)]})
                        _logger.info(f"Removed employee {employee.name} from stage {stage.name}")
                
                current_ownerships.unlink()
                _logger.info(f"Deleted {len(current_ownerships)} ownership records for user {user.name}")
                continue

            stages_user_should_approve = self.env['memo.stage']
            
            if approval_roles:
                context_limited_roles = approval_roles.filtered('limit_to_user_context')
                role_limited_roles = approval_roles.filtered('limit_to_role_context')
                cross_scope_roles = approval_roles - context_limited_roles - role_limited_roles
                
                _logger.info(f"Context limited roles: {context_limited_roles.mapped('name')}")
                _logger.info(f"Role limited roles: {role_limited_roles.mapped('name')}")
                _logger.info(f"Cross scope roles: {cross_scope_roles.mapped('name')}")
                
                for role in context_limited_roles:
                    _logger.info(f"Processing context-limited role: {role.name}")
                    
                    domain = [('approval_role_ids', 'in', [role.id])]
                    
                    if user.company_id:
                        domain.append(('memo_config_id.company_id', '=', user.company_id.id))
                        if role.company_ids and user.company_id not in role.company_ids:
                            _logger.info(f"Skipping role {role.name} - user company {user.company_id.name} not in role's allowed companies")
                            continue
                    
                    if role.branch_ids:
                        if hasattr(user, 'branch_id') and user.branch_id:
                            if user.branch_id not in role.branch_ids:
                                _logger.info(f"Skipping role {role.name} - user branch {user.branch_id.name} not in role's allowed branches")
                            domain.append(('memo_config_id.branch_id', '=', user.branch_id.id))
                        else:
                            _logger.info(f"Skipping role {role.name} - role has branch restrictions but user has no branch assigned")
                            continue
                    
                    _logger.info(f"Searching for stages with domain: {domain}")
                    user_context_stages = MemoStage.search(domain)
                    _logger.info(f"Found {len(user_context_stages)} stages for context-limited role {role.name}: {user_context_stages.mapped('name')}")
                    stages_user_should_approve |= user_context_stages
                
                for role in role_limited_roles:
                    _logger.info(f"Processing role-limited role: {role.name}")
                    
                    domain = [('approval_role_ids', 'in', [role.id])]
                    
                    applicable_companies = user.company_ids & role.company_ids if role.company_ids else user.company_ids           
                    
                    if applicable_companies:
                        domain.append(('memo_config_id.company_id', 'in', applicable_companies.ids))
                    else:
                        _logger.info(f"Skipping role {role.name} - no company intersection between user and role and also no allowed companies set")
                        
                    
                    if role.branch_ids:
                        applicable_branches = role.branch_ids & user.branch_ids if user.branch_ids else False
                        if not applicable_branches:
                            _logger.info(f"Skipping role {role.name} - user has no branches that intersect with role's allowed branches")
                            continue
                        domain.append(('memo_config_id.branch_id', 'in', applicable_branches.ids))
                    
                    _logger.info(f"Searching for stages with domain: {domain}")
                    role_context_stages = MemoStage.search(domain)
                    _logger.info(f"Found {len(role_context_stages)} stages for role-limited role {role.name}: {role_context_stages.mapped('name')}")
                    stages_user_should_approve |= role_context_stages
                
                if cross_scope_roles:
                    _logger.info(f"Processing cross-scope roles: {cross_scope_roles.mapped('name')}")
                    potential_stages = MemoStage.search([('approval_role_ids', 'in', cross_scope_roles.ids)])
                    _logger.info(f"Found {len(potential_stages)} potential stages for cross-scope roles")
                    
                    for stage in potential_stages:
                        stage_config = stage.memo_config_id
                        stage_company = stage_config.company_id
                        stage_branch = stage_config.branch_id if hasattr(stage_config, 'branch_id') else None
                        _logger.info(f"Checking stage: {stage.name} (Company: {stage_company.name if stage_company else 'None'}, Branch: {stage_branch.name if stage_branch else 'None'})")

                        matching_roles = cross_scope_roles & stage.approval_role_ids
                        if not matching_roles:
                            _logger.info(f"No matching roles for stage {stage.name}")
                            continue

                        should_approve = False
                        for role in matching_roles:
                            _logger.info(f"Checking role {role.name} against stage {stage.name}")
                            
                            role_allows_company = True
                            if stage_company and role.company_ids:
                                if stage_company not in role.company_ids:
                                    role_allows_company = False
                                    _logger.info(f"Role {role.name} doesn't allow company {stage_company.name}")

                            role_allows_branch = True
                            if stage_branch:
                                if role.branch_ids:
                                    if stage_branch not in role.branch_ids:
                                        role_allows_branch = False
                                        _logger.info(f"Role {role.name} doesn't allow branch {stage_branch.name}")
                                else:
                                    if not user.branch_ids or stage_branch not in user.branch_ids:
                                        role_allows_branch = False
                                        _logger.info(f"User doesn't have required branch {stage_branch.name}")
                            else:
                                if role.branch_ids and user.branch_ids and not (role.branch_ids & user.branch_ids):
                                    role_allows_branch = False
                                    _logger.info(f"User branches {user.branch_ids.mapped('name')} don't intersect with role branches {role.branch_ids.mapped('name')}")
                                if role.branch_ids and not user.branch_ids:
                                    role_allows_branch = False
                                    _logger.info(f"Role has branch restrictions but user has no branches assigned")

                            _logger.info(f"Role {role.name}: company_allowed={role_allows_company}, branch_allowed={role_allows_branch}")
                            if role_allows_company and role_allows_branch:
                                should_approve = True
                                _logger.info(f"User should approve stage {stage.name} via role {role.name}")
                                break

                        if should_approve:
                            stages_user_should_approve |= stage

            _logger.info(f"Final stages user should approve: {stages_user_should_approve.mapped('name')} (Total: {len(stages_user_should_approve)})")

            current_ownerships = ownership_model.search([
                ('user_id', '=', user.id),
                ('employee_id', '=', employee.id)
            ])
            current_stages = current_ownerships.mapped('stage_id')
            _logger.info(f"Current ownerships found: {len(current_ownerships)}")
            _logger.info(f"Current stages user is approving: {current_stages.mapped('name')} (IDs: {current_stages.ids})")
            
            for stage in stages_user_should_approve:
                _logger.info(f"Stage '{stage.name}' currently has approvers: {stage.approver_ids.mapped('name')} (IDs: {stage.approver_ids.ids})")
                _logger.info(f"Employee {employee.name} (ID: {employee.id}) in approvers? {employee.id in stage.approver_ids.ids}")
            
            actual_current_stages = current_stages.filtered(lambda s: employee in s.approver_ids)

            stages_to_add = stages_user_should_approve - actual_current_stages
            stages_to_remove = actual_current_stages - stages_user_should_approve
            
            _logger.info(f"Stages to add: {stages_to_add.mapped('name')} (Total: {len(stages_to_add)})")
            _logger.info(f"Stages to remove: {stages_to_remove.mapped('name')} (Total: {len(stages_to_remove)})")

            for stage in stages_to_add:
                _logger.info(f"Adding user {user.name} as approver to stage {stage.name}")
                if employee not in stage.approver_ids:
                    stage.write({'approver_ids': [(4, employee.id)]})
                    _logger.info(f"Successfully added employee {employee.name} to stage {stage.name} approvers")

                # Check for duplicate before creating
                existing = ownership_model.search([
                    ('user_id', '=', user.id),
                    ('stage_id', '=', stage.id)
                ], limit=1)
                
                if existing:
                    # Update existing record to correct employee
                    _logger.warning(f"Found existing ownership for user {user.name} on stage {stage.name}, updating to correct employee")
                    granting_roles = approval_roles.filtered(lambda r: r in stage.approval_role_ids)
                    existing.sudo().write({
                        'employee_id': employee.id,
                        'role_ids': [(6, 0, granting_roles.ids)]
                    })
                else:
                    # Create new record
                    granting_roles = approval_roles.filtered(lambda r: r in stage.approval_role_ids)
                    ownership_model.sudo().create({
                        'user_id': user.id,
                        'employee_id': employee.id,
                        'stage_id': stage.id,
                        'role_ids': [(6, 0, granting_roles.ids)]
                    })
                    _logger.info(f"Created ownership record for user {user.name} on stage {stage.name}")

            for stage in stages_to_remove:
                _logger.info(f"Removing user {user.name} as approver from stage {stage.name}")
                if employee in stage.approver_ids:
                    stage.write({'approver_ids': [(3, employee.id)]})
                    _logger.info(f"Successfully removed employee {employee.name} from stage {stage.name} approvers")
                    
            if stages_to_remove:
                ownership_model.search([
                    ('user_id', '=', user.id),
                    ('employee_id', '=', employee.id),
                    ('stage_id', 'in', stages_to_remove.ids)
                ]).unlink()

            remaining_ownerships = ownership_model.search([
                ('user_id', '=', user.id),
                ('employee_id', '=', employee.id),
                ('stage_id', 'in', stages_user_should_approve.ids)
            ])
            for ownership in remaining_ownerships:
                granting_roles = approval_roles.filtered(lambda r: r in ownership.stage_id.approval_role_ids)
                ownership.write({'role_ids': [(6, 0, granting_roles.ids)]})

        return True

    def action_sync_roles_manually(self):
        """Manual action to trigger role and approval sync - useful for testing/troubleshooting."""
        self._sync_permissions_from_roles()
        self._sync_approvals_from_roles()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Role and approval synchronization completed successfully.',
                'type': 'success',
                'sticky': False,
            }
        }