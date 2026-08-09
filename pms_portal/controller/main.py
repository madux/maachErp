# -*- coding: utf-8 -*-
import json
from odoo import http, fields
from odoo.http import request, Response
import logging
from odoo.tools import file_path

_logger = logging.getLogger(__name__)


class PMSPortalController(http.Controller):

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _get_employee(self):
        return request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )

    def _is_manager_of(self, rec, employee):
        if not employee:
            return False
        return (rec.manager_id.id == employee.id or
                rec.administrative_supervisor_id.id == employee.id)

    # ─── Main portal page ─────────────────────────────────────────────────────

    @http.route('/pms-portal', type='http', auth='user', website=False)
    def pms_portal(self, **kw):
        template_path = file_path('pms_portal/static/html/pms_portal.html')
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
        html = html.replace('</head>',
            f'<meta name="pms-user-data" content=\'{json.dumps(data)}\'></head>', 1)
        return request.make_response(html, headers=[('Content-Type', 'text/html')])

    # ─── API: List appraisals ─────────────────────────────────────────────────

    @http.route('/pms/api/appraisals', type='json', auth='user', methods=['POST'])
    def get_appraisals(self, **kw):
        employee = self._get_employee()
        if not employee:
            return {'error': 'No employee record linked to this user.'}
        records = request.env['pms.appraisee'].sudo().search([('employee_id', '=', employee.id)])
        return {'appraisals': [{
            'id': r.id, 'name': r.name, 'type_of_pms': r.type_of_pms, 'state': r.state,
            'submitted_date': r.submitted_date.strftime('%Y-%m-%d %H:%M') if r.submitted_date else '',
        } for r in records]}

    # ─── API: Full appraisal detail ───────────────────────────────────────────

    @http.route('/pms/api/appraisal/<int:appraisal_id>', type='json', auth='user', methods=['POST'])
    def get_appraisal(self, appraisal_id, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists():
            return {'error': 'Record not found.'}
        is_employee   = rec.employee_id.id == employee.id if employee else False
        is_fa         = rec.manager_id.id == employee.id if employee else False
        is_aa         = rec.administrative_supervisor_id.id == employee.id if employee else False
        is_reviewer   = rec.reviewer_id.id == employee.id if employee else False
        if not (is_employee or is_fa or is_aa or is_reviewer):
            return {'error': 'Access denied.'}

        def goal_line(l):
            return {'id': l.id, 'name': l.name, 'weightage': l.weightage,
                    'pms_uom': l.pms_uom, 'target': l.target,
                    'acceptance_status': l.acceptance_status,
                    'fa_comment': l.fa_comment or '', 'state': l.state}

        def hyr_line(l):
            return {'id': l.id, 'name': l.name, 'weightage': l.weightage,
                    'revise_weightage': l.revise_weightage,
                    'pms_uom': l.pms_uom, 'target': l.target,
                    'revise_target': l.revise_target or '',
                    'acceptance_status': l.acceptance_status or 'Accepted',
                    'hyr_fa_rating': l.hyr_fa_rating or '',
                    'hyr_aa_rating': l.hyr_aa_rating or '',
                    'fa_comment': l.fa_comment or '', 'state': l.state}

        def kra_line(l):
            return {'id': l.id, 'name': l.name, 'weightage': l.weightage,
                    'self_rating': l.self_rating,
                    'administrative_supervisor_rating': l.administrative_supervisor_rating,
                    'functional_supervisor_rating': l.functional_supervisor_rating,
                    'reviewer_rating': l.reviewer_rating,
                    'hyr_fa_rating': l.hyr_fa_rating or '',
                    'target': l.target or '', 'weighted_score': l.weighted_score}

        def lc_line(l):
            return {'id': l.id, 'name': l.name, 'weightage': l.weightage,
                    'administrative_supervisor_rating': l.administrative_supervisor_rating,
                    'functional_supervisor_rating': l.functional_supervisor_rating,
                    'reviewer_rating': l.reviewer_rating,
                    'weighted_score': l.weighted_score,
                    'section_avg_scale': l.section_avg_scale}

        def fc_line(l):
            return {'id': l.id, 'name': l.name, 'weightage': l.weightage,
                    'administrative_supervisor_rating': l.administrative_supervisor_rating,
                    'functional_supervisor_rating': l.functional_supervisor_rating,
                    'reviewer_rating': l.reviewer_rating,
                    'weighted_score': l.weighted_score,
                    'section_avg_scale': l.section_avg_scale}

        def training_line(l):
            return {'id': l.id, 'name': l.name or '', 'comments': l.comments or '',
                    'requested_date': str(l.requested_date) if l.requested_date else '',
                    'expected_completion_date': str(l.expected_completion_date) if l.expected_completion_date else '',
                    'requester_name': l.requester_id.name if l.requester_id else ''}

        def curr_assess_line(l):
            return {
                'id': l.id, 'name': l.name or '',
                'administrative_supervisor_rating': l.administrative_supervisor_rating,
                'functional_supervisor_rating': l.functional_supervisor_rating,
                'reviewer_rating': l.reviewer_rating,
                'assessment_type': l.assessment_type or 'none',
                'section_avg_scale': l.section_avg_scale, 
                # 'assessment_key': 'administrative_supervisor_rating' if 
                    }

        def pot_assess_line(l):
            return {'id': l.id, 'name': l.name or '',
                    'administrative_supervisor_rating': l.administrative_supervisor_rating,
                    'functional_supervisor_rating': l.functional_supervisor_rating,
                    'reviewer_rating': l.reviewer_rating,
                    'assessment_type': l.assessment_type or 'none',
                    'section_avg_scale': l.section_avg_scale}

        return {
            'id': rec.id, 'name': rec.name,
            'type_of_pms': rec.type_of_pms, 'state': rec.state,
            'submitted_date': rec.submitted_date.strftime('%Y-%m-%d %H:%M') if rec.submitted_date else '',
            'employee_name': rec.employee_id.name,
            'job_title': rec.job_title or '',
            'staff_id': rec.employee_id.employee_number or '',
            'administrative_supervisor_id': rec.administrative_supervisor_id.name or '',
            'manager_id': rec.manager_id.name or '',
            'reviewer_id': rec.reviewer_id.name or '',
            'department': rec.department_id.name if rec.department_id else '',
            'appraisee_comment': rec.appraisee_comment or '',
            'has_admin_supervisor': bool(rec.administrative_supervisor_id),
            'is_employee': is_employee, 'is_fa': is_fa, 'is_aa': is_aa, 'is_reviewer': is_reviewer,
            'goal_lines': [goal_line(l) for l in rec.goal_setting_section_line_ids],
            'hyr_lines':  [hyr_line(l)  for l in rec.hyr_kra_section_line_ids],
            'kra_lines':  [kra_line(l)  for l in rec.kra_section_line_ids],
            'lc_lines':   [lc_line(l)   for l in rec.lc_section_line_ids],
            'fc_lines':   [fc_line(l)   for l in rec.fc_section_line_ids],
            'training_lines': [training_line(l) for l in rec.training_section_line_ids],
            'current_assessment': [curr_assess_line(l) for l in rec.current_assessment_section_line_ids],
            'potential_assessment': [pot_assess_line(l) for l in rec.potential_assessment_section_line_ids],
            'is_direct_appraisal': 'yes' if not rec.goal_setting_section_line_ids.ids else 'no',
        }

    # ─── API: Save goal lines ─────────────────────────────────────────────────

    @http.route('/pms/api/save-goals', type='json', auth='user', methods=['POST'])
    def save_goals(self, appraisal_id=None, lines=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or rec.employee_id.id != employee.id:
            return {'error': 'Access denied.'}
        if rec.state != 'goal_setting_draft':
            return {'error': 'Appraisal is not in Goal Setting stage.'}
        total = sum(int(l.get('weightage', 0)) for l in lines)
        if total > 100:
            return {'error': f'Total weightage ({total}) cannot exceed 100.'}
        GoalLine = request.env['goal.setting.section.line'].sudo()
        existing_ids = [l['id'] for l in lines if l.get('id')]
        GoalLine.search([('goal_setting_section_id', '=', rec.id), ('id', 'not in', existing_ids)]).unlink()
        for ld in lines:
            vals = {'name': ld.get('name', ''), 'weightage': int(ld.get('weightage', 0)),
                    'pms_uom': ld.get('pms_uom', ''), 'target': ld.get('target', ''),
                    'goal_setting_section_id': rec.id}
            if ld.get('id'):
                GoalLine.browse(ld['id']).write(vals)
            else:
                GoalLine.create(vals)
        return {'success': True, 'message': 'Goal settings saved.'}

    # ─── API: Submit goal setting ─────────────────────────────────────────────

    @http.route('/pms/api/submit-goal-setting', type='json', auth='user', methods=['POST'])
    def submit_goal_setting(self, appraisal_id=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or rec.employee_id.id != employee.id:
            return {'error': 'Access denied.'}
        if rec.state != 'goal_setting_draft':
            return {'error': 'Not in Goal Setting draft stage.'}
        if not rec.goal_setting_section_line_ids:
            return {'error': 'Add at least one Goal Setting line.'}
        try:
            rec.goal_setting_button_submit()
        except AttributeError:
            rec.write({'state': 'gs_fa'})
        return {'success': True, 'message': 'Submitted to Manager for approval.'}

    # ─── API: Manager approve goal setting → HYR ─────────────────────────────

    @http.route('/pms/api/manager-approve-goal-setting', type='json', auth='user', methods=['POST'])
    def manager_approve_goal_setting(self, appraisal_id=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or not self._is_manager_of(rec, employee):
            return {'error': 'Access denied.'}
        if rec.state != 'gs_fa':
            return {'error': 'Not pending manager approval.'}
        try:
            rec.manager_submit_goal_setting_button()
        except AttributeError:
            rec.write({'state': 'hyr_draft'})
        return {'success': True, 'message': 'Approved. Mid Year Review stage started.'}

    # ─── API: Manager return goal setting ─────────────────────────────────────

    @http.route('/pms/api/manager-return-goal-setting', type='json', auth='user', methods=['POST'])
    def manager_return_goal_setting(self, appraisal_id=None, reason=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or not self._is_manager_of(rec, employee):
            return {'error': 'Access denied.'}
        if rec.state != 'gs_fa':
            return {'error': 'Not pending manager approval.'}
        if not reason:
            return {'error': 'Please provide a return reason.'}
        try:
            rec.action_return_goal_setting(reason=reason)
        except (AttributeError, TypeError):
            rec.write({'state': 'goal_setting_draft'})
            rec.message_post(body=f"Returned by manager. Reason: {reason}")
        return {'success': True, 'message': 'Returned to employee.'}

    # ─── API: Save HYR lines ──────────────────────────────────────────────────

    @http.route('/pms/api/save-hyr-lines', type='json', auth='user', methods=['POST'])
    def save_hyr_lines(self, appraisal_id=None, lines=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or not self._is_manager_of(rec, employee):
            return {'error': 'Only managers/AA can edit HYR lines.'}
        if rec.state not in ('hyr_draft', 'hyr_admin_rating', 'hyr_functional_rating'):
            return {'error': 'HYR lines not editable at this stage.'}
        is_fa = rec.manager_id.id == employee.id
        is_aa = rec.administrative_supervisor_id.id == employee.id
        HyrLine = request.env['hyr.kra.section.line'].sudo()
        for ld in lines:
            if not ld.get('id'):
                continue
            line = HyrLine.browse(ld['id'])
            if not line.exists():
                continue
            rw = float(ld.get('revise_weightage', line.revise_weightage) or 0)
            if rw > 25:
                return {'error': f'Revised weightage for "{line.name}" cannot exceed 25.'}
            vals = {
                'revise_weightage': rw,
                'fa_comment': ld.get('fa_comment', line.fa_comment or ''),
                'acceptance_status': ld.get('acceptance_status', line.acceptance_status),
                'revise_target': ld.get('revise_target', line.revise_target or ''),
            }
            if is_fa:
                vals['hyr_fa_rating'] = ld.get('hyr_fa_rating', line.hyr_fa_rating or '')
            if is_aa:
                vals['hyr_aa_rating'] = ld.get('hyr_aa_rating', line.hyr_aa_rating or '')
            line.write(vals)
        return {'success': True, 'message': 'Mid Year lines saved.'}

    # ─── API: Submit HYR (employee → FA) ─────────────────────────────────────

    @http.route('/pms/api/submit-hyr', type='json', auth='user', methods=['POST'])
    def submit_hyr(self, appraisal_id=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or rec.employee_id.id != employee.id:
            return {'error': 'Access denied.'}
        if rec.state != 'hyr_draft':
            return {'error': 'Not in Mid Year Review draft stage.'}
        try:
            rec.hyr_button_submit()
        except AttributeError:
            rec.write({'state': 'hyr_functional_rating'})
        return {'success': True, 'message': 'Submitted for Mid Year functional rating.'}

    # ─── API: Manager submits HYR → FYR ──────────────────────────────────────

    @http.route('/pms/api/submit-hyr-manager', type='json', auth='user', methods=['POST'])
    def submit_hyr_manager(self, appraisal_id=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or not self._is_manager_of(rec, employee):
            return {'error': 'Access denied.'}
        if rec.state != 'hyr_functional_rating':
            return {'error': 'Not in HYR Functional Rating stage.'}
        try:
            rec.hyr_button_functional_manager_rating()
        except AttributeError:
            rec.write({'state': 'draft', 'type_of_pms': 'fyr'})
        return {'success': True, 'message': 'Mid Year complete. Full Appraisal started.'}

    # ─── API: DELETE API  ────────────────────────────────────────────
    @http.route('/pms/api/delete', type='json', auth='user', methods=['POST'])
    def deleteApi(self, record_id=None, model=None, **kw):
        rec = request.env[f'{model}'].sudo().browse(record_id)
        if not rec.exists():
            return {'error': 'Record not existing.'}
        rec.unlink()
        _logger.info(f"DELETED ==> {record_id} {rec}")
        return {'success': True, 'message': 'Deleted record'}

    @http.route('/pms/api/save-kra-self-rating', type='json', auth='user', methods=['POST'])
    def save_kra_self_rating(self, appraisal_id=None, lines=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or rec.employee_id.id != employee.id:
            return {'error': 'Access denied.'}
        # if rec.state != 'draft':
        #     return {'error': 'Self-rating only in Full Appraisal Review. Kindly Click the Submit Full Appraisal Review Button'}
        KRALine = request.env['kra.section.line'].sudo()
        _logger.info(f"KRA SAVED LINES ==> {lines}")
        sum_weightage = [int(weight.get('self_weightage', 0)) for weight in lines]
        if sum(sum_weightage) != 100:
            return {'error': f'Total weightage must be 100 % {sum(sum_weightage)}'}

        for ld in lines:
            rating = int(ld.get('self_rating', 0))
            self_weightage = int(ld.get('self_weightage', 0))
            if rating < 1 or rating > 4:
                return {'error': 'Self rating must be 1–4.'}

            if self_weightage < 5 or self_weightage > 25:
                return {'error': f'Weightage must be 5–25. {self_weightage}'}
            if not ld.get('id'):
                #continue
                _logger.info(f"KRA creating LINES ==> {lines}")

                KRALine.create({
                    'kra_section_id': rec.id, 
                    'name': ld.get('name'), 
                    'weightage': int(ld.get('self_weightage', 0)), 
                    'self_rating': int(ld.get('self_rating', 0)), 
                    'state': rec.state, 
                })
            else:
                KRALine.browse(ld['id']).write({
                    'self_rating': rating,
                    'name': ld.get('name'), 
                    'weightage': int(ld.get('self_weightage', 0)), 
                    'self_rating': int(ld.get('self_rating', 0)), 
                    'state': rec.state, 
                    })
        saved_lines = rec.kra_section_line_ids.read(['id', 'name', 'weightage', 'self_rating', 'state'])
        return {'success': True, 'message': 'Self ratings saved.', 'lines': saved_lines}

    # ─── API: Employee submits FYR ────────────────────────────────────────────

    @http.route('/pms/api/submit-fyr', type='json', auth='user', methods=['POST'])
    def submit_fyr(self, appraisal_id=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        
        if not rec.kra_section_line_ids:
            return {'error': 'Please Add KRAs'}
        if not rec.exists() or rec.employee_id.id != employee.id:
            return {'error': 'Access denied.'}
        if rec.state != 'draft':
            return {'error': 'Not in Full Appraisal Review.'}
        try:
            rec.button_submit()
        except AttributeError:
            next_s = 'admin_rating' if rec.administrative_supervisor_id else 'functional_rating'
            rec.write({'state': next_s})
        return {'success': True, 'message': 'Submitted for rating.'}

    @http.route('/pms/api/save-ratings', type='json', auth='user', methods=['POST'])
    def save_ratings(self, appraisal_id=None, section=None, lines=None, **kw):

        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)

        if not rec.exists():
            return {'error': 'Record not found.'}

        # -------------------------
        # Authorization
        # -------------------------
        is_aa = rec.administrative_supervisor_id.id == employee.id if employee else False
        is_fa = rec.manager_id.id == employee.id if employee else False
        is_reviewer = rec.reviewer_id.id == employee.id if employee else False

        if not (is_aa or is_fa or is_reviewer):
            return {'error': 'Not authorised to rate.'}

        # -------------------------
        # Model Mapping
        # -------------------------
        model_map = {
            'kra': 'kra.section.line',
            'lc': 'lc.section.line',
            'fc': 'fc.section.line',
            'training': 'training.section.line',
            'current_assessment': 'current.assessment.section.line',
            'potential_assessment': 'potential.assessment.section.line',
        }
        if not lines:
            return {'success': True, 'message': 'Nothing to process.'}

        # -------------------------
        # Process Lines
        # -------------------------
        _logger.info(f"cxreated lines{lines}")
        for ld in lines:

            model_key = section if section else ld.get('model')
            if not model_key or model_key not in model_map:
                continue

            Model = request.env[model_map[model_key]].sudo()

            # =========================================================
            # TRAINING SECTION (CREATE OR UPDATE)
            # =========================================================
            if model_key == 'training':
                vals = {
                    'training_section_id': rec.id,
                    'name': ld.get('name', ''),
                    'comments': ld.get('comments', ''),
                }
                line_id = ld.get('id')
                if line_id:
                    line = Model.browse(line_id)
                    if line.exists():
                        line.write(vals)
                    else:
                        Model.create(vals)
                else:
                    Model.create(vals)

                continue

            # =========================================================
            # OTHER SECTIONS (UPDATE ONLY)
            # =========================================================
            line_id = ld.get('id')
            if not line_id:
                continue

            line = Model.browse(line_id)
            if not line.exists():
                continue

            vals = {} 
            if is_aa and 'administrative_supervisor_rating' in ld:
                vals['administrative_supervisor_rating'] = int(ld['administrative_supervisor_rating'])

            if is_fa and 'functional_supervisor_rating' in ld:
                vals['functional_supervisor_rating'] = int(ld['functional_supervisor_rating'])

            if is_reviewer and 'reviewer_rating' in ld:
                vals['reviewer_rating'] = int(ld['reviewer_rating'])

            if model_key in ('current_assessment', 'potential_assessment') and (is_aa or is_fa):
                vals['assessment_type'] = ld.get(
                    'assessment_type',
                    line.assessment_type
                )
            if vals:
                if model_key in ('current_assessment', 'potential_assessment'):
                    _logger.info(f"{line.id} {vals} My assessment lines {ld} ")
                line.write(vals)
 
        return {'success': True, 'message': 'Ratings saved successfully.'}
    # ─── API: Submit AA rating ────────────────────────────────────────────────

    @http.route('/pms/api/submit-aa-rating', type='json', auth='user', methods=['POST'])
    def submit_aa_rating(self, appraisal_id=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or rec.administrative_supervisor_id.id != employee.id:
            return {'error': 'Access denied.'}
        if rec.state != 'admin_rating':
            return {'error': 'Not in Admin Rating stage.'}
        try:
            rec.button_admin_supervisor_rating()
        except AttributeError:
            rec.write({'state': 'functional_rating'})
        return {'success': True, 'message': 'AA rating submitted to FA.'}

    # ─── API: Submit FA rating ────────────────────────────────────────────────

    @http.route('/pms/api/submit-fa-rating', type='json', auth='user', methods=['POST'])
    def submit_fa_rating(self, appraisal_id=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or rec.manager_id.id != employee.id:
            return {'error': 'Access denied.'}
        if rec.state != 'functional_rating':
            return {'error': 'Not in Functional Rating stage.'}
        try:
            rec.button_functional_manager_rating()
        except AttributeError:
            rec.write({'state': 'reviewer_rating'})
        return {'success': True, 'message': 'FA rating submitted to Reviewer.'}

    @http.route('/pms/api/return-rating', type='json', auth='user', methods=['POST'])
    def return_rating(self, appraisal_id=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or rec.manager_id.id != employee.id:
            return {'error': 'Access denied.'}
        rec.return_appraisal_directly()
        return {'success': True, 'message': 'Appraisal returned successfully'}

    # ─── API: Submit Reviewer rating ──────────────────────────────────────────

    @http.route('/pms/api/submit-reviewer-rating', type='json', auth='user', methods=['POST'])
    def submit_reviewer_rating(self, appraisal_id=None, **kw):
        employee = self._get_employee()
        rec = request.env['pms.appraisee'].sudo().browse(appraisal_id)
        if not rec.exists() or rec.reviewer_id.id != employee.id:
            return {'error': 'Access denied.'}
        if rec.state != 'reviewer_rating':
            return {'error': 'Not in Reviewer stage.'}
        try:
            rec.button_reviewer_manager_rating()
        except AttributeError:
            rec.write({'state': 'wating_approval'})
        return {'success': True, 'message': 'Reviewer rating submitted to HR.'}

    # ─── API: Who am I (session info for frontend) ───────────────────────────

    @http.route('/pms/api/whoami', type='json', auth='user', methods=['POST'])
    def whoami(self, **kw):
        employee = self._get_employee()
        user = request.env.user
        return {
            'user_id': user.id,
            'user_name': user.name,
            'employee_id': employee.id if employee else False,
            'employee_name': employee.name if employee else '',
        }

    # ─── API: Pending approvals ───────────────────────────────────────────────

    @http.route('/pms/api/pending-approvals', type='json', auth='user', methods=['POST'])
    def pending_approvals(self, **kw):
        employee = self._get_employee()
        if not employee:
            return {'error': 'No employee record found.'}

        def fmt(recs, action_type):
            return [{'id': r.id, 'name': r.name, 'employee_name': r.employee_id.name,
                     'type_of_pms': r.type_of_pms, 'state': r.state, 'action_type': action_type,
                     'submitted_date': r.submitted_date.strftime('%Y-%m-%d %H:%M') if r.submitted_date else ''}
                    for r in recs]

        Appr = request.env['pms.appraisee'].sudo()
        pending = (
            fmt(Appr.search([('manager_id', '=', employee.id), ('state', '=', 'gs_fa')]), 'approve_gs') +
            fmt(Appr.search([('manager_id', '=', employee.id), ('state', '=', 'hyr_draft')]), 'hyr_rating') +
            fmt(Appr.search([('manager_id', '=', employee.id), ('state', '=', 'hyr_functional_rating')]), 'hyr_submit') +
            fmt(Appr.search([('administrative_supervisor_id', '=', employee.id), ('state', '=', 'admin_rating')]), 'aa_rating') +
            fmt(Appr.search([('manager_id', '=', employee.id), ('state', '=', 'functional_rating')]), 'fa_rating') +
            fmt(Appr.search([('reviewer_id', '=', employee.id), ('state', '=', 'reviewer_rating')]), 'reviewer_rating')
        )
        return {'pending': pending}

    # ─── API: Reporting meta (filter dropdown data) ───────────────────────────

    @http.route('/pms/api/reporting-meta', type='json', auth='user', methods=['POST'])
    def reporting_meta(self, **kw):
        """Return data to populate filter dropdowns — years, managers, employees, departments."""
        employee = self._get_employee()
        # Only managers / HR admins see all; regular employees see their own scope
        is_manager = bool(request.env['pms.appraisee'].sudo().search([
            ('manager_id', '=', employee.id)], limit=1)) if employee else False
        is_admin_sup = bool(request.env['pms.appraisee'].sudo().search([
            ('administrative_supervisor_id', '=', employee.id)], limit=1)) if employee else False

        # Years
        try:
            year_recs = request.env['pms.year'].sudo().search([], order='name desc')
            years = [{'id': y.id, 'name': y.name} for y in year_recs]
        except Exception:
            years = []

        # Get visible appraisals for this user to build dropdown options
        domain = []
        if not (is_manager or is_admin_sup):
            if employee:
                domain = [('employee_id', '=', employee.id)]
        recs = request.env['pms.appraisee'].sudo().search(domain)

        managers = {}
        employees = {}
        departments = {}
        for r in recs:
            if r.manager_id:
                managers[r.manager_id.id] = r.manager_id.name
            if r.employee_id:
                employees[r.employee_id.id] = r.employee_id.name
            if r.department_id:
                departments[r.department_id.id] = r.department_id.name

        return {
            'years':       years,
            'managers':    [{'id': k, 'name': v} for k, v in managers.items()],
            'employees':   [{'id': k, 'name': v} for k, v in employees.items()],
            'departments': [{'id': k, 'name': v} for k, v in departments.items()],
        }

    # ─── API: Reporting data ──────────────────────────────────────────────────

    @http.route('/pms/api/reporting-data', type='json', auth='user', methods=['POST'])
    def reporting_data(self, filters=None, **kw):
        """Return appraisal records with all score fields for the reporting page."""
        filters = filters or {}
        employee = self._get_employee()

        # Determine scope: managers/AA see all their reportees; employees see own
        is_manager = bool(request.env['pms.appraisee'].sudo().search([
            ('manager_id', '=', employee.id)], limit=1)) if employee else False
        is_admin_sup = bool(request.env['pms.appraisee'].sudo().search([
            ('administrative_supervisor_id', '=', employee.id)], limit=1)) if employee else False

        domain = []
        if not (is_manager or is_admin_sup):
            if employee:
                domain = [('employee_id', '=', employee.id)]

        # Apply filters from request
        if filters.get('year'):
            domain.append(('pms_year_id', '=', int(filters['year'])))
        if filters.get('type_of_pms'):
            domain.append(('type_of_pms', '=', filters['type_of_pms']))
        if filters.get('state'):
            domain.append(('state', '=', filters['state']))
        if filters.get('manager_id'):
            domain.append(('manager_id', '=', int(filters['manager_id'])))
        if filters.get('employee_id'):
            domain.append(('employee_id', '=', int(filters['employee_id'])))
        if filters.get('department_id'):
            domain.append(('department_id', '=', int(filters['department_id'])))

        recs = request.env['pms.appraisee'].sudo().search(domain, order='id desc')

        records = []
        for r in recs:
            # Count section lines
            kra_count = len(r.kra_section_line_ids) if hasattr(r, 'kra_section_line_ids') else 0
            lc_count  = len(r.lc_section_line_ids)  if hasattr(r, 'lc_section_line_ids')  else 0
            fc_count  = len(r.fc_section_line_ids)   if hasattr(r, 'fc_section_line_ids')  else 0

            # Period / year label
            try:
                period = r.pms_year_id.name if r.pms_year_id else r.name
            except Exception:
                period = r.name

            records.append({
                'id':                       r.id,
                'name':                     r.name,
                'period':                   period,
                'employee_id':              r.employee_id.id if r.employee_id else False,
                'employee_name':            r.employee_id.name if r.employee_id else '–',
                'department_id':            r.department_id.id if r.department_id else False,
                'department':               r.department_id.name if r.department_id else '–',
                'manager_id':               r.manager_id.id if r.manager_id else False,
                'manager_name':             r.manager_id.name if r.manager_id else '–',
                'pms_year_id':              r.pms_year_id.id if hasattr(r, 'pms_year_id') and r.pms_year_id else False,
                'type_of_pms':              r.type_of_pms,
                'state':                    r.state,
                'kra_count':                kra_count,
                'lc_count':                 lc_count,
                'fc_count':                 fc_count,
                # Score fields — use getattr with safe fallback
                'final_kra_score':          float(getattr(r, 'final_kra_score', 0) or 0),
                'final_lc_score':           float(getattr(r, 'final_lc_score',  0) or 0),
                'final_fc_score':           float(getattr(r, 'final_fc_score',  0) or 0),
                'current_assessment_score': float(getattr(r, 'current_assessment_score', 0) or 0),
                'potential_assessment_score': float(getattr(r, 'potential_assessment_score', 0) or 0),
                'overall_score':            float(getattr(r, 'overall_score', 0) or 0),
                'submitted_date':           r.submitted_date.strftime('%Y-%m-%d') if r.submitted_date else '',
            })

        return {'records': records, 'total': len(records)}

    # ══════════════════════════════════════════════════════════
    #  WORKFORCE PLANNING API ROUTES
    # ══════════════════════════════════════════════════════════

    def _wfp_model(self):
        """Return the workforce planning model, or None if not installed."""
        try:
            return request.env['hr.workforce.planning'].sudo()
        except Exception:
            return None

    @http.route('/pms/api/workforce-data', type='json', auth='user', methods=['POST'])
    def workforce_data(self, **kw):
        """Return all workforce planning records + overview KPIs aggregated from data."""
        WFP = self._wfp_model()
        records_out = []
        overview = {}

        if WFP is not None:
            recs = WFP.search([], order='id desc')
            for r in recs:
                records_out.append({
                    'id': r.id,
                    'record_type': getattr(r, 'record_type', ''),
                    'title': getattr(r, 'title', r.name if hasattr(r, 'name') else ''),
                    'department': getattr(r, 'department_id', False) and r.department_id.name or getattr(r, 'department', ''),
                    'period': getattr(r, 'period', ''),
                    'priority': getattr(r, 'priority', 'medium'),
                    'status': getattr(r, 'status', 'draft'),
                    'created_by': r.create_uid.name if r.create_uid else '',
                    'create_date': r.create_date.strftime('%Y-%m-%d') if r.create_date else '',
                    'type_data': self._extract_wfp_type_data(r),
                })

            # Aggregate overview KPIs from performance records
            perf_recs = [r for r in records_out if r['record_type'] == 'performance']
            budget_recs = [r for r in records_out if r['record_type'] == 'budget']
            demand_recs = [r for r in records_out if r['record_type'] == 'demand']
            supply_recs = [r for r in records_out if r['record_type'] == 'supply']

            def avg_field(recs_list, field):
                vals = [float(r['type_data'].get(field) or 0) for r in recs_list if r['type_data'].get(field)]
                return round(sum(vals)/len(vals), 1) if vals else None

            overview['attrition_rate']   = avg_field(perf_recs, 'attrition')
            overview['absenteeism_rate'] = avg_field(perf_recs, 'absenteeism')
            overview['utilization']      = avg_field(perf_recs, 'utilization')
            overview['efficiency']       = avg_field(perf_recs, 'efficiency')
            overview['output_score']     = avg_field(perf_recs, 'output_score')

            # Headcount from latest supply record
            if supply_recs:
                latest_supply = supply_recs[0]['type_data']
                overview['total_headcount'] = latest_supply.get('headcount')
                overview['pct_under30']     = latest_supply.get('pct_under30')
                overview['pct_3040']        = latest_supply.get('pct_3050')  # approximate
                overview['pct_over50']      = latest_supply.get('pct_over50')

            # Budget totals from latest budget record
            if budget_recs:
                bd = budget_recs[0]['type_data']
                overview['payroll_budget']  = bd.get('payroll_budget', 0)
                overview['payroll_actual']  = bd.get('payroll_actual', 0)
                overview['benefits_budget'] = bd.get('benefits_budget', 0)
                overview['benefits_actual'] = bd.get('benefits_actual', 0)
                overview['training_budget'] = bd.get('training_budget', 0)
                overview['training_actual'] = bd.get('training_actual', 0)
                overview['overtime_budget'] = bd.get('overtime_budget', 0)
                overview['overtime_actual'] = bd.get('overtime_actual', 0)

            # Open vacancies from gap records
            gap_recs = [r for r in records_out if r['record_type'] == 'gap']
            total_gap = sum(
                max(0, int(r['type_data'].get('demand', 0) or 0) - int(r['type_data'].get('supply', 0) or 0))
                for r in gap_recs
            )
            overview['open_vacancies'] = total_gap if total_gap > 0 else None

            # Avg cost per hire from recruitment records
            rec_recs = [r for r in records_out if r['record_type'] == 'recruitment']
            if rec_recs:
                costs = [float(r['type_data'].get('cost_per_hire') or 0) for r in rec_recs if r['type_data'].get('cost_per_hire')]
                if costs:
                    overview['avg_cost_per_hire'] = round(sum(costs)/len(costs), 0)

        else:
            # No Odoo model — return empty with explanation
            overview['_note'] = 'hr.workforce.planning model not found. Install the module or use Create Record to add data.'

        return {'records': records_out, 'overview': overview}

    def _extract_wfp_type_data(self, r):
        """Extract type-specific data fields from the Odoo model record."""
        t = getattr(r, 'record_type', '')
        data = {}
        # Map common fields that might exist on the model
        field_map = {
            'demand':      ['growth_driver','headcount_needed','current_headcount','budget_projection','projects','tech_factor','notes'],
            'supply':      ['headcount','skills','avg_experience','avg_age','pct_under30','pct_3050','pct_over50','pct_high_perf','notes'],
            'gap':         ['role','demand','supply','gap_type','skill_shortages','criticality','notes'],
            'recruitment': ['role','position_count','strategy','target_date','cost_per_hire','total_budget','notes'],
            'training':    ['program','competency','employee_count','training_type','budget','target_date','notes'],
            'succession':  ['role','incumbent','successor_primary','successor_secondary','readiness','role_criticality','notes'],
            'budget':      ['payroll_budget','payroll_actual','benefits_budget','benefits_actual','training_budget','training_actual','overtime_budget','overtime_actual','notes'],
            'performance': ['utilization','absenteeism','attrition','output_score','efficiency','overtime_hours','notes'],
            'risk':        ['risk_type','affected_role','risk_level','employees_at_risk','probability','estimated_impact','notes'],
        }
        fields = field_map.get(t, [])
        for f in fields:
            try:
                val = getattr(r, f, None)
                if val is not None and val is not False:
                    data[f] = str(val) if not isinstance(val, (int, float, bool)) else val
            except Exception:
                pass
        # Fallback: try getting a JSON/serialized field
        try:
            if hasattr(r, 'type_data') and r.type_data:
                import json
                parsed = json.loads(r.type_data)
                data.update(parsed)
        except Exception:
            pass
        return data

    @http.route('/pms/api/workforce-save', type='json', auth='user', methods=['POST'])
    def workforce_save(self, record_type=None, title=None, department=None, period=None,
                       priority='medium', status='draft', type_data=None, record_id=None, **kw):
        """Create or update a workforce planning record."""
        import json
        if not record_type or not title:
            return {'error': 'Record type and title are required.'}

        WFP = self._wfp_model()
        vals = {
            'record_type': record_type,
            'department': department or '',
            'period': period or '',
            'priority': priority,
            'status': status,
        }

        # Try to set title (could be 'name' or 'title' depending on model)
        if hasattr(WFP, '_fields') and 'title' in WFP._fields:
            vals['title'] = title
        else:
            vals['name'] = title

        # Serialize type_data as JSON if the model supports it
        if type_data:
            try:
                vals['type_data'] = json.dumps(type_data)
            except Exception:
                pass
            # Also try to set individual fields if they exist on the model
            if WFP is not None and hasattr(WFP, '_fields'):
                for k, v in (type_data or {}).items():
                    if k in WFP._fields:
                        try:
                            vals[k] = v
                        except Exception:
                            pass

        try:
            if record_id:
                rec = WFP.browse(int(record_id))
                if not rec.exists():
                    return {'error': 'Record not found.'}
                rec.write(vals)
                return {'success': True, 'message': 'Record updated successfully.', 'id': rec.id}
            else:
                rec = WFP.create(vals)
                return {'success': True, 'message': 'Workforce planning record created.', 'id': rec.id}
        except Exception as e:
            # If model doesn't exist, still return success and let frontend handle in-memory
            return {'error': f'Could not save to database: {str(e)}. Ensure hr.workforce.planning model is installed.'}

    @http.route('/pms/api/workforce-delete', type='json', auth='user', methods=['POST'])
    def workforce_delete(self, record_id=None, **kw):
        """Delete a workforce planning record."""
        if not record_id:
            return {'error': 'Record ID required.'}
        WFP = self._wfp_model()
        if WFP is None:
            return {'error': 'Workforce planning model not available.'}
        try:
            rec = WFP.browse(int(record_id))
            if not rec.exists():
                return {'error': 'Record not found.'}
            rec.unlink()
            return {'success': True, 'message': 'Record deleted successfully.'}
        except Exception as e:
            return {'error': str(e)}