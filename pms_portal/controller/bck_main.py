# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo import http, fields
from odoo.http import request, Response
import logging
import traceback
from datetime import datetime, timedelta
from odoo.tools import file_path

class PMSPortalController(http.Controller):

    # ─── Helper ───────────────────────────────────────────────────────────────

    def _get_employee(self):
        """Return hr.employee record linked to current user, or None."""
        return request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )

    # ─── Main portal page ─────────────────────────────────────────────────────

    @http.route('/pms-portal', type='http', auth='user', website=False)
    def pms_portal(self, **kw):
        template_path = file_path('pms_portal/static/html/pms_portal.html')
        # file_path = get_resource_path(
        #     'pms_portal',
        #     'static',
        #     'html',
        #     'pms_portal.html'
        # )
        if not template_path:
            return "PMS Portal HTML file not found."

        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()

        employee = self._get_employee()
        data = {
            'user_name': request.env.user.name,
            'employee_id': employee.id if employee else False,
            'employee_name': employee.name if employee else '',
        }
        return request.make_response(
            html,
            headers=[
                ('Content-Type', 'text/html'),
                ('defaultData', json.dumps(data))
            ]
        )

    # ─── API: List appraisals ─────────────────────────────────────────────────

    @http.route('/pms/api/appraisals', type='json', auth='user', methods=['POST'])
    def get_appraisals(self, **kw):
        employee = self._get_employee()
        if not employee:
            return {'error': 'No employee record linked to this user.'}

        records = request.env['pms.appraisee'].sudo().search([
            ('employee_id', '=', employee.id)
        ])

        result = []
        for rec in records:
            result.append({
                'id': rec.id,
                'name': rec.name,
                'type_of_pms': rec.type_of_pms,
                'state': rec.state,
                'period': rec.name,  # adjust if you have a dedicated period field
                'submitted_date': rec.submitted_date.strftime('%Y-%m-%d %H:%M') if rec.submitted_date else '',
            })
        return {'appraisals': result}

    # ─── API: Get single appraisal ────────────────────────────────────────────

    @http.route('/pms/api/appraisal/<int:appraisal_id>', type='json', auth='user', methods=['POST'])
    def get_appraisal(self, appraisal_id, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or rec.employee_id.id != employee.id:
            return {'error': 'Record not found or access denied.'}

        goal_lines = []
        for line in rec.goal_setting_section_line_ids:
            goal_lines.append({
                'id': line.id,
                'name': line.name,
                'weightage': line.weightage,
                'pms_uom': line.pms_uom,
                'target': line.target,
                'acceptance_status': line.acceptance_status,
                'fa_comment': line.fa_comment or '',
                'state': line.state,
                'is_direct_appraisal': 'yes' if not rec.goal_setting_section_line_ids.ids else 'no',
            })

        return {
            'id': rec.id,
            'name': rec.name,
            'type_of_pms': rec.type_of_pms,
            'state': rec.state,
            'period': rec.name,
            'submitted_date': rec.submitted_date.strftime('%Y-%m-%d %H:%M') if rec.submitted_date else '',
            'employee_name': rec.employee_id.name,
            'job_title': rec.job_title or '',
            'department': rec.department_id.name if rec.department_id else '',
            'goal_lines': goal_lines,
            'appraisee_comment': rec.appraisee_comment or '',
        }

    # ─── API: Save goal lines ─────────────────────────────────────────────────

    @http.route('/pms/api/save-goals', type='json', auth='user', methods=['POST'])
    def save_goals(self, appraisal_id=None, lines=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or rec.employee_id.id != employee.id:
            return {'error': 'Record not found or access denied.'}

        if rec.state not in ('goal_setting_draft',):
            return {'error': 'Appraisal is not in Goal Setting stage.'}

        # Validate total weightage
        total = sum(int(l.get('weightage', 0)) for l in lines)
        if total > 100:
            return {'error': f'Total weightage ({total}) cannot exceed 100.'}

        GoalLine = request.env['goal.setting.section.line'].sudo()

        # Process lines: update existing, create new, delete removed
        existing_ids = [l['id'] for l in lines if l.get('id')]
        # Delete lines removed by user
        GoalLine.search([
            ('goal_setting_section_id', '=', rec.id),
            ('id', 'not in', existing_ids)
        ]).unlink()

        for line_data in lines:
            vals = {
                'name': line_data.get('name', ''),
                'weightage': int(line_data.get('weightage', 0)),
                'pms_uom': line_data.get('pms_uom', ''),
                'target': line_data.get('target', ''),
                'goal_setting_section_id': rec.id,
            }
            if line_data.get('id'):
                GoalLine.browse(line_data['id']).write(vals)
            else:
                GoalLine.create(vals)

        return {'success': True, 'message': 'Goal settings saved successfully.'}

    # ─── API: Submit goal setting ─────────────────────────────────────────────

    @http.route('/pms/api/submit-goal-setting', type='json', auth='user', methods=['POST'])
    def submit_goal_setting(self, appraisal_id=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or rec.employee_id.id != employee.id:
            return {'error': 'Record not found or access denied.'}

        if rec.state != 'goal_setting_draft':
            return {'error': 'Appraisal is not in Goal Setting draft stage.'}

        if not rec.goal_setting_section_line_ids:
            return {'error': 'Please add at least one Goal Setting line before submitting.'}

        total_weightage = sum(rec.goal_setting_section_line_ids.mapped('weightage'))
        if total_weightage > 100:
            return {'error': f'Total weightage ({total_weightage}) cannot exceed 100.'}

        # Trigger the backend submit method if it exists, else write state
        try:
            rec.goal_setting_button_submit()  # call existing backend method
        except AttributeError:
            rec.write({'state': 'gs_fa'})

        return {'success': True, 'message': 'Goal Setting submitted to Manager successfully.'}

    # ─── API: Manager approve / return ────────────────────────────────────────

    @http.route('/pms/api/manager-action', type='json', auth='user', methods=['POST'])
    def manager_action(self, appraisal_id=None, action=None, reason=None, **kw):
        """action: 'approve' | 'return' """
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists():
            return {'error': 'Record not found.'}

        # Only the functional manager (manager_id) or admin supervisor can act
        employee = self._get_employee()
        if not employee or rec.manager_id.id != employee.id:
            # Also allow administrative supervisor
            if not employee or rec.administrative_supervisor_id.id != employee.id:
                return {'error': 'You are not authorised to perform this action.'}

        if rec.state != 'gs_fa':
            return {'error': 'Appraisal is not pending manager approval.'}

        if action == 'approve':
            try:
                rec.action_manager_approve_goal_setting()
            except AttributeError:
                rec.write({'state': 'hyr_draft'})
            return {'success': True, 'message': 'Goal Setting approved.'}

        elif action == 'return':
            if not reason:
                return {'error': 'Please provide a reason for returning.'}
            try:
                rec.action_return_goal_setting(reason=reason)
            except (AttributeError, TypeError):
                # Fallback: log note and revert state
                rec.write({'state': 'goal_setting_draft'})
                rec.message_post(body=f"Goal Setting returned by manager. Reason: {reason}")
            return {'success': True, 'message': 'Goal Setting returned to employee.'}

        return {'error': 'Invalid action.'}

    # ─── API: Manager's pending approvals ─────────────────────────────────────

    @http.route('/pms/api/pending-approvals', type='json', auth='user', methods=['POST'])
    def pending_approvals(self, **kw):
        employee = self._get_employee()
        if not employee:
            return {'error': 'No employee record found.'}

        records = request.env['pms.appraisee'].sudo().search([
            ('manager_id', '=', employee.id),
            ('state', '=', 'gs_fa')
        ])

        result = []
        for rec in records:
            result.append({
                'id': rec.id,
                'name': rec.name,
                'employee_name': rec.employee_id.name,
                'type_of_pms': rec.type_of_pms,
                'state': rec.state,
                'submitted_date': rec.submitted_date.strftime('%Y-%m-%d %H:%M') if rec.submitted_date else '',
            })
        return {'pending': result}