
from odoo import http, fields
from odoo.http import request, Response
import json
import logging
import traceback
from odoo.modules.module import get_resource_path
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

from odoo.tools import file_path
from odoo.modules.module import get_resource_path

class PortalOtherApps(http.Controller):
    @http.route('/payroll-list', type='http', auth='user')
    def show_payroll_list(self, **kw):
        """Display memo list view"""
        file_path = get_resource_path(
            'payroll_portal',
            'static/html',
            'payroll_list.html'
        )
        
        if not file_path:
            return "HTML file not found."
        
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
        
        return request.make_response(
            html,
            headers=[('Content-Type', 'text/html')]
        )
    
    @http.route('/payroll/api/list', type='http', auth='user', methods=['GET'], csrf=False)
    def get_payroll_list(self, **kwargs):
        """
        Get paginated list of memos with filters
        Query params:
            - page: page number (default 1)
            - limit: records per page (default 20)
            - search: search term
            - filter: all, my_approvals, to_approve, to_submit
        """
        try:
            # Get parameters
            page = int(kwargs.get('page', 1))
            limit = int(kwargs.get('limit', 20))
            search = kwargs.get('search', '').strip()
            filter_type = kwargs.get('filter', 'all')
            
            offset = (page - 1) * limit
            
            # Base domain
            domain = []
            
            # Apply filters
            current_user = request.env.user
            top_user = request.env.is_admin() or request.env.user.has_group('hr_payroll.group_hr_payroll_manager')
            
            if filter_type == 'my_approvals':
                # Records where I'm the approver and state is pending approval
                if top_user: 
                    domain = []
                else:
                    domain = [
                        '|', ('employee_id.user_id', '=', current_user.id),
                        ('create_uid', '=', current_user.id),
                    ]
                
            elif filter_type == 'to_approve':
                # All records pending approval
                if top_user: 
                    domain = [('state', 'in', ['done', 'paid'])]
                else:
                    domain = [
                        '|', ('employee_id.user_id', '=', current_user.id),
                        ('create_uid', '=', current_user.id),
                        ('state', 'in', ['verify', 'done', 'paid'])
                    ]
                
            elif filter_type == 'to_submit':
                # All records in submit state
                
                if top_user: 
                    domain = [('state', '=', 'verify')]
                else:
                    domain = [
                        '|', ('employee_id.user_id', '=', current_user.id),
                        ('create_uid', '=', current_user.id),
                        ('state', 'in', ['verify'])
                    ]
                
            elif filter_type == 'all':
                # All records for current user (as initiator or approver)
                if top_user:
                    domain = []
                else:
                    domain = [
                        '|', ('employee_id.user_id', '=', current_user.id),
                        ('create_uid', '=', current_user.id),
                    ]
            
            # Add search filter
            if search:
                search_domain = [
                    '|', '|',
                    ('number', 'ilike', search),
                    ('name', 'ilike', search),
                    ('employee_id.name', 'ilike', search),
                ]
                domain = ['&'] + domain + search_domain if domain else search_domain
            
            # Get records
            payslip = request.env['hr.payslip'].sudo()
            payslips = payslip.search(domain, limit=limit, offset=offset, order='id desc')
            total_count = payslip.search_count(domain)
            
            # Format data
            payslip_list = []
            for payslip in payslips:
                payslip_list.append({
                    'id': payslip.id,
                    'number': payslip.number or payslip.name or 'Untitled',
                    'employee': payslip.employee_id.name or 'N/A',
                    'structure': payslip.struct_id.name or 'N/A',
                    'date_from': payslip.date_from.strftime('%m/%d/%Y %H:%M') if payslip.date_from else '',
                    'date_to': payslip.date_to.strftime('%m/%d/%Y %H:%M') if payslip.date_to else '',
                    'normal_wage': payslip.normal_wage if payslip.normal_wage else 'N/A',
                    'basic_wage': sum([py.total for py in payslip.line_ids.filtered(lambda ln: ln.category_id.code in ['BASIC', 'basic', 'Basic'])]),
                    'net_wage':sum([py.total for py in payslip.line_ids.filtered(lambda ln: ln.category_id.code in ['NET', 'net', 'Net'])]),
                    'gross_wage': sum([py.total for py in payslip.line_ids.filtered(lambda ln: ln.category_id.code in ['GROSS', 'gross', 'Gross'])]),
                    'deductions': sum([py.total for py in payslip.line_ids.filtered(lambda ln: ln.category_id.code in ['DEDUCTIONS', 'TAX', 'deductions', 'Deductions', 'deduction', 'Deduction'])]),
                    'state': payslip.state,
                })
            
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': payslip_list,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total_count,
                        'pages': (total_count + limit - 1) // limit,
                        'has_next': (page * limit) < total_count,
                        'has_prev': page > 1
                    }
                }),
                headers=[('Content-Type', 'application/json')]
            )
            
        except Exception as e:
            _logger.error(f"Error fetching payslip list: {str(e)}")
            _logger.error(traceback.format_exc())
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': str(e)
                }),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
    

    @http.route('/payroll/api/detail/<int:payslip_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_payslip_detail(self, payslip_id, **kwargs):
        """
        Return full detail for a single payslip, including line items.
        Used by the modal view and single-payslip print.
        """
        try:
            current_user = request.env.user
            is_admin     = request.env.is_admin() or request.env.user.has_group('hr_payroll.group_hr_payroll_manager')
 
            payslip = request.env['hr.payslip'].sudo().browse(payslip_id)
 
            if not payslip.exists():
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Payslip not found'}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
 
            # Access control – non-admins may only see their own payslips
            if not is_admin:
                allowed = (
                    payslip.employee_id.user_id.id == current_user.id or
                    payslip.create_uid.id == current_user.id
                )
                if not allowed:
                    return request.make_response(
                        json.dumps({'status': 'error', 'message': 'Access denied'}),
                        headers=[('Content-Type', 'application/json')],
                        status=403
                    )
 
            # Build payslip lines
            lines = []
            for line in payslip.line_ids:
                lines.append({
                    'name':  line.name or '',
                    'code':  line.code or '',
                    'total': line.total or 0.0,
                    'category': line.category_id.name or '',
                })
 
            data = {
                'id':            payslip.id,
                'number':        payslip.number or payslip.name or 'Untitled',
                'employee':      payslip.employee_id.name or 'N/A',
                'employee_code': payslip.employee_id.barcode or payslip.employee_id.identification_id or 'N/A',
                'department':    payslip.employee_id.department_id.name if payslip.employee_id.department_id else 'N/A',
                'job_position':  payslip.employee_id.job_id.name if payslip.employee_id.job_id else 'N/A',
                'structure':     payslip.struct_id.name if payslip.struct_id else 'N/A',
                'company':       payslip.company_id.name if payslip.company_id else 'N/A',
                'date_from':     payslip.date_from.strftime('%m/%d/%Y') if payslip.date_from else '',
                'date_to':       payslip.date_to.strftime('%m/%d/%Y')   if payslip.date_to   else '',
                'state':         payslip.state,
                'stage':         payslip.state,          # map to human label in frontend
                'normal_wage':   payslip.normal_wage or 0.0,
                'basic_wage':    sum(l.total for l in payslip.line_ids if l.category_id.code in ['BASIC', 'basic', 'Basic']),
                'net_wage':      sum(l.total for l in payslip.line_ids if l.category_id.code in ['NET',   'net',   'Net']),
                'gross_wage':    sum(l.total for l in payslip.line_ids if l.category_id.code in ['GROSS', 'gross', 'Gross']),
                'deductions':    sum(l.total for l in payslip.line_ids if l.category_id.code in ['DEDUCTIONS', 'TAX', 'deductions', 'Deductions', 'deduction', 'Deduction']),
                'lines':         lines,
            }
 
            return request.make_response(
                json.dumps({'status': 'success', 'data': data}),
                headers=[('Content-Type', 'application/json')]
            )
 
        except Exception as e:
            _logger.error(f"Error fetching payslip detail {payslip_id}: {str(e)}")
            _logger.error(traceback.format_exc())
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
 
 
    @http.route('/payroll/api/company', type='http', auth='user', methods=['GET'], csrf=False)
    def get_company_info(self, **kwargs):
        """
        Return the current user's company name and logo URL.
        Used as the header in both the modal view and printed payslips.
        """
        try:
            company    = request.env.company
            logo_url   = None
 
            if company.logo:
                # The standard Odoo web route serves the binary attachment
                logo_url = f'/web/image/res.company/{company.id}/logo'
 
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'data': {
                        'name':     company.name or 'Organisation',
                        'logo_url': logo_url,
                        'street':   company.street  or '',
                        'city':     company.city    or '',
                        'phone':    company.phone   or '',
                        'email':    company.email   or '',
                    }
                }),
                headers=[('Content-Type', 'application/json')]
            )
 
        except Exception as e:
            _logger.error(f"Error fetching company info: {str(e)}")
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
                