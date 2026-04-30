from odoo import http
from odoo.http import request, Response
import json
import logging
import traceback
from odoo.modules.module import get_resource_path

_logger = logging.getLogger(__name__)


class EmployeeDashboardPortal(http.Controller):

    # ── Page route ────────────────────────────────────────────────────────────
    @http.route('/emp-portal', type='http', auth='user')
    def show_employee_dashboard(self, **kw):
        """Serve the employee dashboard HTML page."""
        file_path = get_resource_path(
            'portal_request',          # <-- change to your module name
            'static/src/html',
            'employee_portal.html'
        )

        if not file_path:
            return "Dashboard HTML file not found."

        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()

        return request.make_response(
            html,
            headers=[('Content-Type', 'text/html')]
        )

    # ── Employee profile API ───────────────────────────────────────────────────
    @http.route('/employee/api/dashboard/profile', type='http', auth='user', methods=['GET'], csrf=False)
    def get_employee_profile(self, **kwargs):
        """
        Return profile data for the logged-in employee.
        Fields: name, employee_number, department, manager, job_position,
                work_email, work_phone, company, image_url
        """
        try:
            current_user = request.env.user
            employee = request.env['hr.employee'].sudo().search(
                [('user_id', '=', current_user.id)], limit=1
            )

            if not employee:
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'No employee record linked to this user.'}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Build image URL using Odoo's binary route
            image_url = None
            if employee.image_1920 or employee.image_128:
                image_url = f'/web/image/hr.employee/{employee.id}/image_128'

            data = {
                'id':              employee.id,
                'name':            employee.name or '',
                'employee_number': employee.employee_number or employee.barcode or 'N/A',
                'department':      employee.department_id.name if employee.department_id else 'N/A',
                'manager':         employee.parent_id.name if employee.parent_id else 'N/A',
                'job_position':    employee.job_id.name if employee.job_id else (employee.job_title or 'N/A'),
                'work_email':      employee.work_email or current_user.email or 'N/A',
                'work_phone':      employee.work_phone or employee.mobile_phone or 'N/A',
                'company':         employee.company_id.name if employee.company_id else 'N/A',
                'image_url':       image_url,
            }

            return request.make_response(
                json.dumps({'status': 'success', 'data': data}),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error(f"Dashboard profile error: {e}\n{traceback.format_exc()}")
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    # ── Stats API ──────────────────────────────────────────────────────────────
    @http.route('/employee/api/dashboard/stats', type='http', auth='user', methods=['GET'], csrf=False)
    def get_employee_stats(self, **kwargs):
        """
        Return all dashboard statistics for the logged-in employee:
          - requests   : count of records in memo.model linked to employee
          - leaves     : approved leave allocations / requests taken
          - appraisals : count of pms.appraisee records
          - payslips   : count of hr.payslip records
          - projects   : count of project.project where employee is member
          - tasks      : count of project.task assigned to employee
          - appraisal_scores : list of overall_score floats (for donut chart)
          - appraisal_avg    : average of above scores
        """
        try:
            current_user = request.env.user
            env          = request.env

            # Find linked employee
            employee = env['hr.employee'].sudo().search(
                [('user_id', '=', current_user.id)], limit=1
            )

            emp_id  = employee.id if employee else False
            user_id = current_user.id

            # ── 1. Requests (memo.model) ────────────────────────────────
            requests_count = 0
            try:
                MemoModel = env['memo.model'].sudo()
                if emp_id:
                    requests_count = MemoModel.search_count([
                        '|',
                        ('employee_id', '=', emp_id),
                        ('create_uid', '=', user_id),
                    ])
                else:
                    requests_count = MemoModel.search_count([('create_uid', '=', user_id)])
            except Exception:
                _logger.warning("memo.model not available or query failed")

            # ── 2. Leaves taken ─────────────────────────────────────────
            leaves_count = 0
            try:
                LeaveRequest = env['hr.leave'].sudo()
                domain = [
                    ('state', 'in', ['validate', 'validate1']),
                    ('holiday_status_id.time_type', '=', 'leave'),
                ]
                if emp_id:
                    domain.append(('employee_id', '=', emp_id))
                else:
                    domain.append(('user_id', '=', user_id))
                leaves_count = LeaveRequest.search_count(domain)
            except Exception:
                _logger.warning("hr.leave query failed")

            # ── 3. Appraisals (pms.appraisee) ───────────────────────────
            appraisals_count  = 0
            appraisal_scores  = []
            appraisal_avg     = None
            try:
                AppraiseeModel = env['pms.appraisee'].sudo()
                domain = []
                if emp_id:
                    domain = [('employee_id', '=', emp_id)]
                elif user_id:
                    domain = [('user_id', '=', user_id)]

                appraisees       = AppraiseeModel.search(domain)
                appraisals_count = len(appraisees)

                # Collect overall_score values (skip nulls/zeros for the chart)
                for a in appraisees:
                    score = getattr(a, 'overall_score', None) or getattr(a, 'score', None)
                    if score is not None:
                        try:
                            appraisal_scores.append(float(score))
                        except (TypeError, ValueError):
                            pass

                if appraisal_scores:
                    appraisal_avg = sum(appraisal_scores) / len(appraisal_scores)
            except Exception:
                _logger.warning("pms.appraisee not available or query failed")

            # ── 4. Payslips (hr.payslip) ─────────────────────────────────
            payslips_count = 0
            try:
                PayslipModel = env['hr.payslip'].sudo()
                domain = []
                if emp_id:
                    domain = [('employee_id', '=', emp_id)]
                else:
                    domain = [('create_uid', '=', user_id)]
                payslips_count = PayslipModel.search_count(domain)
            except Exception:
                _logger.warning("hr.payslip query failed")

            # ── 5. Projects (project.project) ────────────────────────────
            projects_count = 0
            try:
                ProjectModel = env['project.project'].sudo()
                # Projects where user is a member OR is project manager
                all_projects = ProjectModel.search([])
                projects_count = len(all_projects.filtered(
                    lambda p: (
                        user_id in p.message_partner_ids.mapped('user_ids').ids or
                        (p.user_id and p.user_id.id == user_id) or
                        user_id in (p.members or p.env['res.users']).ids
                    )
                ))
                # Fallback: try direct member field
                if projects_count == 0:
                    projects_count = ProjectModel.search_count([
                        '|',
                        ('user_id', '=', user_id),
                        ('members', 'in', [user_id]),
                    ])
            except Exception:
                _logger.warning("project.project query failed")

            # ── 6. Tasks (project.task) ───────────────────────────────────
            tasks_count = 0
            try:
                TaskModel = env['project.task'].sudo()
                tasks_count = TaskModel.search_count([
                    ('user_ids', 'in', [user_id])
                ])
            except Exception:
                # Odoo 14 and below used user_id (single)
                try:
                    tasks_count = env['project.task'].sudo().search_count([
                        ('user_id', '=', user_id)
                    ])
                except Exception:
                    _logger.warning("project.task query failed")

            # ── Build response ────────────────────────────────────────────
            stats = {
                'requests':        requests_count,
                'leaves':          leaves_count,
                'appraisals':      appraisals_count,
                'payslips':        payslips_count,
                'projects':        projects_count,
                'tasks':           tasks_count,
                'appraisal_scores': appraisal_scores,
                'appraisal_avg':    round(appraisal_avg, 2) if appraisal_avg is not None else None,
            }

            return request.make_response(
                json.dumps({'status': 'success', 'data': stats}),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error(f"Dashboard stats error: {e}\n{traceback.format_exc()}")
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )