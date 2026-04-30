
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
        @http.route('/inventory-list', type='http', auth='user')
        def show_inventory_list(self, **kw):
            """Display memo list view"""
            file_path = get_resource_path(
                'portal_request',
                'static/html',
                'inventory.html'
            )
            
            if not file_path:
                return "HTML file not found."
            
            with open(file_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            return request.make_response(
                html,
                headers=[('Content-Type', 'text/html')]
            )
        
        
        @http.route('/inventory/api/list', type='http', auth='user', methods=['GET'], csrf=False)
        def get_inventory_list(self, **kwargs):
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
                            ('create_uid', '=', current_user.id),
                        ]
                    
                elif filter_type == 'to_approve':
                    # All records pending approval
                    if top_user: 
                        domain = []
                    else:
                        domain = [
                            ('create_uid', '=', current_user.id),
                        ]
                    
                elif filter_type == 'to_submit':
                    # All records in submit state
                    
                    if top_user: 
                        domain = []
                    else:
                        domain = [
                            ('create_uid', '=', current_user.id),
                        ]
                    
                elif filter_type == 'all':
                    # All records for current user (as initiator or approver)
                    if top_user:
                        domain = []
                    else:
                        domain = [
                            ('create_uid', '=', current_user.id),
                        ]
                
                # Add search filter
                if search:
                    search_domain = [
                        '|', '|',
                        ('product_id.default_code', 'ilike', search),
                        ('product_id.name', 'ilike', search),
                        ('location_id.name', 'ilike', search),
                    ]
                    domain = ['&'] + domain + search_domain if domain else search_domain
                
                # Get records
                stock_quant = request.env['stock.quant'].sudo()
                stock_quants = stock_quant.search(domain, limit=limit, offset=offset, order='id desc')
                total_count = stock_quant.search_count(domain)
                
                # Format data
                record_list = []
                for rec in stock_quants:
                    record_list.append({
                        'id': rec.id,
                        'location': rec.location_id.name or rec.name or 'Untitled',
                        'location_code': rec.location_id.wh_code or 'N/A',
                        'category': rec.product_categ_id.name or 'N/A',
                        'product_id': rec.sudo().product_id.name or 'N/A',
                        'lot_number': rec.lot_id.name or 'N/A',
                        'product_code': rec.product_id.default_code or 'N/A',
                        'qty_hand': rec.quantity or rec.inventory_quantity_auto_apply or 0,
                        'reserved': rec.reserved_quantity if rec.reserved_quantity else 0,
                        'cost_price': rec.product_id.standard_price if rec.product_id else 0,
                        'sale_price': rec.product_id.lst_price if rec.product_id else 0,
                        'company': rec.company_id.name,
                        'state': 'Completed',
                        'value': rec.value,
                    })
                
                return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data': record_list,
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
                _logger.error(f"Error fetching records list: {str(e)}")
                _logger.error(traceback.format_exc())
                return request.make_response(
                    json.dumps({
                        'status': 'error',
                        'message': str(e)
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )