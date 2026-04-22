# -*- coding: utf-8 -*-
import base64
import json
import logging
import ast 
import random
from multiprocessing.spawn import prepare
import urllib.parse
from odoo import http, fields, _
from odoo.exceptions import ValidationError
from odoo.tools import consteq, plaintext2html
from odoo.http import request
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
import odoo
import odoo.addons.web.controllers.home as main
from odoo.addons.web.controllers.utils import ensure_db, _get_login_redirect_url, is_user_internal
from odoo.tools.translate import _
from odoo.tools.misc import format_date


_logger = logging.getLogger(__name__)
# Shared parameters for all login/signup flows
SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'message', 'error', 'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
                          'password', 'confirm_password', 'city', 'country_id', 'lang', 'signup_email'}
LOGIN_SUCCESSFUL_PARAMS = set()

def get_url(id):
    base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
    base_url += "/my/request/view/%s" % (id)
    return "<a href={}> </b>Click<a/>. ".format(base_url)

def get_model_url(id, model):
    base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
    internal_path = "/my/request/view/%s" % (id) # "/web#id={}&model={}&view_type=form".format(id, model)
    internal_url = internal_path #  base_url + internal_path
    return internal_url

def format_to_odoo_date(date_str: str) -> str:
    """Formats date format mm/dd/yyyy eg.07/01/1988 to %Y-%m-%d
        OR  date format yyyy/mm/dd to  %Y-%m-%d
    Args:
        date (str): date string to be formated

    Returns:
        str: The formated date
    """
    if not date_str:
        return

    data = date_str.split('/')
    if len(data) > 2 and len(data[0]) ==2: #format mm/dd/yyyy
        try:
            mm, dd, yy = int(data[0]), int(data[1]), data[2]
            if mm > 12: #eg 21/04/2021" then reformat to 04/21/2021"
                dd, mm = mm, dd
            if mm > 12 or dd > 31 or len(yy) != 4:
                return
            return f"{yy}-{mm}-{dd}"
        except Exception:
            return
        
class Home(main.Home):
    
    def _login_redirect(self, uid, redirect=None):
        '''we did this so that every user will be directed to portal page'''
        return '/' # _get_login_redirect_url(uid, redirect)
    
    # @http.route('/', type='http', auth="none")
    # def index(self, s_action=None, db=None, **kw):
    # 	# if request.db and request.session.uid and not is_user_internal(request.session.uid):
    # 	# 	# return request.redirect_query('/web/login_successful', query=request.params)
    # 	# 	return request.redirect('/')
    # 	# return request.redirect_query('/web', query=request.params)
    # 	# return request.redirect('/my/requests')
    # 	return request.redirect('/')
        
    # @http.route('/web/login', type='http', auth="none")
    # def web_login(self, redirect=None, **kw):
    # 	ensure_db()
    # 	request.params['login_success'] = False
    # 	if request.httprequest.method == 'GET' and redirect and request.session.uid:
    # 		return request.redirect(redirect)
    # 		# return request.redirect('/')
        


    # 	# simulate hybrid auth=user/auth=public, despite using auth=none to be able
    # 	# to redirect users when no db is selected - cfr ensure_db()
    # 	if request.env.uid is None:
    # 		if request.session.uid is None:
    # 			# no user -> auth=public with specific website public user
    # 			request.env["ir.http"]._auth_method_public()
    # 		else:
    # 			# auth=user
    # 			request.update_env(user=request.session.uid)

    # 	values = {k: v for k, v in request.params.items() if k in SIGN_UP_REQUEST_PARAMS}
    # 	try:
    # 		values['databases'] = http.db_list()
    # 	except odoo.exceptions.AccessDenied:
    # 		values['databases'] = None

    # 	if request.httprequest.method == 'POST':
    # 		try:
    # 			uid = request.session.authenticate(request.db, request.params['login'], request.params['password'])
    # 			request.params['login_success'] = True
    # 			# return request.redirect(self._login_redirect(uid, redirect=redirect))
    # 			return request.redirect('/')
    # 		except odoo.exceptions.AccessDenied as e:
    # 			if e.args == odoo.exceptions.AccessDenied().args:
    # 				values['error'] = _("Wrong login/password")
    # 			else:
    # 				values['error'] = e.args[0]
    # 	else:
    # 		if 'error' in request.params and request.params.get('error') == 'access':
    # 			values['error'] = _('Only employees can access this database. Please contact the administrator.')

    # 	if 'login' not in values and request.session.get('auth_login'):
    # 		values['login'] = request.session.get('auth_login')

    # 	if not odoo.tools.config['list_db']:
    # 		values['disable_database_manager'] = True

    # 	response = request.render('web.login', values)
    # 	response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # 	response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
    # 	return response
    
class PortalRequest(http.Controller):
    
    
    @http.route(["/portal-request"], type='http', auth='user', website=True, website_published=True)
    def portal_request(self, **kw):
        """Request portal for employee / portal users
        """
        
        memo_type_key = kw.get('memo_type_key', False) or kw.get('memo_type', False)
        selected_district_id = kw.get('district_id', False)
        
        _logger.info(f"=== Portal Request Form (Create New) ===")
        _logger.info(f"URL params: {kw}")
        _logger.info(f"Extracted memo_type_key: {memo_type_key}")
        
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        user_branch = user.branch_id
        
        allowed_branches_ids = set()
        if user.branch_id:
            allowed_branches_ids.add(user.branch_id.id)
        if user.branch_ids:
            allowed_branches_ids.update(user.branch_ids.ids)
            
        allowed_branches_ids = list(allowed_branches_ids) if allowed_branches_ids else []
        
        if allowed_branches_ids:
            if not selected_district_id or int(selected_district_id) not in allowed_branches_ids:
                selected_district_id = user_branch.id if user_branch else (allowed_branches_ids[0] if allowed_branches_ids else False)
            else:
                selected_district_id = int(selected_district_id)
        else:
            selected_district_id = False
            _logger.warning(f"User {user.name} has no branch configured")
        
        memo_configs = request.env['memo.model'].sudo().get_user_configs()
        source_location_data_ids = request.env['stock.location'].sudo().search(
            [('usage', '=', 'internal')]
        )
        destination_location_data_ids = request.env['stock.location'].sudo().search(
            [
            ('usage', '=', 'internal'),
            ('company_id.id', 'in', [request.env.user.company_id.id] + request.env.user.company_ids.ids),
            ]
        )
        
        # all_districts = request.env['multi.branch'].sudo().search([])
        
        _logger.info(f"Found {len(memo_configs)} configs for user: {memo_configs.mapped('name')}")
        
        # memo_type_ids = request.env['memo.type'].sudo().search([
        #     ('allow_for_publish', '=', True),
        #     ('active', '=', True)
        # ])
        memo_type_ids = memo_configs.mapped('memo_type')
        
        has_inter_district_configs = any(config.inter_district for config in memo_configs)
        _logger.info(f"Has inter-district configs: {has_inter_district_configs}")
        
        selected_memo_type_id = False
        if memo_type_key:
            # selected_memo_type = request.env['memo.type'].sudo().search([
            #     ('memo_key', '=', memo_type_key),
            #     ('allow_for_publish', '=', True),
            #     ('active', '=', True)
            # ], limit=1)
            selected_memo_type = memo_type_ids.filtered(lambda m: m.memo_key == memo_type_key)
            
            if selected_memo_type:
                selected_memo_type_id = selected_memo_type.id
                _logger.info(f"✓ Selected memo type: {selected_memo_type.name} (ID: {selected_memo_type_id}, Key: {memo_type_key})")
            else:
                _logger.warning(f"✗ No memo type found for key: {memo_type_key}")
        else:
            _logger.info("No memo_type_key provided in URL")
        
        vals = {
            "leave_type_ids": request.env["hr.leave.type"].sudo().search([
                ('company_id', '=', request.env.user.company_id.id)
            ]),
            "memo_key_ids": [{'id': 0, 'name': ''}],
            "source_location_data_ids": source_location_data_ids,
            "destination_location_data_ids": destination_location_data_ids,
            "memo_type_ids": memo_type_ids,
            "config_type_ids": memo_configs,
            # "all_districts": all_districts,
            "selected_memo_type_id": selected_memo_type_id,
            "preselected_memo_key": memo_type_key,
            # doform
            "user_id": request.env.user,
            "company_id": request.env.user.company_id,
            "currency_ids": request.env['res.currency'].search([('active', '=', True)]),
            # 
            "has_inter_district_configs": has_inter_district_configs,
            "user_branch": user_branch,
            "allowed_branches": request.env['multi.branch'].sudo().browse(allowed_branches_ids),
            "selected_district_id": selected_district_id,
            "show_branch_selector": len(allowed_branches_ids) > 1,
        }
        
        _logger.info(f"Rendering portal request with selected_memo_type_id: {selected_memo_type_id}")
        
        return request.render("portal_request.portal_request_template", vals)
    
    
    @http.route(['/reset/password'], type='http', website=True, auth="none", csrf=False)
    def reset_password(self, **post):
        data = json.loads(request.httprequest.data)
        employee_email = data.get('employee_email')
        staff_num = data.get('staff_number')
        _logger.info(f'Checking password reset ID No ...{data}')
        if staff_num:
            employee = request.env['hr.employee'].sudo().search(
            [
                ('employee_number', '=ilike', staff_num),
                ('active', '=', True)], limit=1)
            if employee:
                if not employee.user_id:
                    return json.dumps({
                        "status": False,
                        "message": "No related user found for this employee. Contact admin to linked you to a user", 
                    })
                _logger.info(f'MY EMPLOYEE EMAIL IS ...{employee_email} {employee.work_email}' )
                if employee.work_email == employee_email:
                    _logger.info(f'Employee email corresponds ...{employee_email} {employee.work_email}' )
                    employee.reset_employee_user_password()
                    employee.send_credential_notification([employee.id])
                    return json.dumps({
                        "status": True,
                        "message": "Your password reset was successful.. Please check your email", 
                    })
                elif employee_email in [employee.user_id.login]:
                    _logger.info(f'Employee user login corresponds ...{employee_email} {employee.user_id.login}' )
                    employee.reset_employee_user_password()
                    employee.send_credential_notification([employee.id])
                    return json.dumps({
                        "status": True,
                        "message": "Your password reset was successful.. Please check your email", 
                    })
                else:
                    # employee.reset_employee_user_password()
                    # employee.send_credential_notification()
                    # if employee.parent_id.work_email:
                        # '''send to manager's email'''
                        # return json.dumps({
                        #     "status": True,
                        #     "message": "Your password reset was successfully sent to your manager's email", 
                        # })
                    # else:
                    return json.dumps({
                            "status": False,
                            "message": "We could not find any related email to send your password. Contact admin to linked you to a user", 
                        })
            else:
                return json.dumps({
                    "status": False,
                    "message": "Employee with staff ID provided does not exist. Contact Admin", 
                })
        else:
            return json.dumps({
                "status": False,
                "message": "Please provide valid staff number. Contact Admin", 
            })
                
    @http.route(['/check_staffid'], type='json', website=True, auth="user", csrf=False)
    def check_staff_num(self, **post):
        """Check staff Identification No.
        Args:
            staff_num (str): The Id No to be validated
        Returns:
            dict: Response
        """
        staff_num = post.get('staff_num')
        _logger.info(f'Checking Staff ID No ...{staff_num}')
        user = request.env.user
        # ('user_id', '=', user.id)
        if staff_num:
            employee = request.env['hr.employee'].sudo().search(
            [
                ('employee_number', '=ilike', staff_num),
                ('active', '=', True),
                ('user_id', '=', user.id)], limit=1)
            if employee:
                if employee.leave_reliever:
                    return {
                        "status": False,
                        "data": {
                            'name': "",
                            'phone': "",
                            'work_email': "",
                        },
                        "message": " Are you back from Leave? if yes, kindly click the button 'I am Available Now'", 
                    }
                if employee.department_id:
                    
                    return {
                        "status": True,
                        "data": {
                            'name': employee.name or "",
                            'phone': employee.work_phone or employee.mobile_phone or "",
                            'work_email': employee.work_email or "",
                        },
                        "message": "", 
                    }
                else:
                    return {
                        "status": False,
                        "data": {
                            'name': "",
                            'phone': "",
                            'work_email': "",
                        },
                        "message": "Employee is not linked to any department. Contact Admin", 
                    }
            
            
            else:
                return {
                    "status": False,
                    "data": {
                        'name': "",
                        'phone': "",
                        'work_email': "",
                    },
                    "message": "Employee with staff ID provided does not exist. Contact Admin", 
                }
                
    # @http.route(['/get-stock-location'], type='http', website=True, auth="user", csrf=False)
    # def get_stock_location(self, **post):
    #     user = request.env.user
    #     location_type = post.get('location_type')
    #     is_inter_company = post.get('is_inter_company')
    #     selected_location_id = post.get('selected_source')
    #     selectedOption_id = post.get('selectedOption_id')
        
    #     location_data_ids =None
        
    #     processing_branch_id = post.get('processing_branch_id') 
        
    #     query = request.params.get('q', '') 
    #     is_inter_company2 = request.params.get('is_inter_company') 
    #     branch_ids = [user.branch_id.id] + user.branch_ids.ids
    #     company_ids = [request.env.user.company_id.id] + request.env.user.company_ids.ids
    #     stockObj = request.env['stock.location'].sudo()
    #     _logger.info(f"Search locations : params Selected location : {selected_location_id}, ==> is intercompany : {is_inter_company} SELECTED OPTION {selectedOption_id} - location type:  {location_type}, QUERY ==> {query}")
        
    #     is_inter_company = False if is_inter_company in [False, 'false', 'False', '0', 'Off'] else True 
        
    #     domain = [('usage', '=', 'internal')]
        
    #     if not is_inter_company:
            
    #         if location_type == "source":
    #             domain += [
    #                 # ('usage', '=', 'internal'),
    #                 ('branch_id.id', 'in', branch_ids),
    #                 ('company_id.id', 'in', company_ids),
    #                 # ('name', 'ilike', query)
    #                 ]
    #             if selected_location_id:
    #                 domain.append(('id', '!=', selected_location_id))
    #             location_data_ids = stockObj.search(domain)
                
    #         else:
    #             domain=[
    #                 ('usage', '=', 'internal'),
    #                 ('branch_id.id', 'in', branch_ids),
    #                 ('company_id.id', 'in', company_ids),
    #                 ('name', 'ilike', query)
    #                 ]
    #             if selected_location_id:
    #                 domain.append(('id', '!=', selected_location_id))
    #             location_data_ids = stockObj.search(domain)
    #     else:
    #         if location_type == "source":
    #             '''returns all locations if it is not interdistrict or intercompany'''
    #             if selectedOption_id:
    #                 option = request.env['memo.config'].sudo().browse([int(selectedOption_id)])
    #                 all_branches = [option.processing_branch_id.id]
    #             else:
    #                 all_branches = request.env['multi.branch'].sudo().search([])
    #                 all_branches = all_branches.ids
                
    #             domain = [
    #                     ('usage', '=', 'internal'),
    #                     ('branch_id', 'in', all_branches),
    #                     ('name', 'ilike', query)
    #                 ]
    #             if selected_location_id:
    #                 domain.append(('id', '!=', selected_location_id))
    #             location_data_ids = stockObj.search(domain)
                
    #         else:
    #             domain=[
    #                 ('usage', '=', 'internal'),
    #                 ('branch_id.id', 'in', branch_ids),
    #                 ('company_id.id', 'in', [request.env.user.company_id.id] + request.env.user.company_ids.ids),
    #                 ('name', 'ilike', query)
    #                 ]
    #             if selected_location_id:
    #                 domain.append(('id', '!=', selected_location_id))
    #             location_data_ids = stockObj.search(domain)
                 
    #     return json.dumps({
    #         "results": [{"id": item.id, "text": f'{item.name}'} for item in location_data_ids],
    #         "pagination": {
    #             "more": True,
    #         }
    #     })
    
    @http.route('/get-stock-location', type='http', auth='user', csrf=False, methods=['POST'])
    def get_stock_location(self, **kwargs):
        try:
            q = request.params.get('q', '').strip()
            page_limit = int(request.params.get('page_limit', 10))
            page = int(request.params.get('page', 1))
            
            # Handle boolean string conversion
            is_inter_company_raw = request.params.get('is_inter_company')
            is_inter_company = str(is_inter_company_raw).lower() in ('true', '1', 'yes', 'on')
            
            # Get district_id
            district_id = request.params.get('district_id')
            if district_id and district_id not in ['null', 'undefined', 'false', '', 0, '0']:
                try:
                    district_id = int(district_id)
                except (ValueError, TypeError):
                    district_id = 0
            else:
                district_id = 0 
                
            location_type = request.params.get('location_type', 'source')
            
            # Get selected_location_id to exclude
            selected_location_id_raw = request.params.get('selected_location_id', 0)
            try:
                selected_location_id = int(selected_location_id_raw) if selected_location_id_raw else 0
            except (ValueError, TypeError):
                selected_location_id = 0
            
            _logger.info(f"Searching Stock: q={q}, inter={is_inter_company}, district={district_id}, exclude={selected_location_id} testing_loc...")
            
            if location_type == 'source':
                domain = [('usage', '=', 'internal')]
            else:
                domain = [('usage', 'in', ['supplier', 'customer', 'internal'])]
            company_ids = [request.env.user.company_id.id] + request.env.user.company_ids.ids
            if not is_inter_company:
                domain.append(('company_id', '=', request.env.user.company_id.id))
                # domain.append(('company_id', '=', company_ids))
            
            if district_id and district_id > 0:
                domain.append(('branch_id', '=', district_id))
            
            if q:
                domain.append(('name', 'ilike', q))
                
            if selected_location_id and selected_location_id > 0:
                domain.append(('id', '!=', selected_location_id))
            
            _logger.info(f"Search domain: location type {location_type} {domain}")
            
            # Perform Search
            locations = request.env['stock.location'].sudo().search(domain, limit=page_limit)
            
            results = [
                {
                    "id": loc.id,
                    "text": f"{loc.name} ({loc.branch_id.name})" if loc.branch_id else loc.name
                }
                for loc in locations
            ]
            
            _logger.info(f"Found kwargs ==> {len(results)} locations")
            
            return request.make_response(
                json.dumps({
                    "results": results,
                    "total": len(results),
                }),
                headers=[('Content-Type', 'application/json')]
            )
            
        except Exception as e:
            _logger.exception("Error in get_stock_location")
            return request.make_response(
                json.dumps({
                    "error": str(e),
                    "results": [],
                    "total": 0
                }),
                headers=[('Content-Type', 'application/json')]
            )
            
    @http.route(['/relieve/reliever'], type='json', website=True, auth="user", csrf=False)
    def reset_relieve_reliever(self, **post):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search(
        [('active', '=', True), ('user_id', '=', user.id)], limit=1)
        if employee:
            employee.reset_leave_reliever()
            return {
                "status": True,
                "message": "", 
            }
        else:
            return {
                "status": False,
                "message": "You are not linked to any employee record.. Contact HR", 
            } 
            
    # @http.route(
    # 		['/get/leave-allocation/<int:leave_type>/<staff_num>/'], 
    # 		type='json', website=True, auth="user", csrf=False)
    # def get_leave_allocation(self,leave_type,staff_num):
    # 	"""Check staff Identification No.
    # 	Args:
    # 		staff_num (str): The Id No to be validated
    # 	Returns:
    # 		dict: Response
    # 	"""
    # 	_logger.info('Checking Staff ID No ...')
    # 	user = request.env.user
    # 	if staff_num:
    # 		employee = request.env['hr.employee'].sudo().search(
    # 		[('employee_number', '=', staff_num), ('active', '=', True)], limit=1) 
    # 		if employee:
    # 			# get leave artifacts
    # 			leave_allocation = request.env['hr.leave.allocation'].sudo()
    # 			leave_allocation_id = leave_allocation.search([
    # 				('holiday_status_id', '=', leave_type),
    # 				('employee_id.employee_number', '=', staff_num)
    # 				], limit=1)
    # 			if leave_allocation_id:
    # 				return {
    # 					"status": True,
    # 					"data": {
    # 						'number_of_days_display': leave_allocation_id.number_of_days_display,
    # 					},
    # 					"message": "", 
    # 				}
    # 			else:
    # 				return {
    # 				"status": False,
    # 				"data": {
    # 					'number_of_days_display': "",
    # 				},
    # 				"message": "No allocation set up for the employee. Contact Admin", 
    # 				}
    # 		else:
    # 			return {
    # 				"status": False,
    # 				"data": {
    # 					'number_of_days_display': "",
    # 				},
    # 				"message": "Employee with staff ID provided does not exist. Contact Admin", 
    # 				}
    # 	return {
    # 			"status": False,
    # 			"data": {
    # 				'number_of_days_display': "",
    # 			},
    # 			"message": "Please select staff ID. Contact Admin", 
    # 			}
    # ['/get/leave-allocation/<int:leave_type>/<staff_num>/'], 
    # @http.route(['/get/leave-allocation'], type='json', website=True, auth="user", csrf=False)
    # def get_leave_allocation(self, **post):
    #     """Check staff Identification No.
    #     Args:
    #         staff_num (str): The Id No to be validated
    #     Returns:
    #         dict: Response
    #     """
    #     _logger.info(f'Checking Staff leave ID No ... {post}')
    #     staff_num = post.get('staff_num')
    #     leave_type = post.get('leave_id')
    #     user = request.env.user
    #     if staff_num:
    #         _logger.info('staff number found ...')
    #         employee = request.env['hr.employee'].sudo().search(
    #         [('employee_number', '=', staff_num), ('active', '=', True)], limit=1) 
    #         if employee:
    #             _logger.info(f'Lets us see ====> staff {staff_num} == {int(leave_type)} ==employee {employee.id}...')

    #             # get leave artifacts
    #             leave_allocation = request.env['hr.leave.allocation'].sudo()
    #             # Get today's year
    #             current_year = date.today().year
    #             # Define the range
    #             within_this_start_year = date(current_year, 1, 1)    # Jan 1
    #             within_this_end_year = date(current_year, 12, 31)    # Dec 31
    #             leave_allocation_id = leave_allocation.search([
    #                 ('holiday_status_id', '=', int(leave_type)),
    #                 ('employee_id', '=', employee.id),
    #                 ('date_from', '>=', within_this_start_year),
    #                 ('date_from', '<=', within_this_end_year),
    #                 ('active', '=', True),
    #                 # ('holiday_status_id.requires_allocation', '=', 'yes'), # ensure not all leave type
    #                 ], limit=1)
    #             leave_type_obj = request.env['hr.leave.type'].sudo().browse([int(leave_type)])
    #             # _logger.info('staff number found ...')
    #             _logger.info(f'Lets see what happens ...{leave_type_obj} == > {leave_allocation_id} == {within_this_start_year}   =={within_this_end_year}')
    
    #             if leave_type_obj.requires_allocation == 'yes' and not leave_allocation_id:
    #                 return {
    #                     "status": False,
    #                     "data": {
    #                         'number_of_days_display': "",
    #                     },
    #                     "message": "No allocation set up for the employee. Contact Admin", 
    #                     }
    #             else: # if leave_allocation_id:
    #                 return {
    #                     "status": True,
    #                     "data": {
    #                         'number_of_days_display': employee.allocation_remaining_display,
    #                         # 'number_of_days_display': leave_allocation_id.number_of_days_display,
    #                     },
    #                     "message": "", 
    #                 }

    #         else:
    #             return {
    #                 "status": False,
    #                 "data": {
    #                     'number_of_days_display': "",
    #                 },
    #                 "message": "Employee with staff ID provided does not exist. Contact Admin", 
    #                 }
    #     return {
    #             "status": False,
    #             "data": {
    #                 'number_of_days_display': "",
    #             },
    #             "message": "Please select2 staff ID. Contact Admin", 
    #             }
  
    # @http.route(['/check-overlapping-leave'], type='json', website=True, auth="user", csrf=False)
    # def check_overlapping_leave(self, **post):
    #     staff_num = post.get('data').get('staff_num')
    #     start_date = post.get('data').get('start_date')
    #     end_date = post.get('data').get('end_date')
    #     _logger.info(f'posted to check overlapping leave ...{staff_num}, {start_date}, {end_date}')

    #     employee_id = request.env['hr.employee'].sudo().search([
    #         ('employee_number', '=', staff_num)
    #         ], limit=1)
    #     if not any([staff_num, start_date, end_date]):
    #         return {
    #                 "status": False,
    #                 "message": "Please ensure you provide staff number , leave start date and leave end date", 
    #                 }
    #     else:
    #         _logger.info('All fields captured')

    #     if employee_id: 
    #         st = datetime.strptime(start_date, "%m/%d/%Y")
    #         ed = datetime.strptime(end_date, "%m/%d/%Y")
    #         # all_employees = self.employee_id | self.employee_ids
    #         hr_request = request.env['hr.leave'].sudo().search(
    #             [
    #             ('request_date_from', '<=', st),
    #             ('request_date_to', '>=', ed),
    #             ('employee_id', '=', employee_id.id),
    #             # ('state', 'not in', ['draft', 'Refuse']),
    #             ], 
    #             limit=1) 
    #         if hr_request:
    #             msg = """You can not set two time off that overlap on the same day for the same employee. Existing time off:"""
    #             return {
    #                 "status": False,
    #                 "message": msg, 
    #                 } 
    #         else:
    #             _logger.info('No date inbetween')
    #             return {
    #                 "status": True,
    #                 "message": "", 
    #                 }
    #     else:
    #         msg = """No Employee record found"""
    #         return {
    #             "status": False,
    #             "message": msg, 
    #             }
    
    @http.route(['/get/leave-allocation'], type='json', website=True, auth="user", csrf=False)
    def get_leave_allocation(self, **post):
        """Check staff Identification No.
            Args:
                staff_num (str): The Id No to be validated
            Returns:
                dict: Response
        """
        _logger.info(f'Checking Staff leave allocation ... {post}')
        staff_num = post.get('staff_num')
        leave_type = post.get('leave_id')
        user = request.env.user
        if staff_num:
            _logger.info('staff number found ...')
            employee = request.env['hr.employee'].sudo().search(
            [('employee_number', '=', staff_num), ('active', '=', True)], limit=1) 
            if employee:
                _logger.info(f'Lets us see ====> staff {staff_num} == {int(leave_type)} ==employee {employee.id}...')
                leave_allocation = request.env['hr.leave.allocation'].sudo()
                today = date.today()
                leave_allocation_id = request.env['hr.leave.allocation'].sudo().search([
                    ('holiday_status_id', '=', int(leave_type)),
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'validate'),
                    ('active', '=', True),
                    ('date_from', '<=', today),
                    '|', ('date_to', '=', False), ('date_to', '>=', today)
                ], order='date_to asc, date_from asc')
                
                leave_type_obj = request.env['hr.leave.type'].sudo().browse([int(leave_type)])
                # _logger.info('staff number found ...')
                number_of_days_display, leaves_taken = 0, 0
                for lv in leave_allocation_id:
                    number_of_days_display += lv.number_of_days_display 
                    leaves_taken += lv.leaves_taken
                
                if leave_type_obj.requires_allocation == 'yes' and not leave_allocation_id:
                    return {
                        "status": False,
                        "data": {
                            'number_of_days_display': "",
                        },
                        "message": "No allocation set up for the employee. Contact Admin", 
                        }
                else: # if leave_allocation_id:
                    return {
                        "status": True,
                        "data": {
                            # 'number_of_days_display': employee.allocation_remaining_display,
                            # 'number_of_days_display': leave_allocation_id.number_of_days_display,
                            # 'number_of_days_display': leave_allocation_id.number_of_days_display - leave_allocation_id.leaves_taken,
                            'number_of_days_display': number_of_days_display - leaves_taken,
                        },
                        "message": "", 
                    }

            else:
                return {
                    "status": False,
                    "data": {'number_of_days_display': ""},
                    "message": f"No allocation set up for {leave_type_obj.name}. Contact Admin", 
                }
            
                # # CRITICAL FIX: Return the remaining days for THIS SPECIFIC leave type only
                # remaining_days = leave_allocation_id.number_of_days_display
                
                # _logger.info(f'Remaining days for {leave_type_obj.name}: {remaining_days}')
                
                # return {
                #     "status": True,
                #     "data": {
                #         'number_of_days_display': remaining_days,
                #         'leave_type_name': leave_type_obj.name,
                #         'allocation_id': leave_allocation_id.id,
                #     },
                #     "message": "", 
                # }
        else:
            # For leave types that don't require allocation (unlimited leaves)
            return {
                "status": True,
                "data": {
                    'number_of_days_display': 999,  # Or set a high number for unlimited
                    'leave_type_name': leave_type_obj.name,
                    'allocation_id': False,
                },
                "message": "", 
            }


    @http.route(['/check-overlapping-leave'], type='json', website=True, auth="user", csrf=False)
    def check_overlapping_leave(self, **post):
        """Check if employee has overlapping leave dates"""
        data = post.get('data', {})
        staff_num = data.get('staff_num')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        _logger.info(f'Checking overlapping leave: Staff={staff_num}, Start={start_date}, End={end_date}')
        
        # Validate inputs
        if not all([staff_num, start_date, end_date]):
            return {
                "status": False,
                "message": "Please provide staff number, leave start date and leave end date", 
            }
        
        # Find employee
        employee_id = request.env['hr.employee'].sudo().search([
            ('employee_number', '=', staff_num)
        ], limit=1)
        
        if not employee_id:
            return {
                "status": False,
                "message": "Employee not found", 
            }
        
        try:
            # Parse dates
            st = datetime.strptime(start_date, "%m/%d/%Y")
            ed = datetime.strptime(end_date, "%m/%d/%Y")
            
            # Check for overlapping leaves
            # A leave overlaps if:
            # - It starts before or on the new end date AND
            # - It ends on or after the new start date
            overlapping_leaves = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', employee_id.id),
                ('request_date_from', '<=', ed),
                ('request_date_to', '>=', st),
                ('state', 'not in', ['cancel', 'refuse']),  # Exclude cancelled/refused
            ], limit=1)
            
            if overlapping_leaves:
                msg = f"You cannot set overlapping leave dates. Existing leave from {overlapping_leaves.request_date_from.strftime('%m/%d/%Y')} to {overlapping_leaves.request_date_to.strftime('%m/%d/%Y')}"
                _logger.warning(msg)
                return {
                    "status": False,
                    "message": msg, 
                }
            
            _logger.info('No overlapping leave found')
            return {
                "status": True,
                "message": "", 
            }
            
        except ValueError as e:
            _logger.error(f'Date parsing error: {e}')
            return {
                "status": False,
                "message": "Invalid date format. Please use MM/DD/YYYY", 
            }
        except Exception as e:
            _logger.error(f'Error checking overlapping leave: {e}')
            return {
                "status": False,
                "message": f"Error: {str(e)}", 
            }
        
    @http.route(['/check-configured-stage'], type='json', website=True, auth="user", csrf=False)
    def check_configured_memo_config(self, **post):
        staff_num = post.get('staff_num')
        request_option = post.get('request_option')
        request_config_option = post.get('request_config_option')
        _logger.info(f'posted to check configured stage ...{staff_num}, {request_config_option}')
        employee_id = request.env['hr.employee'].sudo().search([
            ('employee_number', '=', staff_num)
            ], limit=1)
        if not any([staff_num, request_config_option]):
            return {
                    "status": False,
                    "message": "Please ensure you provide staff number, request option", 
                    }
        else:
            _logger.info('All fields captured')

        # if employee_id and employee_id.department_id:
            # check if user is from external company, restrict them from using internal applications 
            # memo_setting_id = request.env['memo.config'].sudo().search([
            # 	('memo_type.memo_key', '=', request_option),
            # 	('department_id', '=', employee_id.department_id.id)
            # 	], limit=1) 
            memo_setting_id = request.env['memo.config'].sudo().search(
               [('id', '=', int(request_config_option))], limit=1)
            if not memo_setting_id or not memo_setting_id.stage_ids:
                msg = """
                Please contact system admin to properly 
                configure a request type for your department"""
                return {
                    "status": False,
                    "message": msg, 
                    } 
            else:
                _logger.info('Found memo setting for thee')
                # if employee_id.is_external_staff and not employee_id.external_company_id.id in memo_setting_id.mapped('allowed_for_company_ids').ids:
                # # .filtered(
                # # 	lambda partner: partner.id !=  employee_id.external_company_id.id): 
                #     _logger.info('Employee not an external user')
                #     return {
                #         "status": False,
                #         "message": '''
                #         Sorry! You are not allowed to
                #         use this option for now ''' 
                #         }
                # else:
                _logger.info('Employee is internal allowed user')
                
                district_domain = []
                if not memo_setting_id.allow_cross_company_requests:
                    district_domain = [('company_id', '=', request.env.user.company_id.id)] #AAdd allowed companies
                districts = request.env['multi.branch'].sudo().search(district_domain)
                return {
                    "status": True,
                    "message": "", 
                    "data": {
                        'inter_district_request': memo_setting_id.inter_district,
                        'districts': [{'id': d.id, 'name': d.name} for d in districts], 
                    }
                    }
            # else:
            # 	msg = """
            # 	No Employee record found or employee department 
            # 	not properly configured. Contact system Admin"""
            # 	return {
            # 		"status": False,
            # 		"message": msg, 
            # 		}
        
    @http.route(['/check-cash-retirement'], type='json', website=True, auth="user", csrf=False)
    def check_cash_retirement(self, **post):
        user = request.env.user 
        staff_num = post.get('staff_num')
        memo_obj = request.env['memo.model'].sudo()
        employee_obj = request.env['hr.employee'].sudo()
        if staff_num:
            domain = [
                ('employee_id.employee_number', '=', staff_num),
                ('active', '=', True),
                ('employee_id.user_id', '=', user.id),
                ('memo_type.memo_key', '=', 'cash_advance'),
                # ('soe_advance_reference', '=', False),
                ('is_cash_advance_retired', '=', False),
                ('state', 'in', ['Done']) # PLEASE DONT REMOVE: until the request is completed, 
                # Because its possible the requests was reject, 
            ]
            employee = employee_obj.search([('employee_number', '=', staff_num)], limit=1)
            cash_advance_not_retired = memo_obj.search_count(domain)
            employee_max_cash_advance_limit = employee.maximum_cash_advance_limit
            _logger.info(f"This is cash advance check staff_num: {staff_num}")
            if cash_advance_not_retired >= employee_max_cash_advance_limit:
                _logger.info(f"Cash advance not retired: {cash_advance_not_retired}")
                return {
                    "status": False,
                    "message": f"""You have exhauseted your maximum cash advance limit of {employee_max_cash_advance_limit} to request. 
                     You cannot request for another cash advance without retiring an existing one. Contact admin to set more cash advance limit for you:"""
                }
            else:
                _logger.info(f"Cash advance is retired")
                return {
                    "status": True,
                    "message": "" 
                }
                
        else:
            return {
                "status": False,
                "message": "Staff Number required" 
            }

    @http.route(['/portal-request-cash-advance'], type='http', website=True, auth="user", csrf=False)
    def get_portal_cash_advance(self, **post):
        """Search for unretired cash advances for the current employee"""
        query = request.params.get('q', '').strip()
        staff_num = post.get('staff_num', '').strip()
        page_limit = int(post.get('page_limit', 10))
        page = int(post.get('page', 1))
        
        is_inter_district = post.get('is_inter_district', 'false')
        is_inter_district = is_inter_district in ['true', 'True', '1', 'on', True]
        _logger.info(f"This is..._ {is_inter_district}")
        
        _logger.info(f'Searching cash advances: query={query}, staff_num={staff_num}')
        
        if not staff_num:
            return json.dumps({
                "results": [],
                "total": 0,
                "pagination": {"more": False}
            })
        
        employee = request.env['hr.employee'].sudo().search([
            ('employee_number', '=', staff_num),
            ('active', '=', True)
        ], limit=1)
        
        if not employee:
            return json.dumps({
                "results": [],
                "total": 0,
                "pagination": {"more": False}
            })
        
        domain = [
            ('employee_id', '=', employee.id),
            ('active', '=', True),
            ('memo_type.memo_key', '=', 'cash_advance'),
            ('is_cash_advance_retired', '=', False),
            ('state', 'in', ['Done']),
            ('memo_setting_id.inter_district', '=', is_inter_district)
        ]
        
        if query:
            domain.append('|')
            domain.append(('code', 'ilike', query))
            domain.append(('name', 'ilike', query))
        
        offset = (page - 1) * page_limit
        cash_advances = request.env['memo.model'].sudo().search(
            domain, 
            limit=page_limit,
            offset=offset,
            order='create_date desc'
        )
        
        total_count = request.env['memo.model'].sudo().search_count(domain)
        
        results = []
        for ca in cash_advances:
            amount_display = f"{ca.request_total_amount:,.2f}" if ca.request_total_amount else "0.00"
            date_display = ca.date.strftime('%d-%b-%Y') if ca.date else ''
            
            results.append({
                "id": ca.id,
                "text": f"{ca.code} - {ca.name} (₦{amount_display}) - {date_display}",
                "code": ca.code
            })
        
        return json.dumps({
            "results": results,
            "total": total_count,
            "pagination": {
                "more": (page * page_limit) < total_count
            }
        })

    # @http.route(['/check_order'], type='json', website=True, auth="user", csrf=False)
    # def check_order(self, **post):
    #     staff_num = post.get('staff_num')
    #     existing_order = post.get('existing_order')
    #     request_type = post.get('request_type')
    #     # staff_num, existing_order
    #     """Check existing order No.
    #     Args:
    #         existing_order (str): The Id No to be validated
    #         staff num (str): staff num of the employee 
    #     Returns:
    #         dict: Response
    #     """
    #     _logger.info(f'Checking check_order No {existing_order}...{request_type}')
    #     user = request.env.user 
    #     if staff_num:
    #         domain = [
    #             ('employee_id.employee_number', '=', staff_num),
    #             ('active', '=', True),
    #             ('employee_id.user_id.id', '=', user.id),
    #             ('code', '=ilike', existing_order) 
    #         ]
    #         if request_type == "soe":
    #             '''this should only return the request cash advance that has
    #               been approved and taken out from the account side
    #             '''
    #             domain += [('state', 'in', ['Done']), ('memo_type.memo_key', 'in', ['cash_advance'])]
    #         else:
    #             domain += [('state', 'in', ['submit'])]
    #         memo_request = request.env['memo.model'].sudo().search(domain, limit=1) 
    #         _logger.info(f"DOMAAAN {domain}")
    #         if memo_request: 
    #             if request_type == "soe" and not memo_request.mapped('product_ids').filtered(lambda x: not x.retired):
    #                 return {
    #                 "status": False,
    #                 "link": False,
                    
    #                 "data": {
    #                     'name': "",
    #                     'phone': "",
    #                     'work_email': "",
    #                     'subject': "",
    #                     'description': "",
    #                     'request_date': "",
    #                     'product_ids': "",
    #                 },
    #                 "message": 'You cannot process with retirement as All cash advance lines has been retired' 
    #                 }
    #             existing_soe_inprogress = request.env['memo.model'].sudo().search([
    #                 ('cash_advance_reference.code', '=', existing_order.upper()), 
    #                 ('state', 'in', ['Sent', 'Approve', 'Approve2', 'Done'])], limit=1) 
    #             is_internal_user = request.env.user.has_group('base.group_user')
    #             if request_type == "soe" and existing_soe_inprogress:
    #                 return {
    #                 "status": False,
    #                 "link": get_model_url(existing_soe_inprogress.id, 'memo.model') if is_internal_user else f'/my/request/view/{existing_soe_inprogress.id}',
    #                 "data": {
    #                     'name': "",
    #                     'phone': "",
    #                     'work_email': "",
    #                     'subject': "",
    #                     'description': "",
    #                     'request_date': "",
    #                     'product_ids': "",
    #                 },
    #                 "message": f"There is an existing retirement with REF: {existing_soe_inprogress.code} still in progress. You will be redirected to the record to cancel or refuse it, then proceed" 
    #                 }
    #             return {
    #                 "status": True,
    #                 "link": False,
    #                 "data": {
    #                     'name': memo_request.employee_id.name,
    #                     'phone': memo_request.employee_id.work_phone or memo_request.employee_id.mobile_phone,
    #                     'state': 'Draft' if memo_request.state == 'submit' else 'Waiting For Payment / Confirmation' if memo_request.state == 'Approve' else 'Approved' if memo_request.state == 'Approve2' else 'Done' if memo_request.state == 'Done' else 'Refused',
    #                     'work_email': memo_request.employee_id.work_email,
    #                     'subject': f"RETIREMENT FOR {memo_request.code} - {memo_request.name}",
    #                     'description': memo_request.description or "",
    #                     'amount': sum([
    #                         rec.amount_total or rec.product_id.list_price for rec in memo_request.product_ids]) \
    #                             if memo_request.product_ids else memo_request.amountfig,
    #                     # 'district_id': memo_request.employee_id.ps_district_id.id,
    #                     # 'district_id': memo_request.employee_id.ps_district_id.id,
    #                     'request_date': memo_request.date.strftime("%m/%d/%Y") if memo_request.date else "",
    #                     'product_ids': [
    #                         {'id': q.product_id.id, 
    #                         'name': q.product_id.name if q.product_id else q.description, 
    #                         'qty': q.quantity_available,
    #                         # building lines for cash advance and soe
    #                         'used_qty': q.quantity_available, # q.used_qty,
    #                         'amount_total': q.amount_total, # FIXME PLEASE DONT CHANGE RATHER ADD THE SUB TOTAL AMOUNT ON THE DYNAMIC RENDERING
    #                         'used_amount': q.amount_total, # q.used_amount, 
    #                         'sub_total_amount': q.sub_total_amount, # q.used_amount,
    #                         'description': q.description or "",
    #                         'request_line_id': q.id,
    #                         } 
    #                         for q in memo_request.mapped('product_ids').filtered(lambda x: not x.retired)
    #                     ]
    #                 },
    #                 "message": "", 
    #                 }
    #         else:
    #             message = "Sorry !!! ReF does not exist or You cannot do an SOE because the request Cash Advance has not been approved" \
    #             if request_type == "soe" else "Request ID with staff ID does not exist / has been submitted already. Contact Admin"
    #             return {
    #                 "status": False,
    #                 "link": False,
                    
    #                 "data": {
    #                     'name': "",
    #                     'phone': "",
    #                     'work_email': "",
    #                     'subject': "",
    #                     'description': "",
    #                     # 'district_id': "",
    #                     # 'district_id': "",
    #                     'request_date': "",
    #                     'product_ids': "",
    #                 },
    #                 "message": message 
    #                 }

    @http.route(['/check_order'], type='json', website=True, auth="user", csrf=False)
    def check_order(self, **post):
        staff_num = post.get('staff_num')
        existing_order = post.get('existing_order')
        existing_order_id = post.get('existing_order_id')
        request_type = post.get('request_type')
        
        _logger.info(f'Checking order: existing_order={existing_order}, existing_order_id={existing_order_id}, type={request_type}')
        
        user = request.env.user 
        
        if not staff_num:
            return {
                "status": False,
                "link": False,
                "data": {},
                "message": "Staff number is required"
            }
        
        domain = [
            ('employee_id.employee_number', '=', staff_num),
            ('active', '=', True),
            ('employee_id.user_id.id', '=', user.id),
        ]
        
        if existing_order_id:
            domain.append(('id', '=', int(existing_order_id)))
        elif existing_order:
            domain.append(('code', '=ilike', existing_order))
        else:
            return {
                "status": False,
                "link": False,
                "data": {},
                "message": "Please provide cash advance reference"
            }
        
        if request_type == "soe":
            domain += [
                ('state', 'in', ['Done']), 
                ('memo_type.memo_key', 'in', ['cash_advance'])
            ]
        else:
            domain += [('state', 'in', ['submit'])]
        
        memo_request = request.env['memo.model'].sudo().search(domain, limit=1)
        
        _logger.info(f"Search domain: {domain}")
        
        if not memo_request:
            message = "Sorry! Ref does not exist or You cannot do an SOE because the request Cash Advance has not been approved" \
                if request_type == "soe" else "Request ID with staff ID does not exist / has been submitted already. Contact Admin"
            
            return {
                "status": False,
                "link": False,
                "data": {},
                "message": message
            }
        
        if request_type == "soe" and not memo_request.mapped('product_ids').filtered(lambda x: not x.retired):
            return {
                "status": False,
                "link": False,
                "data": {},
                "message": 'You cannot proceed with retirement as all cash advance lines have been retired'
            }
        
        existing_soe_inprogress = request.env['memo.model'].sudo().search([
            ('cash_advance_reference.code', '=', memo_request.code.upper()), 
            ('state', 'in', ['Sent', 'Approve', 'Approve2', 'Done'])
        ], limit=1)
        
        is_internal_user = request.env.user.has_group('base.group_user')
        
        if request_type == "soe" and existing_soe_inprogress:
            link = get_model_url(existing_soe_inprogress.id, 'memo.model') if is_internal_user else f'/my/request/view/{existing_soe_inprogress.id}'
            return {
                "status": False,
                "link": link,
                "data": {},
                "message": f"There is an existing retirement with REF: {existing_soe_inprogress.code} still in progress. You will be redirected to the record to cancel or refuse it, then proceed"
            }
        
        return {
            "status": True,
            "link": False,
            "data": {
                'name': memo_request.employee_id.name,
                'phone': memo_request.employee_id.work_phone or memo_request.employee_id.mobile_phone,
                'state': 'Draft' if memo_request.state == 'submit' else 'Waiting For Payment / Confirmation' if memo_request.state == 'Approve' else 'Approved' if memo_request.state == 'Approve2' else 'Done' if memo_request.state == 'Done' else 'Refused',
                'work_email': memo_request.employee_id.work_email,
                'subject': f"RETIREMENT FOR {memo_request.code} - {memo_request.name}",
                'description': memo_request.description or "",
                'amount': sum([
                    rec.amount_total or rec.product_id.list_price for rec in memo_request.product_ids
                ]) if memo_request.product_ids else memo_request.amountfig,
                'request_date': memo_request.date.strftime("%m/%d/%Y") if memo_request.date else "",
                'product_ids': [
                    {
                        'id': q.product_id.id, 
                        'name': q.product_id.name if q.product_id else q.description, 
                        'qty': q.quantity_available,
                        'used_qty': q.quantity_available,
                        'amount_total': q.amount_total,
                        'used_amount': q.amount_total,
                        'sub_total_amount': q.sub_total_amount,
                        'description': q.description or "",
                        'request_line_id': q.id,
                    } 
                    for q in memo_request.mapped('product_ids').filtered(lambda x: not x.retired)
                ]
            },
            "message": ""
        }
            
    @http.route(["/portal-success"], type='http', auth='user', website=True, website_published=True)
    def portal_success(self):
        """Request portal for employee / portal users
        """
        memo_number = request.session.get('memo_ref')
        memo_id = request.session.get('memo_record_id')
        vals = {
            "memo_number": memo_number,
            "memo_id": memo_id
        }
        # request.session.clear()
        return request.render("portal_request.portal_request_success_template", vals)

    # @http.route(['/portal-request-product'], type='http', website=True, auth="user", csrf=False)
    # def get_portal_product(self, **post):
    #     productItems = json.loads(post.get('productItems'))
    #     request_type_option = post.get('request_type')
    #     source_locationId = post.get('source_locationId')
    #     _logger.info(f'productitemmms {productItems}')
    #     query = request.params.get('q', '') 
    #     productItems_List = [int(i) for i in productItems if i]
    #     result = []
    #     if source_locationId:
    #         domain = [
    #         ('product_id.id', 'not in', productItems_List),
    #         ('location_id', '=', int(source_locationId)), 
    #           '|','|', 
    #         ('product_id.name', 'ilike', query),
    #         ('product_id.default_code', 'ilike', query),
    #         ('product_id.barcode', 'ilike', query)
    #         ]
    #         quants = request.env["stock.quant"].sudo().search(domain)
    #         if quants:
    #             for item in quants:
    #                 result.append(
    #                     {
    #                         "id": item.product_id.id,
    #                         "text": f'{item.product_id.name} {item.product_id.default_code}', 
    #                         "qty": item.product_id.qty_available
    #                     })
    #     else:
    #         domain = [
    #         ('detailed_type', 'in', ['consu', 'product']), 
    #            ('id', 'not in', productItems_List),
    #         ('company_id', '=', request.env.user.company_id.id), 
    #            ('active', '=', True), 
    #           '|','|', 
    #         ('name', 'ilike', query),
    #         ('default_code', 'ilike', query),
    #         ('barcode', 'ilike', query)
    #         ]
    #         products = request.env["product.product"].sudo().search(domain)
    #         if products:
    #             for item in products:
    #                 result.append(
    #                     {
    #                         "id": item.id,
    #                         "text": f'{item.name} {item.default_code}', 
    #                         'qty': item.qty_available
    #                     })

    #     if request_type_option and request_type_option == "vehicle_request":
    #         result = []
    #         domain = [
    #                     ('is_vehicle_product', '=', True), 
    #                     ('detailed_type', 'in', ['service']), 
    #                     ('id', 'not in', productItems_List),
    #                     ('company_id', '=', request.env.user.company_id.id), 
    #                     ('active', '=', True), 
    #                     '|','|', 
    #                     ('name', 'ilike', query),
    #                     ('default_code', 'ilike', query),
    #                     ('barcode', 'ilike', query)
    #                   ]
    #         products = request.env["product.product"].sudo().search(domain)
    #         if products:
    #             for item in products:
    #                 result.append(
    #                     {
    #                         "id": item.id,
    #                         "text": f'{item.name} {item.default_code}', 
    #                         'qty': item.qty_available
    #                     })
    #     # domain = [('id', 'in', [403, 222, 1000, 5000])]
    #     return json.dumps({
    #         "results": result , #[{"id": item.id,"text": f'{item.name} {item.default_code}', 'qty': item.qty_available} for item in products],
    #         "pagination": {
    #             "more": True,
    #         }
    #     })
    
    # @http.route(['/portal-request-product'], type='http', website=True, auth="user", csrf=False)
    # def get_portal_product(self, **post):
    #     productItems = json.loads(post.get('productItems'))
    #     request_type_option = post.get('request_type')
    #     source_locationId = post.get('source_locationId')
    #     processing_branch = post.get('processing_branch')
        
    #     company = self.env['multi.branch'].search(processing_branch.company_id)
        
    #     _logger.info(f'productItems {productItems}')
    #     query = request.params.get('q', '') 
    #     productItems_List = [int(i) for i in productItems if i]
    #     result = []
        
    #     domain = [
    #         ('id', 'not in', productItems_List),
    #         ('company_id', '=', company.id), 
    #         ('active', '=', True), 
    #         '|','|', 
    #         ('name', 'ilike', query),
    #         ('default_code', 'ilike', query),
    #         ('barcode', 'ilike', query)
    #     ]

    #     service_allowed_types = ['procurement_request', 'sale_request']
        
    #     if request_type_option == "vehicle_request":
    #         domain += [
    #             ('is_vehicle_product', '=', True), 
    #             ('detailed_type', 'in', ['service'])
    #         ]
    #     elif request_type_option == 'material_request':
    #         domain += [('detailed_type', 'in', ['consu', 'product'])]
    #     elif request_type_option in service_allowed_types:
    #         domain += [('detailed_type', 'in', ['consu', 'product', 'service'])]
    #     else:
    #         domain += [('detailed_type', 'in', ['consu', 'product'])]

    #     products = request.env["product.product"].sudo().search(domain, limit=20)
        
    #     for item in products:
    #         qty_available = 0.0
            
    #         if source_locationId and str(source_locationId).isdigit():
    #             qty_available = item.with_context(location=int(source_locationId)).qty_available
    #         else:
    #             qty_available = item.qty_available

    #         result.append({
    #             "id": item.id,
    #             "text": f'{item.name} {item.default_code or ""}', 
    #             "qty": qty_available
    #         })
        
    #     return json.dumps({
    #         "results": result,
    #         "pagination": {
    #             "more": len(products) == 20,
    #         }
    #     })
    
    @http.route(['/portal-request-product'], type='http', website=True, auth="user", csrf=False)
    def get_portal_product(self, **post):
        productItems = json.loads(post.get('productItems'))
        request_type_option = post.get('request_type')
        
        # Get IDs from POST
        source_locationId = post.get('source_locationId')
        processing_branch_id = post.get('processing_branch_id')
        memo_config_id = post.get('memo_config_id')
        
        _logger.info(f'Product Search - Source: {source_locationId}, Branch: {processing_branch_id}, Config: {memo_config_id}')
        
        query = request.params.get('q', '') 
        productItems_List = [int(i) for i in productItems if i]
        result = []

        target_company_id = request.env.user.company_id.id # Default fallback

        # Priority 1: If Source Location is selected, use its company
        if source_locationId and str(source_locationId).isdigit():
            loc = request.env['stock.location'].sudo().browse(int(source_locationId))
            if loc.company_id:
                target_company_id = loc.company_id.id
        
        elif processing_branch_id and str(processing_branch_id).isdigit():
            branch = request.env['multi.branch'].sudo().browse(int(processing_branch_id))
            if branch.company_id:
                target_company_id = branch.company_id.id

        elif memo_config_id and str(memo_config_id).isdigit():
            config = request.env['memo.config'].sudo().browse(int(memo_config_id))
            if config.processing_company_id:
                target_company_id = config.processing_company_id.id
            elif config.processing_branch_id and config.processing_branch_id.company_id:
                target_company_id = config.processing_branch_id.company_id.id
        # ---------------------------------------

        # Use target_company_id in the domain
        domain = [
            ('id', 'not in', productItems_List),
            ('company_id', '=', target_company_id), 
            ('active', '=', True), 
            '|','|', 
            ('name', 'ilike', query),
            ('default_code', 'ilike', query),
            ('barcode', 'ilike', query)
        ]

        service_allowed_types = ['procurement_request', 'sale_request']
        
        if request_type_option == "vehicle_request":
            domain += [('is_vehicle_product', '=', True), ('detailed_type', 'in', ['service'])]
        elif request_type_option == 'material_request':
            domain += [('detailed_type', 'in', ['consu', 'product'])]
        elif request_type_option in service_allowed_types:
            domain += [('detailed_type', 'in', ['consu', 'product', 'service'])]
        else:
            domain += [('detailed_type', 'in', ['consu', 'product'])]

        products = request.env["product.product"].sudo().search(domain, limit=20)
        
        for item in products:
            qty_available = 0.0
            
            if source_locationId and str(source_locationId).isdigit():
                qty_available = item.with_context(location=int(source_locationId)).qty_available
            else:
                qty_available = item.qty_available

            result.append({
                "id": item.id,
                "text": f'{item.name} {item.default_code or ""} (Qty: {qty_available})', 
                "qty": qty_available
            })
        
        return json.dumps({
            "results": result,
            "pagination": {
                "more": len(products) == 20,
            }
        })
        
    @http.route(['/portal-request-employee-reliever'], type='http', website=True, auth="user", csrf=False)
    def get_employee_reliever(self, **post):
        available_employees = []
        query = request.params.get('q', '') 
        domain = [
            ('active', '=', True), 
            # ('company_id', '=', request.env.user.company_id.id),
            # ('company_id.user_id.company_ids.ids', 'in', [request.env.user.company_id.id]),
            '|', ('name', 'ilike', query),('employee_number', 'ilike', query),
            ]#, ('id', 'in', available_employees)]
        employees = request.env["hr.employee"].sudo().search(domain)
        return json.dumps({
            "results": [{"id": item.id, "text": f'{item.name} - {item.employee_number}'} for item in employees],
            "pagination": {
                "more": True,
            }
        })
        
    @http.route(['/portal-request-get-vendors'], type='http', website=True, auth="user", csrf=False)
    def get_vendors(self, **post):
        available_employees = []
        query = request.params.get('q', '') 
        domain = [
            ('active', '=', True), 
            # ('company_id', '=', request.env.user.company_id.id),
            # ('supplier_rank', 'in', [1, '1']),
            # ('company_id.user_id.company_ids.ids', 'in', [request.env.user.company_id.id]),
            '|', ('name', 'ilike', query),('vendor_code', 'ilike', query),
            ]
        vendors = request.env["res.partner"].sudo().search(domain)
        return json.dumps({
            "results": [{"id": item.id, "text": f"{item.name} - {item.vendor_code or ''}"} for item in vendors],
            "pagination": {
                "more": True,
            }
        })
    
    @http.route(['/portal-request-employee'], type='http', website=True, auth="user", csrf=False)
    def get_portal_employee(self, **post):
        request_type_option = post.get('request_type')
        if request_type_option:
            if request_type_option == "employee":
                employeeItems = json.loads(post.get('employeeItems'))
                _logger.info(f'Employeeitemmms {employeeItems}')
                domain = [('active', '=', True), ('id', 'not in', [int(i) for i in employeeItems if i]), 
                          ('company_id', '=', request.env.user.company_id.id)]
                employees = request.env["hr.employee"].sudo().search(domain)
                return json.dumps({
                    "results": [{"id": item.id,"text": f'{item.name} - {item.employee_number}'} for item in employees],
                    "pagination": {
                        "more": True,
                    }
                })	
            elif request_type_option == "department":
                domain = [('active', '=', True), ('company_id', '=', request.env.user.company_id.id)]
                departments = request.env["hr.department"].sudo().search(domain)
                return json.dumps({
                    "results": [{"id": item.id,"text": f'{item.name}'} for item in departments if item],
                    "pagination": {
                        "more": True,
                    }
                })
            elif request_type_option == "role":
                domain = [('active', '=', True), ('company_id', '=', request.env.user.company_id.id)]
                departments = request.env["hr.job"].sudo().search(domain)
                return json.dumps({
                    "results": [{"id": item.id,"text": f'{item.name}'} for item in departments],
                    "pagination": {
                        "more": True,
                    }
                })
            elif request_type_option == "district":
                domain = [('company_id', '=', request.env.user.company_id.id)]
                departments = request.env["multi.branch"].sudo().search(domain)
                return json.dumps({
                    "results": [{"id": item.id,"text": f'{item.name}'} for item in departments if item],
                    "pagination": {
                        "more": True,
                    }
                })
            else:	
                return json.dumps({
                    "results": [{"id": '',"text": '',}],
                    "pagination": {
                        "more": True,
                    }
                })	
        else:
            return json.dumps({
                "results": [{"id": '',"text": ''}],
                "pagination": {
                    "more": True,
                }
            })

    # @http.route(['/portal-request-employee'], type='http', website=True, auth="user", csrf=False)
    # def get_portal_employee(self, **post):
    # 	request_type_option = post.get('request_type')
    # 	if request_type_option:
    # 		if request_type_option == "employee":
    # 			employeeItems = json.loads(post.get('employeeItems'))
    # 			_logger.info(f'Employeeitemmms {employeeItems}')
    # 			domain = [('active', '=', True), ('id', 'not in', [int(i) for i in employeeItems])]
    # 			employees = request.env["hr.employee"].sudo().search(domain)
    # 			return json.dumps({
    # 				"results": [{"id": item.id,"text": f'{item.name} - {item.employee_number}'} for item in employees],
    # 				"pagination": {
    # 					"more": True,
    # 				}
    # 			})	
    # 		elif request_type_option == "department":
    # 			domain = [('active', '=', True)]
    # 			departments = request.env["hr.department"].sudo().search(domain)
    # 			return json.dumps({
    # 				"results": [{"id": item.id,"text": f'{item.name}'} for item in departments],
    # 				"pagination": {
    # 					"more": True,
    # 				}
    # 			})
    # 		elif request_type_option == "role":
    # 			domain = [('active', '=', True)]
    # 			departments = request.env["hr.job"].sudo().search(domain)
    # 			return json.dumps({
    # 				"results": [{"id": item.id,"text": f'{item.name}'} for item in departments],
    # 				"pagination": {
    # 					"more": True,
    # 				}
    # 			})
    # 		elif request_type_option == "district":
    # 			domain = []
    # 			departments = request.env["multi.branch"].sudo().search(domain)
    # 			return json.dumps({
    # 				"results": [{"id": item.id,"text": f'{item.name}'} for item in departments],
    # 				"pagination": {
    # 					"more": True,
    # 				}
    # 			})
    # 		else:	
    # 			return json.dumps({
    # 				"results": [{"id": '',"text": '',}],
    # 				"pagination": {
    # 					"more": True,
    # 				}
    # 			})	
    # 	else:
    # 		return json.dumps({
    # 			"results": [{"id": '',"text": ''}],
    # 			"pagination": {
    # 				"more": True,
    # 			}
    # 		})	

    @http.route(['/my/request-state'], type='json', website=True, auth="user", csrf=False)
    def check_request_state(self,  *args, **kwargs):
        type = kwargs.get('type') 
        id = kwargs.get('id') 
        """ 
        Args:
            type (type): either set to draft or set to Sent
            id: id of the record
        Returns:
            dict: Response
        """
        _logger.info(f'Sending request of .... {type} with id {id}')
        if id and type:
            record = request.env['memo.model'].sudo().search(
            [
                ('active', '=', True),
                ('id', '=', int(id))
            ], 
            limit=1) 
            if record:
                return {
                    "status": True,
                    "message": f"Succeessfully updated", 
                    }
            else:
                return {
                    "status": False,
                    "message": "There is no record found to update status", 
                    }
        else:
            return {
                "status": False,
                "message": "No record found to update", 
                }
                 
        
    @http.route(['/check-quantity'], type='json', website=True, auth="user", csrf=False)
    def check_qty(self,  *args, **kwargs):
        # params = kwargs.get('params')
        product_id = kwargs.get('product_id')
        qty = kwargs.get('qty') 
        sourceLocationId = kwargs.get('sourceLocationId') 
        is_interdistrict = kwargs.get('is_interdistrict') 
        district = kwargs.get('district') 
        request_type = kwargs.get('request_type') 

        """Check quantity.
        Args:
            product_id (id): The Id No to be validated
            qty (qty): qty
        Returns:
            dict: Response
        """
        if request_type in ['procurement_request', 'sale_request', 'Payment', 'cash_advance']:
            return {
                "status": True,
                "location_id": False,
                "message": "", 
            }
            
        _logger.info(f'Checking product for {product_id},INTERDISTRICT {is_interdistrict}, SOURCE LOCATION {sourceLocationId} REQUEST TYPE {request_type} District {request.env.user.branch_id.id} check_ qty No ...{qty}')
        if product_id:# and type(product_id) in [int]:
            product = request.env['product.product'].sudo().search(
            [
                ('active', '=', True),
                # ('detailed_type', '=', 'product'),
                ('id', '=', int(product_id)),
            ], 
            limit=1) 
            LocationObj = request.env['stock.location'].sudo()
            if product:
                # is_interdistrict = True if is_interdistrict in ['on', 'On', 'On', 'true', False] else False
                is_interdistrict = True
                if not is_interdistrict:
                    domain = [
                        ('company_id', '=', request.env.user.company_id.id),
                        ('usage', '=', 'internal')
                    ] 
                else:
                    if not sourceLocationId:
                        return {
                            "status": False,
                            "location_id": False,
                            "message": f"""Source location for interdistrict transfer must be provided""", 
                            }
                    src = LocationObj.browse(int(sourceLocationId))
                    _logger.info(f'setting inter source location domain as {src}')
                    domain = [
                        ('company_id', '=', src.company_id.id),
                        ('usage', '=', 'internal')
                    ] 
                # should_bypass_reservation : False
                if request_type in ['material_request'] and product.detailed_type in ['product']:
                    sourceLocationId = False if sourceLocationId in [False, 'false', 'False'] else sourceLocationId 
                    location_ids = LocationObj.browse(int(sourceLocationId)) if sourceLocationId else LocationObj.search(domain)
                    '''Checks if any location of type internal and company is user company only'''
                    _logger.info(f"Locations found: {location_ids}")
                    if not location_ids:
                        return {
                            "status": False,
                            "location_id": False,
                            "message": f"""No internal storage source location found for request you wanted to make.
                               Contact store officer for Assistance""", 
                            }
                    location = False
                    product_qty = float(qty) if qty else 0
                    total_availability = 0
                    for loc in location_ids:
                        _logger.info(f"what is location {loc}, and product {product.id}, {product.name}")
                        '''search quant with the designated location'''
                        location_with_qty = request.env['stock.quant'].sudo().search(
                            [('location_id', '=', loc.id),
                             ('location_id.usage', '=', 'internal'), 
                             ('product_id', '=', product.id),
                            #  ('quantity', '>', 0)
                             ]
                            )
                        _logger.info(f"Quant with Quantity {location_with_qty.quantity}")
                        # location_with_qty = loc.mapped('quant_ids').filtered(lambda q: q.available_quantity >= product_qty)
                        if location_with_qty:
                            '''Quant with Quantit'''
                            for lc_quant in location_with_qty:
                                total_availability += lc_quant.quantity
                                if lc_quant.quantity > product_qty: # if any is greater than request qty, use the location
                                    location = loc
                                    break
                                else:
                                    # '''necessary at least to ensure there is any location of those products'''
                                    # location = loc
                                    pass 
                                _logger.info(f"What is quant quantity {lc_quant.quantity}")
                    
                    '''necessary at least to ensure there is any location of those products'''
                    if total_availability <= 0: 
                        '''if no quantity found in all warehouse location'''
                        # suggestable_locations = request.env['stock.location'].search([('usage', '=', 'internal')])
                        # for loc_quant in suggestable_locations:
                        quants_with_qty = request.env['stock.quant'].sudo().search(
                            [
                             ('location_id.usage', '=', 'internal'), 
                             ('product_id', '=', product.id),
                             ('quantity', '>=', product_qty)
                             ]
                            )
                        msg_loc = []
                        for loc_quant in quants_with_qty:
                            _logger.info(f"wegere  {loc_quant.location_id.name} {product_qty}")
                            msg_loc.append(f"{loc_quant.location_id.name} - {loc_quant.quantity}")
                        message_display = '\n'.join(msg_loc)
                        return {
                            "status": False,
                            "location_id": False,
                            "message": f"""
                            System could not found any single quantity available in your 
                            company locations.However below are the locations that have them available.\n
                            {message_display}
                            """, 
                        }
                    if product_qty > total_availability: 
                        return {
                            "status": False,
                            "location_id": False,
                            "message": f"""
                            Selected product: ({product_qty}) 
                            quantity is higher than the Available Quantity. 
                            Available quantity is {total_availability}""", 
                        }
                    else:
                        _logger.info(f"Location outcome is {location}")
                        return {
                            "status": True,
                            "message": "",
                            "location_id": location and location.id
                        }
                else:
                    return {
                            "status": True,
                            "location_id": False,
                            "message": "", 
                            }
            else:
                return {
                    "status": False,
                    "location_id": False,
                    "message": "The product does not exist on the inventory", 
                    }
        else:
            return {
                "status": False,
                "location_id": False,
                "message": "Select a product first, before adding unit quantity", 
                }
 
    def generate_attachment(self, name, title, datas, res_id, model='memo.model', delete_record=False):
        attachment = request.env['ir.attachment'].sudo()
        if delete_record:
            existing_attachment=attachment.search([
                ('res_model', '=', 'memo.model'),
                ('res_id', '=', res_id)])
            existing_attachment.unlink()
        attachment_id = attachment.create({
            'name': f"{title} for {name}",
            'type': 'binary',
            'datas': datas,
            'res_name': name,
            'res_model': model,
            'res_id': res_id,
        })
        return attachment_id
    
    def _parse_float(self, value):
        """
        Safely convert string to float, handling commas and empty values.
        """
        if not value:
            return 0.0
        try:
            val_str = str(value)
            val_str = val_str.replace(',', '').strip()
            return float(val_str)
        except (ValueError, TypeError):
            _logger.warning(f"Could not parse float value: {value}")
            return 0.0
    
    # inputFollowers = '6083, 36646, 37111'
    def save_memo_record(self, post, memo_id=None):
        _logger.info("SAVE POST DATA %s", post)

        env = request.env
        Memo = env['memo.model'].sudo()

        # ---------- Helpers ----------
        def _to_int(val):
            try:
                return int(val)
            except Exception:
                return False

        def _to_float(val):
            try:
                return float(val)
            except Exception:
                return 0.0

        def _to_date(val):
            if not val:
                return fields.Date.today()
            try:
                return datetime.strptime(val, "%m/%d/%Y")
            except Exception:
                return fields.Date.today()

        def _is_checked(field):
            return post.get(field) == "on"

        def _clean_id(field):
            val = post.get(field)
            return int(val) if val and str(val).isdigit() else False

        # ---------- Followers ----------
        inputFollowers = []
        if post.get('inputFollowers'):
            inputFollowers = [int(x.get('id')) for x in post.get('inputFollowers') if x]

        # ---------- Employee ----------
        employee = env['hr.employee'].sudo().search([
            ('user_id', '=', env.uid),
            ('employee_number', '=', post.get('staff_id'))
        ], limit=1)

        # ---------- Dates ----------
        leave_start_date = _to_date(post.get("leave_start_datex"))
        leave_end_date = _to_date(post.get("leave_end_datex")) if post.get("leave_end_datex") \
            else leave_start_date + relativedelta(days=1)

        # ---------- Config ----------
        memo_config = env['memo.config'].sudo().browse(_to_int(post.get("selectConfigOption")))

        # ---------- Existing Memo Reference ----------
        cash_advance_id = False
        existing_order = post.get("existing_order")

        if post.get("selectRequestOption") == "soe" and existing_order:
            if str(existing_order).isdigit():
                cash_advance_id = env['memo.model'].sudo().browse(int(existing_order))
            else:
                cash_advance_id = env['memo.model'].sudo().search([
                    ('code', '=ilike', existing_order)
                ], limit=1)

        # ---------- Processing Branch ----------
        processing_branch_id = _clean_id('processing_branch_id')
        processing_company_id = False

        if processing_branch_id:
            branch = env['multi.branch'].sudo().browse(processing_branch_id)
            processing_company_id = branch.company_id.id if branch.company_id else False

        processing_branch_id = processing_branch_id or memo_config.processing_branch_id.id
        processing_company_id = processing_company_id or memo_config.processing_company_id.id

        # ---------- Requirements Description ----------
        requirements = []

        option_fields = [
            ('applicationChange', 'Application change'),
            ('enhancement', 'Enhancement'),
            ('datapatch', 'Datapatch'),
            ('databaseChange', 'Database Change'),
            ('osChange', 'OS Change'),
            ('ids_on_os_and_db', 'Ids on OS and DB'),
            ('versionUpgrade', 'Version Upgrade'),
            ('hardwareOption', 'Hardware Option')
        ]

        for field, label in option_fields:
            if _is_checked(field):
                requirements.append(f"{label}: True")

        if post.get("other_system_details"):
            requirements.append(f"Other Changes: {post.get('other_system_details')}")

        if post.get("justification_reason"):
            requirements.append(f"Justification: {post.get('justification_reason')}")

        description_body = f"""
            <b>Description:</b> {post.get("description","")}<br/>
            <b>Requirements:</b><br/>{'<br/>'.join(requirements)}
        """

        # ---------- Values ----------
        vals = {
            "employee_id": employee.id,
            "memo_type": memo_config.memo_type.id,
            "memo_setting_id": memo_config.id,
            "memo_type_key": memo_config.memo_type.memo_key,

            "name": post.get("subject"),
            "email": post.get("email_from"),
            "phone": post.get("phone_number"),

            "amountfig": _to_float(post.get("amount_fig")),
            "date": _to_date(post.get("request_date")),

            "leave_start_date": leave_start_date,
            "leave_end_date": leave_end_date,

            "leave_Reliever": _clean_id("leave_reliever"),
            "vendor_id": _clean_id("vendor_id"),
            "currency_id": _clean_id("currency_id") or env.user.company_id.currency_id.id,

            "conversion_rate": _to_float(post.get("currency_rate")),

            "source_location_id": _clean_id("TargetSourceLocation"),
            "dest_location_id": _clean_id("destination_location_id"),

            "applicationChange": _is_checked("applicationChange"),
            "enhancement": _is_checked("enhancement"),
            "datapatch": _is_checked("datapatch"),
            "databaseChange": _is_checked("databaseChange"),
            "osChange": _is_checked("osChange"),
            "ids_on_os_and_db": _is_checked("ids_on_os_and_db"),
            "versionUpgrade": _is_checked("versionUpgrade"),
            "hardwareOption": _is_checked("hardwareOption"),

            "description": description_body,
            "users_followers": [(6, 0, inputFollowers)],

            "state": "submit",
            "stage_id": False if not memo_config.stage_ids else memo_config.stage_ids[0].id,
            "company_id": env.user.company_id.id,
            "branch_id": env.user.branch_id.id if env.user.branch_id else False,

            "cash_advance_reference": cash_advance_id.id if cash_advance_id else False,

            "processing_branch_id": processing_branch_id,
            "processing_company_id": processing_company_id,
        }

        _logger.info("FINAL VALS %s", vals)

        # ---------- Data Items ----------
        def _parse_json(value):
            if not value:
                return []
            if isinstance(value, (list, dict)):
                return value
            try:
                return json.loads(value)
            except Exception:
                _logger.warning("Invalid JSON value: %s", value)
                return []

        DataItems = _parse_json(post.get("DataItems"))
        # ---------- Create / Update ----------
        if not memo_id:
            memo_id = Memo.create(vals)
        else:
            memo_id = Memo.browse([memo_id])
            memo_id.sudo().write(vals)

        # ---------- Lines ----------
        if DataItems:
            if post.get("selectRequestOption") != "employee_update":
                self.generate_request_line(DataItems, memo_id)
            else:
                self.generate_employee_transfer_line(DataItems, memo_id)
        else:
            memo_id.product_ids = [(5,)]

        # ---------- Attachments ----------
        # if 'other_docs' in request.params:
        #     for file in request.httprequest.files.getlist('other_docs'):
        #         datas = base64.b64encode(file.read())
        #         self.generate_attachment(memo_id.code, file.filename, datas, memo_id.id, True)
        attachments = post.get('attachments', [])
        for file in attachments:
            datas = file.get('datas')
            filename = file.get('filename')
            if datas:
                self.generate_attachment(
                    memo_id.code,
                    filename,
                    datas.encode() if isinstance(datas, str) else datas,
                    memo_id.id,
                    True
                )
        # ---------- Subscribe Followers ----------
        partners = []
        for emp_id in inputFollowers:
            emp = env['hr.employee'].sudo().browse(emp_id)
            if emp.user_id:
                partners.append(emp.user_id.partner_id.id)

        memo_id.message_subscribe(partner_ids=partners)
        return memo_id

    def _get_employee(self):
        employee_id = request.env['hr.employee'].sudo().search([
                ('user_id', '=', request.env.uid), 
                # ('employee_number', '=', post.get('staff_id')
            ], limit=1)
        return employee_id

    @http.route('/request/api/save', type='json', auth='user', methods=['POST'])
    def save_Request(self, formData=None, request_id=None, lines=None, toSubmit=None, **kw):
        # toSubmit: indicate users wants to submit to manager
        employee = self._get_employee()
        # formData is now a Python dict
        memo_vals = formData

        request_id = self.save_memo_record(memo_vals, request_id)
        if toSubmit:
            approver_ids, next_stage_id = request_id.get_next_stage_artifact(request_id.stage_id, True)
            request_id.write({'stage_id': next_stage_id})
            _logger.info(f"SUBMITT {next_stage_id}")
            request_id.confirm_memo(
                    request_id.direct_employee_id or employee.parent_id, 
                    "",
                    from_website=True,
                    default_stage_id=request_id.stage_id.id
                    )
        request.session['memo_ref'] = request_id.code
        request.session['memo_record_id'] = request_id.id

        return {
            'message': 'Saved successfully',
            'request_id': request_id.id,
            'success': True,
        }

    @http.route(['/portal_data_process'], type='http', methods=['POST'], website=True, auth="user", csrf=False)
    def portal_data_process(self, **post):
        '''used to process portal data'''
        saveAction = post.get('saveAction')
        _logger.info(f"All posted data ======> {saveAction}")
        _logger.info(post)
        try:
            # inputFollowers = '6083, 36646, 37111'
            inputFollowers = [int(r) for r in str(post.get('inputFollowers')).split(',')] if post.get('inputFollowers') else [] 
            #request.httprequest.form.getlist('inputFollowers[]')  # get multiple values
            employee_id = request.env['hr.employee'].sudo().search([
                ('user_id', '=', request.env.uid), 
                ('employee_number', '=', post.get('staff_id'))], limit=1)
            if not employee_id:
                return json.dumps({'status': False, 'message': "No employee record found for staff id provided"})
            existing_request  = post.get("selectTypeRequest")
            existing_order = post.get("existing_order")
            memo_id = False
            if existing_request == "existing":
                memo_id = request.env['memo.model'].sudo().search([
                ('employee_id', '=', employee_id.id), 
                ('code', '=', existing_order)], limit=1)
                if not memo_id:
                    return json.dumps({'status': False, 'message': "No existing request found for the employee"})
            leave_start_date = datetime.strptime(post.get("leave_start_datex",''), "%m/%d/%Y") if post.get("leave_start_datex") else fields.Date.today()
            leave_end_date = datetime.strptime(post.get("leave_end_datex",''), "%m/%d/%Y") \
                if post.get("leave_start_datex") else leave_start_date + relativedelta(days=1)
            if post.get("selectRequestOption") == "soe" and existing_order:
                # existing_order may be an ID (from Select2) or a code string
                if str(existing_order).isdigit():
                    cash_advance_id = request.env['memo.model'].sudo().browse(int(existing_order))
                    if not cash_advance_id.exists():
                        cash_advance_id = False
                else:
                    cash_advance_id = request.env['memo.model'].sudo().search([
                        ('code', '=ilike', existing_order)], limit=1)
            else:
                cash_advance_id = False
            systemRequirementOptions = [
                'Application change : True' if post.get("applicationChange") == "on" else '',
                'Enhancement : True' if post.get("enhancement") == "on" else '',
                'Datapatch : True' if post.get("datapatch") == "on" else '',
                'Database Change : True' if post.get("databaseChange") == "on" else '',
                'OS Change : True' if post.get("osChange") == "on" else '',
                'Ids on OS and DB : True' if post.get("ids_on_os_and_db") == "on" else '',
                'Version Upgrade : True' if post.get("versionUpgrade") == "on" else '',
                'Hardware Option : True' if post.get("hardwareOption") == "on" else '',
                'Other Changes : ' + post.get("other_system_details", "") if post.get("other_system_details") else '', 
                'Justification reason : ' + post.get("justification_reason", "") if post.get("justification_reason") else '', 
                'Start date : ' + post.get("request_date",'') if post.get("request_date") else '', 
                'End date : ' + post.get("request_end_date",'') if post.get("request_end_date") else '', 
                ]
            description_body = f"""
            <b>Description: </b> {post.get("description", "")}<br/>
            <b>Requirements: </b> {'<br/>'.join([r for r in systemRequirementOptions if r ])}
            """
            memo_config = request.env['memo.config'].sudo().search([('id', '=', int(post.get("selectConfigOption")))], limit=1)

            def get_browsed_data(model, recid):
                data = request.env[f'{model}'].sudo().browse(int(recid))
                if data:
                    return data 
                else:
                    return False
            
            # 1. Capture the Processing District (Integration)
            processing_branch_id = False
            processing_company_id = False
            if post.get('processing_branch_id') and str(post.get('processing_branch_id')).isdigit():
                processing_branch_id = int(post.get('processing_branch_id'))
                branch_rec = request.env['multi.branch'].sudo().browse(processing_branch_id)
                if branch_rec.company_id:
                    processing_company_id = branch_rec.company_id.id
                    
            if not processing_branch_id and memo_config.processing_branch_id:
                processing_branch_id = memo_config.processing_branch_id.id
            if not processing_company_id and memo_config.processing_company_id:
                processing_company_id = memo_config.processing_company_id.id
                    

            vals = {
                "employee_id": employee_id.id,
                "memo_type": memo_config.memo_type.id,
                "memo_setting_id": memo_config.id,
                "memo_type_key": memo_config.memo_type.memo_key,
                "email": post.get("email_from"),
                "payment_reference": post.get("PaymentcashAdvance"),
                "phone": post.get("phone_number"),
                "name": post.get("subject", ''),
                # "amountfig": post.get("amount_fig", 0),
                "amountfig": self._parse_float(post.get("amount_fig")),
                "date": datetime.strptime(post.get("request_date",''), "%m/%d/%Y") if post.get("request_date") else fields.Date.today(), #format_to_odoo_date(post.get("request_date",'')),
                "leave_type_id": post.get("leave_type_id", ""),
                "leave_start_date": leave_start_date,
                "leave_end_date": leave_end_date,
                "leave_Reliever": int(post.get("leave_reliever")) if post.get("leave_reliever") not in ['false', False, None, '', 'none', 'None'] else False,
                "vendor_id": int(post.get("vendor_id")) if post.get("vendor_id") not in ['false', False, None, '', 'none', 'None'] else False,
                "currency_id": int(post.get("currency_id")) if post.get("currency_id") not in ['false', False, None, '', 'none', 'None'] else request.env.user.company_id.currency_id.id,
                "conversion_rate": int(post.get("currency_rate")) if post.get("currency_rate") not in ['false', False, None, '', 'none', 'None'] else 0,
                "customer_id": int(post.get("vendor_id")) if post.get("vendor_id") not in ['false', False, None, '', 'none', 'None'] else False,
                "source_location_id": post.get("TargetSourceLocation") if post.get("TargetSourceLocation") not in ['false', False, None, '', 'none', 'None', 0, '0'] else False,
                'dest_location_id': int(post.get("destination_location_id")) if post.get("destination_location_id") not in ['false', False,  None, '', 'none', 'None',0, '0'] else False,
                
                "is_inter_district_transfer": True if post.get("isInterDistrict") == "on" else False,
                "applicationChange": True if post.get("applicationChange") == "on" else False,
                "enhancement": True if post.get("enhancement") == "on" else False,
                "datapatch": True if post.get("datapatch") == "on" else False,
                "databaseChange": True if post.get("databaseChange") == "on" else False,
                "osChange": True if post.get("osChange") == "on" else False,
                "ids_on_os_and_db": True if post.get("ids_on_os_and_db") == "on" else False,
                "versionUpgrade": True if post.get("versionUpgrade") == "on" else False,
                "hardwareOption": True if post.get("hardwareOption") == "on" else False,
                "otherChangeOption": True if post.get("otherChangeOption") == "on" else False,
                "other_system_details": post.get("other_system_details"),
                "justification_reason": post.get("justification_reason"),
                "state": "Sent",
                "company_id": request.env.user.company_id.id,
                "branch_id": request.env.user.branch_id and request.env.user.branch_id.id,
                # "currency_id": request.env.user.company_id.currency_id.id,
                "cash_advance_reference": cash_advance_id.id if cash_advance_id else False,
                "users_followers": [(6, 0, inputFollowers)], 
                "description": description_body, 
                "request_date": datetime.strptime(post.get("request_date",''), "%m/%d/%Y") if post.get("request_date") else fields.Date.today(),
                "request_end_date": datetime.strptime(post.get("request_end_date",''), "%m/%d/%Y") if post.get("request_end_date") else False,
                "processing_branch_id": processing_branch_id,
                "processing_company_id": processing_company_id,
            }
            _logger.info(f"POST DATA {vals}")
            _logger.info(f"""Accreditation ggeenn geen===>  {json.loads(post.get('DataItems'))}""")
            DataItems = []
            DataItems = json.loads(post.get('DataItems'))
            memo_obj = request.env['memo.model']
            if not memo_id:
                _logger.info("Request id creating")
                memo_id = memo_obj.sudo().create(vals)
            else:
                _logger.info("Request id updating")
                memo_id.sudo().write(vals)
            if DataItems:
                _logger.info(f'DATA ITEMS IDS IS HERE {DataItems}')
                if post.get("selectRequestOption") != "employee_update":
                    self.generate_request_line(DataItems, memo_id)
                else: 
                    self.generate_employee_transfer_line(DataItems, memo_id)
            
            ## generating attachment
            if 'other_docs' in request.params:
                attached_files = request.httprequest.files.getlist('other_docs')
                for attachment in attached_files:
                    file_name = attachment.filename
                    datas = base64.b64encode(attachment.read())
                    other_docs_attachment = self.generate_attachment(memo_id.code, file_name, datas, memo_id.id)
            # memo_id.action_submit_button()
            memo_id.message_subscribe(partner_ids=[get_browsed_data('hr.employee', id) and get_browsed_data('hr.employee', id).user_id.partner_id.id for id in inputFollowers])
            stage_id = memo_id.get_initial_stage(
                memo_config.id,
                )
            _logger.info(f'''initial stage come be {stage_id} memo type => {memo_id.memo_type_key} and department {memo_id.employee_id.department_id.name}''')
            
            # Note: get_next_stage_artifact might return a list of potential approvers
            approver_ids, next_stage_id = memo_id.get_next_stage_artifact(stage_id, True)
            
            if not approver_ids and not next_stage_id:
                _logger.info(f'''Friendly approvers {approver_ids} memo type => {next_stage_id}''')
                return json.dumps({'status': False, 'message': "Please ensure to configure the Memo type\n for the employee department!"})
                # return {'status': False, 'message': "Please ensure to configure the Memo type\n for the employee department!"}

            stage_obj = request.env['memo.stage'].sudo().search([('id', '=', next_stage_id)])
            
            # === START OF IMPROVED ROUTING LOGIC ===
            potential_approvers = stage_obj.approver_ids
            final_approver_id = False

            # 1. Priority: Filter by Processing District (if one was selected)
            if processing_branch_id and potential_approvers:
                district_specific_approver = potential_approvers.filtered(
                    lambda emp: emp.branch_id.id == processing_branch_id
                )
                if district_specific_approver:
                    final_approver_id = district_specific_approver[0].id
                    _logger.info(f"Routing: Found specific approver for district: {district_specific_approver[0].name}")
                else:
                    _logger.warning(f"Routing: Selected district {processing_branch_id} has no matching approver in stage {stage_obj.name}. Falling back.")

            # 2. Fallback: Standard Random Selection (Line Manager or Stage Approvers)
            if not final_approver_id:
                # Use potential_approvers from stage, or fall back to parent_id if stage has no approvers
                available_ids = potential_approvers.ids if potential_approvers else [employee_id.parent_id.id] if employee_id.parent_id else []
                
                if available_ids:
                    final_approver_id = random.choice(available_ids)

            # Final Validation
            if not final_approver_id:
                return json.dumps({'status': False, 'message': "Configuration Error: No approver found for the next stage."})

            # Standard follower logic
            follower_ids = [(4, final_approver_id)]
            user_ids = [(4, request.env.user.id)]
            if employee_id.administrative_supervisor_id:
                follower_ids.append((4, employee_id.administrative_supervisor_id.id))
            if employee_id.parent_id:
                follower_ids.append((4, employee_id.parent_id.id))

            memo_id.sudo().update({
                'stage_id': next_stage_id, 
                'approver_id': final_approver_id,
                'set_staff': final_approver_id,
                # Using (6, 0, [id]) to explicitly set the authorized approver for this stage
                'approver_ids': [(6, 0, [final_approver_id])],
                "direct_employee_id": final_approver_id,
                'users_followers': follower_ids,
                'res_users': user_ids,
                'memo_setting_id': stage_obj.memo_config_id.id,
                'memo_type_key': memo_id.memo_type_key or memo_id.memo_key,
            })
            _logger.info(f'''
                Successfully Registered! with approver = {final_approver_id} \
                    stage {next_stage_id}''')
            # === END OF IMPROVED ROUTING LOGIC ===
            
            saveAction = True if saveAction in ['true', 'True', True] else False
            if saveAction:
                _logger.info(f"submitting action done 1 {saveAction}")
                '''This saves the record and set the stage to the initial
                configure stage of the memo settings'''
                if memo_id.memo_setting_id.stage_ids:
                    memo_id.stage_id = memo_id.memo_setting_id.stage_ids[0]
                    memo_id.state = 'submit'
                else:
                    memo_id.stage_id = False
                    memo_id.state = 'submit'
            else:
                _logger.info(f"submitting action done 2 {saveAction}")
                memo_id.confirm_memo(
                    memo_id.direct_employee_id or employee_id.parent_id, 
                    post.get("description", ""),
                    from_website=True
                    )
            request.session['memo_ref'] = memo_id.code
            request.session['memo_record_id'] = memo_id.id
            return json.dumps({'status': True, 'message': "Form Submitted!", "request_id": memo_id.id})
        except Exception as ex:
            _logger.exception("Unexpected Error while sending ERP Request: %s" % ex)
            return json.dumps({'status': False, 'message': "Form Submitted!"})
    
    def update_request_line(self, DataItems, memo_id):
        message = []
        for rec in DataItems:
            desc = rec.get('description', '')
            _logger.info(f"UPDATING REQUESTS INCLUDES=====> MEMO IS {memo_id} -ID {memo_id.id} ---{rec}")
            request_vals = { 
                    'quantity_available': float(rec.get('qty').replace(',', '')) if rec.get('qty') else 0,
                    'description': BeautifulSoup(desc, features="lxml").get_text(),
                    'used_qty': rec.get('used_qty'),
                    'amount_total': float(rec.get('amount_total').replace(',', '')),
                    'used_amount': rec.get('used_amount'),
                    'note': rec.get('note'), 
                    'to_retire': True if rec.get('line_checked') in ['on', 'On'] else False,
                    'distance_from': rec.get('distance_from'),
                    'distance_to': rec.get('distance_to'),
                }
            _logger.info(f"UPDATED REQUESTS with VALS =====> {request_vals} ")
            # productid = 0 if rec.get('product_id') in ['false', False, 'none', None] or not rec.get('product_id').isdigit() else rec.get('product_id') 
            request_line = request.env['request.line'].sudo().search([('id', '=', int(rec.get('request_line_id'))), ('memo_id', '=', memo_id.id)])
            if not request_line:
                message.error(f"No request line with this memo ID {memo_id.id} found on the system")
            if rec.get('product_id') and rec.get('product_id').isdigit():
                # raise ValidationError(f"{rec.get('product_id')}")
                product_id = request.env['product.product'].sudo().browse([int(rec.get('product_id'))])
                if product_id:
                    request_vals.update({
                        'product_id': product_id.id, 
                    })
                else:
                    message.error(f"No product with ID {rec.get('product_id')} found on the system")
            request_line.update(request_vals)
        
    def generate_request_line(self, DataItems, memo_id):
        memo_id.sudo().write({'product_ids': False})
        counter = 1
        for rec in DataItems:
            desc = rec.get('description', '')
            line_source_location_id = memo_id.source_location_id.id or rec.get('location_id') 
            line_source_location_id = False if line_source_location_id in ['false', False, 'none', None, 0, '0', 'undefined'] else line_source_location_id
            line_dest_location_id = memo_id.dest_location_id.id if memo_id.dest_location_id else rec.get('dest_location_id')
            line_dest_location_id = False if line_dest_location_id in ['false', False, 'none', None, 0, '0', 'undefined'] else line_dest_location_id
            
            _logger.info(f"REQUESTS INCLUDES=====> MEMO IS {memo_id} -ID {memo_id.id} ---{rec} location is {line_source_location_id}")
            
            qty = self._parse_float(rec.get('qty'))
            amount_total = self._parse_float(rec.get('amount_total'))
            used_qty = self._parse_float(rec.get('used_qty'))
            used_amount = self._parse_float(rec.get('used_amount'))
            
            request_vals = {
                'memo_id': memo_id.id,
                'memo_type': memo_id.memo_type.id,
                'memo_type_key': memo_id.memo_type_key,
                # 'quantity_available': float(rec.get('qty')) if rec.get('qty') else 0,
                'quantity_available': qty,
                'description': BeautifulSoup(desc, features="lxml").get_text(),
                # 'used_qty': rec.get('used_qty'),
                'used_qty': used_qty,
                # 'amount_total': rec.get('amount_total'),
                'amount_total': amount_total,
                # 'used_amount': rec.get('used_amount'),
                'used_amount': used_amount,
                'note': rec.get('note'),
                'source_location_id': line_source_location_id,
                'dest_location_id': line_dest_location_id,
                'request_line_id': int(rec.get('request_line_id')) if rec.get('request_line_id') else 0,
                'to_retire': True if rec.get('line_checked') in ['on', 'On'] else False,
                'distance_from': rec.get('distance_from'),
                'distance_to': rec.get('distance_to'),
            }
            _logger.info(f"REQUESTS VALS =====> {rec.get('line_checked')} == valxxx [{request_vals}]")
            product_data = rec.get('product_id')
            productid = 0 if product_data in ['false', False, 'none', None] or type(product_data) not in [int] else product_data
            product_id = request.env['product.product'].sudo().browse([int(productid)])
            if product_id:
                request_vals.update({
                    'product_id': product_id.id, 
                })
            request.env['request.line'].sudo().create(request_vals)
            counter += 1
    
    def generate_employee_transfer_line(self, DataItems, memo_id):
        counter = 1
        for rec in DataItems:
            _logger.info(f"REQUESTS INCLUDES=====> MEMO IS {memo_id} -ID {memo_id.id} ---{rec}")
            transfer_line = request.env['hr.employee.transfer.line'].sudo()
            employee = request.env['hr.employee'].sudo()
            department = request.env['hr.department'].sudo()
            role = request.env['hr.job'].sudo()
            district = request.env['multi.branch'].sudo()
            employee_id = employee.browse([int(rec.get('employee_id'))]) if rec.get('employee_id') else False
            transfer_dept_id = department.browse([int(rec.get('transfer_dept'))]) if rec.get('transfer_dept') else False
            role_id = role.browse([int(rec.get('new_role'))]) if rec.get('new_role') else False
            district_id = district.browse([int(rec.get('new_district'))]) if rec.get('new_district') else False
            # district_id = district.browse([int(rec.get('new_district'))]) if rec.get('new_district') else False

            if employee_id and transfer_dept_id and role_id: 
                transfer_line.create({
                    'memo_id': memo_id.id,
                    'employee_id': employee_id.id, 
                    'transfer_dept': transfer_dept_id.id,
                    'current_dept_id': employee_id.department_id.id,
                    'new_role': role_id.id,
                    'new_district': district_id.id,
                    # 'new_district': district_id.id, 
                })
            counter += 1

    # def get_pagination(self, page):
    #     sessions = request.session  
    #     session_start_limit = sessions.get('start')
    #     session_end_limit = sessions.get('end')
    #     if page == "next":
    #         s = session_end_limit 
    #         e = session_end_limit + 10
    #     elif page == 'prev': 
    #         # e.g start 20 , end 30
    #         s = session_start_limit - 10
    #         e = session_end_limit - 10
    #         # sessions['start'] = s 
    #         # sessions['end'] = e
    #     else:
    #         s = 0 
    #         e = 10
    #     return s, e
    
    def get_pagination(self, page):
        """Helper method to handle pagination logic"""
        sessions = request.session
        PAGE_SIZE = 10
        
        if page == 'next':
            start = sessions.get('start', 0) + PAGE_SIZE
            end = sessions.get('end', PAGE_SIZE) + PAGE_SIZE
        elif page == 'prev':
            start = max(0, sessions.get('start', 0) - PAGE_SIZE)
            end = sessions.get('end', PAGE_SIZE) - PAGE_SIZE
            if end < PAGE_SIZE:
                end = PAGE_SIZE
        else:
            start = sessions.get('start', 0)
            end = sessions.get('end', PAGE_SIZE)
        
        return start, end
    
    def get_request_info(self, request):
        """
        Returns context data extracted from :param:`request`.
        """
        urlparts = urllib.parse.urlsplit(request.url)
        query_string = urlparts.query
        _logger.info(f"URL PARTS = {urlparts} QUERY STRING IS {query_string}")
        
    def _get_memo_display_name(self, memo_key):
        """Return user-friendly display name for memo types"""
        display_names = {
            'soe': 'Retirement',
            'cash_advance': 'Cash Advance',
            'leave_request': 'Leave',
            'material_request': 'Material Request',
            'procurement_request': 'Procurement',
            'vehicle_request': 'Vehicle Request',
            'server_access': 'Server Access',
            'employee_update': 'Employee Update',
            'Payment': 'Payment',
            'sale_request': 'Sales Request',
        }
        if not memo_key:
            return "Request" 
        return display_names.get(memo_key, memo_key.replace('_', ' ').title())


    
    @http.route([
    '/my/requests', 
    '/my/requests/<string:type>', 
    '/my/requests/<string:type>/page/<string:page>',
    '/my/requests/<string:type>/jump/<int:page_num>',
    '/my/requests/param/<path:search_param>',
    '/my/requests/param', 
    '/my/requests/page/<string:page>'], 
    type='http', auth="user", website=True)
    def my_requests(self, type=False, page=False, page_num=None, search_param=None, **kw):
        """This route displays user records with enhanced filtering
        page: pagination index (prev/next)
        type: request type (material_request, etc)
        filter: filter type (all, to_approve, own, related, approved_by_me, completed, refused, cancelled)
        """
        user = request.env.user
        sessions = request.session
        
        PAGE_SIZE = 10
        
        filter_type = request.params.get('filter', 'all')
        
        if page_num:
            start = (page_num - 1) * PAGE_SIZE
            end = page_num * PAGE_SIZE
            sessions['start'] = start
            sessions['end'] = end
        elif not page: 
            sessions['start'] = 0 
            sessions['end'] = PAGE_SIZE
            
        search_input_query2 = request.params.get('search')
        _logger.info(f"Search test {search_input_query2} {request.params.get('searchme')}, "
                    f"search_input_panel == {request.params.get('search_input_panel')}")
        
        search_input_query = request.params.get('searchme')
        search_param = request.params.get('search_param')
        search_input_panel = request.params.get('search_input_panel')

        all_memo_type_keys = [rec.memo_key for rec in request.env['memo.type'].sudo().search([])]
        
        memo_type = ['Payment', 'Loan'] if type in ['Payment', 'Loan'] \
            else ['soe'] if type == 'soe' \
            else ['cash_advance'] if type == 'cash_advance' \
            else ['leave_request'] if type in ['leave_request'] \
            else ['employee_update'] if type in ['employee_update'] \
            else ['Internal', 'procurement_request', 'sale_request', 'vehicle_request', 'material_request'] \
                if type in ['Internal', 'procurement_request', 'server_access', 'sale_request', 
                        'vehicle_request', 'material_request'] \
            else all_memo_type_keys
                                
        def get_date_query(date_query):
            """Parse date from various formats"""
            date_val = None
            if date_query:
                for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                    try:
                        date_val = datetime.strptime(date_query, fmt).date()
                        break
                    except ValueError:
                        pass 
            return date_val 
        
        memo_obj = request.env['memo.model'].sudo()
        
        def get_cancelled_request_ids():
            """
            Get IDs of cancelled requests by checking action history.
            A request is considered cancelled if:
            1. It has a 'cancelled' action in history, OR
            2. It's in 'submit' state AND has previous approval/rejection actions
            (meaning it was reset after being processed)
            """
            cancelled_ids = []
            
            history_cancelled = request.env['memo.action.history'].sudo().search([
                ('action', '=', 'cancelled')
            ]).mapped('memo_id.id')
            cancelled_ids.extend(history_cancelled)
            
            all_histories = request.env['memo.action.history'].sudo().search([
                ('action', 'in', ['approved', 'rejected', 'returned'])
            ])
            
            for history in all_histories:
                memo = history.memo_id
                if memo.state == 'submit':
                    latest_action = request.env['memo.action.history'].sudo().search([
                        ('memo_id', '=', memo.id)
                    ], order='action_date desc', limit=1)
                    
                    if latest_action and latest_action.action in ['approved', 'rejected', 'returned']:
                        actions_after = request.env['memo.action.history'].sudo().search([
                            ('memo_id', '=', memo.id),
                            ('action_date', '>', latest_action.action_date)
                        ])
                        
                        if not actions_after and memo.id not in cancelled_ids:
                            cancelled_ids.append(memo.id)
            
            return list(set(cancelled_ids))
        
        def get_filter_domain(filter_type, user, memo_type):
            """Build domain based on filter type"""
            base_domain = [('active', '=', True)]
            
            if memo_type and memo_type != all_memo_type_keys:
                base_domain.append(('memo_type_key', 'in', memo_type))
            
            # Base access domain - user must have some relation to the request
            access_domain = [
                '|', '|', '|', '|', '|',
                ('employee_id.user_id.id', '=', user.id),
                ('users_followers.user_id.id', '=', user.id),
                ('employee_id.administrative_supervisor_id.user_id.id', '=', user.id),
                ('employee_id.parent_id.user_id.id', '=', user.id),
                ('memo_setting_id.approver_ids.user_id.id', '=', user.id),
                ('stage_id.approver_ids.user_id.id', '=', user.id),
            ]
            
            if filter_type == 'to_approve':
                return base_domain + [
                    '|', '|',
                    ('memo_setting_id.approver_ids.user_id.id', '=', user.id),
                    ('stage_id.approver_ids.user_id.id', '=', user.id),
                    ('approver_id.user_id.id', '=', user.id),
                    ('state', 'not in', ['approved', 'done', 'cancel', 'Refuse'])
                ]
            
            elif filter_type == 'own':
                return base_domain + [
                    ('employee_id.user_id.id', '=', user.id)
                ]
            
            elif filter_type == 'related':
                return base_domain + [
                    ('employee_id.user_id.id', '!=', user.id),
                    '|', '|',
                    ('users_followers.user_id.id', '=', user.id),
                    ('employee_id.administrative_supervisor_id.user_id.id', '=', user.id),
                    ('employee_id.parent_id.user_id.id', '=', user.id),
                ]
            
            elif filter_type == 'approved_by_me':
                return base_domain + [
                    ('action_history_ids.actor_id.user_id', '=', user.id),
                    ('action_history_ids.action', '=', 'approved'),
                ]
            
            elif filter_type == 'completed':
                return base_domain + access_domain + [
                    '|',
                    ('state', 'in', ['done', 'approved']),
                    ('stage_id.name', 'ilike', 'done')
                ]
            
            elif filter_type == 'refused':
                return base_domain + access_domain + [
                    ('state', '=', 'Refuse')
                ]
            
            elif filter_type == 'cancelled':
                cancelled_ids = get_cancelled_request_ids()
                if not cancelled_ids:
                    return [('id', '=', False)]
                return base_domain + access_domain + [
                    ('id', 'in', cancelled_ids)
                ]
            
            else:
                return base_domain + access_domain
        
        domain = get_filter_domain(filter_type, user, memo_type)
        
        if search_input_query or search_input_panel:
            qry_param = search_input_query or search_input_panel
            _logger.info(f"Applying search query: {qry_param}")
            
            search_domain = [
                '|', ('code', 'ilike', qry_param),
                ('name', 'ilike', qry_param),
            ]
            
            date_search = get_date_query(qry_param)
            if date_search:
                search_domain += [
                    '|', ('request_date', '=', date_search), 
                    ('create_date', '=', date_search)
                ]
            
            domain = domain + search_domain
        
        total_count = memo_obj.search_count(domain)
        
        start, end = self.get_pagination(page)
        if page_num:
            max_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE if total_count > 0 else 1
            if page_num < 1:
                page_num = 1
                start = 0
                end = PAGE_SIZE
            elif page_num > max_pages:
                page_num = max_pages
                start = (page_num - 1) * PAGE_SIZE
                end = page_num * PAGE_SIZE
        
        _logger.info(f"Pagination: start={start}, end={end}, total={total_count}, filter={filter_type}")
        
        memo_records = memo_obj.search(
            domain, 
            order='create_date desc', 
            limit=PAGE_SIZE, 
            offset=start
        )

        if memo_records:
            sessions['start'] = start
            sessions['end'] = min(start + PAGE_SIZE, total_count)
        
        current_page = (start // PAGE_SIZE) + 1 if start >= 0 else 1
        total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE if total_count > 0 else 1
        has_prev = start > 0
        has_next = (start + PAGE_SIZE) < total_count
        
        values = {
            'requests': memo_records,
            'memo_requests': memo_records,
            'current_memo_type_key': type if type else False,
            'current_memo_display_name': self._get_memo_display_name(type) if type else 'All',
            'current_filter': filter_type,
            'page_name': 'my_requests',
            'current_page': current_page,
            'total_pages': total_pages,
            'total_count': total_count,
            'has_prev': has_prev,
            'has_next': has_next,
            'page_size': PAGE_SIZE,
            'search': search_input_query or search_input_panel or '',
        }
        
        _logger.info(f"Rendering with current_page={current_page}, total_pages={total_pages}, "
                    f"has {len(memo_records)} records, filter={filter_type}")
        
        return request.render("portal_request.my_portal_request", values)
    
    
    
    # def get_leave_days_taken(self, record):
    #     if record and record.leave_end_date and record.leave_start_date:
    #         duration = record.leave_end_date - record.leave_start_date
    #         return duration.days if duration else 0
    #     else:
    #         return 0
    def get_leave_days_taken(self, record):
        if record and record.leave_end_date and record.leave_start_date:
            start = record.leave_start_date
            end = record.leave_end_date

            day_count = 0
            current = start

            while current <= end:
                # Monday = 0 ... Sunday = 6
                if current.weekday() < 5:  # exclude Saturday(5) and Sunday(6)
                    day_count += 1
                current += timedelta(days=1)

            return day_count
        else:
            return 0

    @http.route("/print/memo/invoice/<int:id>",
                type='http', auth="user", website=True, csrf=False)
    def view_result(self, id, **kwargs):
        """View Invoice.
        """
        memo_id = id # kwargs.get('memo_id')
        # memoRecord = request.env['memo.model'].sudo().search([('id', '=', int(memo_id))], limit=1)
        invoice = request.env['account.move'].sudo().search([('memo_id', '=', int(memo_id))], limit=1)
        payment = request.env['account.payment'].sudo().search([('memo_reference', '=', int(memo_id))], limit=1)
        template = ""
        id_render = 0
        if invoice:
            template = "account.account_invoices"
            id_render = invoice.id

        elif payment:
            template = "account.action_report_payment_receipt"
            id_render = payment.id
        _logger.info(f"WHICH TEMPLATE NEEDED TO BE PRINTED {template}")
        report_id = request.env.ref(template) 
        if not report_id:
            _logger.info(f"NO TEMPLATE STILL FOUND {template}")
            pass #raise NotFound(f"No template found for printing {template}")
        else:
            # pdf, report_format = report_id.sudo().render_qweb_pdf(report_id, id_render)
            pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(template, [id_render])
   
            pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', u'%s' %
                                                  len(pdf)), 
            ('Content-Disposition', 'inline; filename={}'.format(invoice and invoice.id or payment and payment.id))]
            return request.make_response(pdf, headers=pdfhttpheaders)
    

    # @http.route(['/check-employee-still-onleave'], type='json', website=True, auth="user", csrf=False)
    # def employee_still_on_leave(self, **post):
    #     '''Check if employee is absent and return a validation message'''
    #     employee_id = post.get('employee_id', 0)
    #     start_date = post.get('start_date')
    #     end_date = post.get('end_date')
    #     _logger.info(f"lost for {post}")
    #     employee_obj = request.env['hr.employee'].sudo().browse([int(employee_id or 0)])
    #     _logger.info(f'WHO IS EMPLOYEE {employee_obj}')
    #     if employee_obj and employee_obj.hr_icon_display in ['presence_holiday_present', 'presence_holiday_absent']:
    #         '''Check if employee is on leave and return validation message'''
    #         msg = """The employee to relieve you is currently on leave / Absent"""
    #         return {
    #             "status": False,
    #             "message": msg, 
    #             } 
    #     else:
    #         _logger.info('EMPLOYEE NOT ON LEAVE')
    #         return {
    #             "status": True,
    #             "message": "", 
    #             }
    
    @http.route(['/check-employee-still-onleave'], type='json', website=True, auth="user", csrf=False)
    def employee_still_on_leave(self, **post):
        '''Check if employee has a conflicting leave during the requested period'''
        employee_id = post.get('employee_id', 0)
        start_date_str = post.get('start_date')
        end_date_str = post.get('end_date')
        
        if not employee_id:
            return {"status": True, "message": ""}

        employee_obj = request.env['hr.employee'].sudo().browse([int(employee_id)])
        
        start_date_dt = self.compute_date_format(start_date_str)
        end_date_dt = self.compute_date_format(end_date_str)

        if not start_date_dt or not end_date_dt:
            return {"status": True, "message": ""}

        start_date = start_date_dt.date()
        end_date = end_date_dt.date()

        domain = [
            ('employee_id', '=', employee_obj.id),
            ('state', 'in', ['validate', 'validate1']),
            ('request_date_from', '<=', end_date),
            ('request_date_to', '>=', start_date),
        ]
        
        conflicting_leave = request.env['hr.leave'].sudo().search(domain, limit=1)

        if conflicting_leave:
            l_start = conflicting_leave.request_date_from.strftime('%d-%b-%Y')
            l_end = conflicting_leave.request_date_to.strftime('%d-%b-%Y')
            
            msg = f"""The selected reliever ({employee_obj.name}) has an approved leave from {l_start} to {l_end} which conflicts with your request period."""
            return {
                "status": False,
                "message": msg, 
            } 
        
        return {
            "status": True,
            "message": "", 
        }
   
    @http.route('/my/request/view/<string:id>', type='http', auth="user", website=True)
    def my_single_request(self, id):
        id = int(id) if id else 0
        """This route is used to call the requesters or user record for display"""
        
        referer = request.httprequest.environ.get('HTTP_REFERER', '/my/requests')
        back_url = '/my/requests'
        if 'memo_type' in referer or '/my/requests/' in referer:
            back_url = referer
            
        user = request.env.user
        request_id = request.env['memo.model'].sudo()
        attachment = request.env['ir.attachment'].sudo()
        domain = [
                ('active', '=', True),
                # ('employee_id.user_id', '=', user.id),
                ('id', '=', int(id)),
                '|','|','|','|','|',
                ('employee_id.user_id', '=', user.id),
                ('users_followers.user_id','=', user.id),
                ('employee_id.administrative_supervisor_id.user_id.id','=', user.id),
                ('employee_id.parent_id.user_id.id','=', user.id),
                ('memo_setting_id.approver_ids.user_id.id','=', user.id),
                ('stage_id.approver_ids.user_id.id','=', user.id),
            ]
        requests = request_id.search(domain, limit=1)
        memo_attachment_ids = attachment.search([
            ('res_model', '=', 'memo.model'),
            ('res_id', '=', requests.id)
            ])
        leave_allocation = request.env['hr.leave.allocation'].sudo()
        leave_allocation_id = leave_allocation.search([
                    ('holiday_status_id', '=', int(requests.leave_type_id.id)),
                    ('employee_id', '=', requests.employee_id.id),
                    ])
        number_of_days_display, leaves_taken = 0, 0
        for lv in leave_allocation_id:
            number_of_days_display += lv.number_of_days_display 
            leaves_taken += lv.leaves_taken
        number_of_days_display = number_of_days_display - leaves_taken
        values = {
            'req': requests,
            # 'format_date': lambda date, fmt='%m/%d/%Y': format_date(request.env, date, date_format=fmt),
            'is_edit_mode': 'on' if requests.state in ['draft', 'submit', 'refuse', 'cancel'] else 'off',
               'leave_taken': self.get_leave_days_taken(requests),
            'current_user': user.id,
            'staff_num': user.id,
               'employee_ids': request.env['hr.employee'].sudo().search([('active', '=', True)]),
            "leave_type_ids": request.env["hr.leave.type"].sudo().search([]),
            'record_attachment_ids': memo_attachment_ids,
            # "number_of_days_display": requests.employee_id.allocation_remaining_display, # leave_allocation_id.number_of_days_display,
            "number_of_days_display": number_of_days_display,#leave_allocation_id.number_of_days_display,
            "description_body": BeautifulSoup(requests.description or "-", "html.parser").get_text(),
            'back_url': back_url,
            'memo_display_name': self._get_memo_display_name(requests.memo_type_key),
        }
        return request.render("portal_request.request_form_template", values) 
    
    @http.route('/user/approver', type='json', auth='user', website=True)
    def check_user_is_approver(self, **post):
        _logger.info(f"checking user is approver / refuser of the request ...{post.get('memo_id')}")
        user = request.env.user	
        # domain = [('id', '=', post.get('memo_id'))]
        # request_id = request.env['memo.model'].sudo()
        rec = request.env['memo.model'].sudo().browse([int(post.get('memo_id'))])
        if rec:
            manager_approve = []
            approver_ids = [r.user_id.id for r in rec.sudo().stage_id.approver_ids]
            
            if rec.sudo().state == 'Refuse':
                return {
                    "status": True,
                    "warning": True, 
                    "message": "The record is already in refuse state. Kindly cancel, resend or approve", 
                    }
            if rec.sudo().stage_id.id in rec.memo_setting_id.stage_ids.ids:
                if rec.memo_setting_id.stage_ids.ids.index(rec.sudo().stage_id.id) in [0, 1]:
                    manager_approve = [rec.employee_id.administrative_supervisor_id.user_id.id, rec.employee_id.parent_id.user_id.id]
            approver_ids = manager_approve + approver_ids
            if rec.stage_id and user.id not in approver_ids: 
                return {
                    "status": True, 
                    "warning": True, 
                    "message": "You are not authorized to refuse this request", 
                    }
            else:
                return {
                    "status": True, 
                    "warning": False, 
                    "message": "", 
                    }
        else:
            return {
                    "status": False, 
                    "warning": False, 
                    "message": "No reference record couls be found to refuse this request", 
                    }


    
    # @http.route('/my/request/update', type='json', auth="user", website=True)
    # def update_my_request(self, **post):
    #     _logger.info(f"updating the request ...{post.get('memo_id')}")
    #     user = request.env.user
    #     request_id = request.env['memo.model'].sudo()
    #     domain = [
    #         # ('employee_id.user_id', '=', user.id),
    #         ('id', '=', post.get('memo_id')),
    #         # ('state', 'in', ['Refuse']),
    #     ]
    #     request_record = request_id.search(domain, limit=1)
    #     stage_id = False
    #     status = post.get('status', '')

    #     if request_record:
    #         if status == "cancel":
    #             stage_id = request.env.ref('company_memo.memo_cancel_stage').id
                
    #             request_record._log_action(
    #                 action='cancelled',
    #                 comments='Cancelled via portal'
    #             )
                
    #             body_msg = f"""
    #                 Dear Sir / Madam, <br/>
    #                 I wish to notify you that a request with description \n <br/>\
    #                 has been cancel by {request.env.user.name} <br/>\
    #                 Kindly {get_url(request_record.id)}"""
    #             request_record.mail_sending_direct(body_msg)
    #             request_record.write({
    #                 'state': 'Refuse', 
    #                 'stage_id': stage_id,
    #                 })
    #             return {
    #                 "status": True, 
    #                 "link": False, 
    #                 "message": "Record updated successfully", 
    #                 }
            
    #         elif status == "Sent":
    #             stage_id = request_record.sudo().memo_setting_id.stage_ids[0].id if \
    #                 request_record.sudo().memo_setting_id.stage_ids else \
    #                     request.env.ref('company_memo.memo_cancel_stage').id
    #             request_record.sudo().write({'state': 'Sent', 'stage_id': stage_id})
    #             return {
    #                 "status": True, 
    #                 "link": False, 
    #                 "message": "Record updated successfully", 
    #                 }
            
    #         elif status in ["Resend"]:
    #             # useds this to determine the stages configured on the system
    #             # if the length of stages is just 1, try the first condition else,
    #             # set the stage to the next stage after draft.
    #             if not request.env.user.id == request_record.employee_id.user_id.id:
    #                 return {
    #                     "status": False, 
    #                     "link": False, 
    #                     "message": "Only initiator can resend this request", 
    #                     }
                
    #             memoStage_ids = request_record.sudo().memo_setting_id.stage_ids.ids 
    #             if memoStage_ids:
    #                 stage_id = memoStage_ids[0] if len(memoStage_ids) < 1 else memoStage_ids[1]
    #                 next_stage = request.env['memo.stage'].browse(stage_id)
                    
    #                 request_record._log_action(
    #                     action='submitted',
    #                     comments='Resubmitted via portal',
    #                     next_stage=next_stage
    #                 )
                    
    #                 request_record.write({'state': 'Sent', 'stage_id': stage_id})
    #                 return {
    #                     "status": True, 
    #                     "link": False,
    #                     "message": "Record updated successfully", 
    #                     }
    #             else:
    #                 return {
    #                 "status": False, 
    #                 "link": False, 
    #                 "message": "No stage configured or found for this request. Contact admin", 
    #                 }
            
    #         elif status in ["Approve"]:
                
    #             # approver_ids, stage = request_record.get_next_stage_artifact()
    #             current_stage_approvers = request_record.sudo().stage_id.approver_ids
    #             manager_approvals = []
    #             if request_record.sudo().memo_setting_id.stage_ids.ids.index(request_record.sudo().stage_id.id) in [0, 1]:
    #                 manager_approvals = [request_record.sudo().employee_id.parent_id.user_id.id, request_record.sudo().employee_id.administrative_supervisor_id.user_id.id]
    #             # user_employeeid = request.env.user.employee_id.id
    #             if not request.env.user.id in [r.user_id.id for r in current_stage_approvers] + manager_approvals:
    #                 if not (request_record.supervisor_comment or request_record.manager_comment):
    #                     return {
    #                         "status": False, 
    #                         "link": False,
    #                         "message": "Please Scroll down to the ending of the form to provide manager's or supervisor's comment", 
    #                         }
    #                 else:
    #                     return {
    #                         "status": False, 
    #                         "link": False,
    #                         "message": "You are not assigned to approve this record", 
    #                         }
    #             """First check if the server """
    #             # ensure that current stage is not the main approval stage. Only internal users
    #             # can go into office memo to approve
    #             if request_record.sudo().stage_id.is_approved_stage:
    #                 url_link = get_model_url(request_record.id, 'memo.model')
    #                 is_internal_user = request.env.user.has_group('base.group_user')
    #                 _logger.info(f"LINKAGE {url_link} Internal user found {is_internal_user}")
    #                 return {
    #                         "status": False, 
    #                         "link": get_model_url(request_record.id, 'memo.model') if is_internal_user else False,
    #                         "message": """Click the 'VIEW AS A CORE USER' Button to Approve this record. You can Contact system admin to give you guidance""" 
                            
    #                         }
    #             current_stage_approvers = [r.user_id.id for r in current_stage_approvers] + manager_approvals
    #             is_approved_stage = request_record.sudo().memo_setting_id.mapped('stage_ids').\
    #                 filtered(lambda appr: appr.is_approved_stage == True) 
    #             if is_approved_stage:
    #                 stage_id = is_approved_stage[0] 
    #                 # is_approved_stage = request_record.sudo().memo_setting_id.mapped('stage_ids').\
    #                 # filtered(lambda appr: appr.approver_id.user_id.id == request.env.user.id)
    #                 if request.env.user.id in current_stage_approvers:
    #                     # Get the stage before update for logging
    #                     current_stage_before = request_record.stage_id
                        
    #                     request_record.sudo().update_final_state_and_approver()
                        
    #                     # LOG ACTION: Approved
    #                     request_record._log_action(
    #                         action='approved',
    #                         comments='Approved via portal',
    #                         next_stage=request_record.stage_id  # Use the new stage after update
    #                     )
                        
    #                     request_record.sudo().write({
    #                         'res_users': [(4, request.env.user.id)]
    #                         })
    #                 else:
    #                     return {
    #                         "status": True,
    #                         "link": False,
    #                         "message": "You are not allowed to approve this document", 
    #                     }
    #                     # request_record.write({'state': 'Sent', 'stage_id': stage_id})
    #                 body_msg = f"""
    #                 Dear Sir / Madam <br/>\
    #                 I wish to notify you that a request with description \n <br/>\
    #                 has been approved for validation by {request.env.user.name} <br/>\
    #                 Kindly {get_url(request_record.id)}"""
    #                 request_record.mail_sending_direct(body_msg)
    #                 return {
    #                     "status": True,
    #                     "link": False,
    #                     "message": "Record updated successfully", 
    #                     }
    #             else:
    #                 return {
    #                 "status": False, 
    #                 "link": False,
    #                 "message": "No stage configured as approved stage. Contact admin", 
    #                 }
    #         else:
    #             return {
    #                     "status": False,
    #                     "link": False, 
    #                     "message": "Request must have a status", 
    #                     }
    #     else:
    #         return {
    #                 "status": False, 
    #                 "link": False,
    #                 "message": "No matching record found", 
    #                 }
            # return request.redirect(f'/my/request/view/{str(id)}')# %(requests.id))
            
    
    @http.route('/my/request/update', type='json', auth="user", website=True)
    def update_my_request(self, **post):
        _logger.info(f"updating the request ...{post.get('memo_id')}")
        
        # --- Capture Inputs from Popups ---
        selected_approver_id = int(post.get('selected_approver_id')) if post.get('selected_approver_id') else False
        selected_route_id = int(post.get('selected_route_id')) if post.get('selected_route_id') else False
        selected_district_id = int(post.get('selected_district_id')) if post.get('selected_district_id') else False

        request_id = request.env['memo.model'].sudo()
        request_record = request_id.search([('id', '=', post.get('memo_id'))], limit=1)
        status = post.get('status', '')

        if request_record:
            
            if status == "cancel":
                stage_id = request.env.ref('company_memo.memo_cancel_stage').id
                request_record._log_action(action='cancelled', comments='Cancelled via portal')
                
                body_msg = f"""Dear Sir/Madam, Request cancelled by {request.env.user.name}"""
                request_record.mail_sending_direct(body_msg)
                
                request_record.write({'state': 'Refuse', 'stage_id': stage_id})
                return {"status": True, "message": "Record cancelled successfully"}
            
            elif status == "Sent":
                stage_id = request_record.memo_setting_id.stage_ids[0].id if request_record.memo_setting_id.stage_ids else False
                
                if stage_id:
                    request_record.sudo().write({'state': 'Sent', 'stage_id': stage_id})
                    return {"status": True, "message": "Record updated successfully"}
                else:
                    return {"status": False, "link": False, "message": "Configuration Error: No stages found"}

            elif status == "Resend":
                if request.env.user.id != request_record.employee_id.user_id.id:
                    return {"status": False, "link": False, "message": "Only initiator can resend this request"}
                
                memoStage_ids = request_record.memo_setting_id.stage_ids.ids 
                if memoStage_ids:
                    if len(memoStage_ids) > 1:
                        stage_id = memoStage_ids[1]
                    else:
                        stage_id = memoStage_ids[0]
                        
                    next_stage = request.env['memo.stage'].browse(stage_id)
                    
                    request_record._log_action(
                        action='submitted', 
                        comments='Resubmitted via portal', 
                        next_stage=next_stage
                    )
                    
                    request_record.sudo().write({'state': 'Sent', 'stage_id': stage_id})
                    return {"status": True, "link": False, "message": "Record updated successfully"}
                else:
                    return {"status": False, "link": False, "message": "No stage configured or found for this request."}
            
            elif status in ["Approve"]:
                
                # --- Permission Checks ---
                current_stage_approvers = request_record.stage_id.approver_ids
                manager_approvals = []
                
                # Stage Index Check
                config_stage_ids = request_record.memo_setting_id.stage_ids.ids
                current_stage_id = request_record.stage_id.id
                
                if current_stage_id and current_stage_id in config_stage_ids:
                    # Allow managers override if in Draft/Stage 1
                    if config_stage_ids.index(current_stage_id) in [0, 1]:
                        if request_record.employee_id.parent_id:
                            manager_approvals.append(request_record.employee_id.parent_id.user_id.id)
                        if request_record.employee_id.administrative_supervisor_id:
                            manager_approvals.append(request_record.employee_id.administrative_supervisor_id.user_id.id)
                
                authorized_users = [r.user_id.id for r in current_stage_approvers] + manager_approvals
                
                if request.env.user.id not in authorized_users:
                    if not (request_record.supervisor_comment or request_record.manager_comment):
                        return {"status": False, "link": False, "message": "Please provide comments at the bottom of the form"}
                    else:
                        return {"status": False, "link": False, "message": "You are not assigned to approve this record"}

                if request_record.stage_id.is_approved_stage:
                    is_internal_user = request.env.user.has_group('base.group_user')
                    if is_internal_user:
                        return {
                            "status": False, 
                            "link": get_model_url(request_record.id, 'memo.model'),
                            "message": "Click 'VIEW AS A CORE USER' to Approve. Contact admin for guidance"
                        }

                # Get Next Stage ---
                potential_approver_ids, next_stage_id = request_record.get_next_stage_artifact(request_record.stage_id, from_website=True)

                if not next_stage_id:
                    return {"status": False, "message": "No next stage found. Process complete or Configuration Error."}

                next_stage = request.env['memo.stage'].sudo().browse(next_stage_id)
                potential_approvers = request.env['hr.employee'].sudo().browse(potential_approver_ids)

                final_approver_id = False
                
                # --- INITIALIZE PROCESSING CONTEXT ---
                proc_branch_id = request_record.processing_branch_id
                routing_mode = getattr(request_record.memo_setting_id, 'routing_mode', 'standard')

                
                # 1. User selected a specific STAFF
                if selected_approver_id:
                    final_approver_id = selected_approver_id
                
                # 2. User selected a SUB-APPROVER (Route)
                elif selected_route_id:
                    route_rec = request.env['memo.stage.route'].sudo().browse(selected_route_id)
                    final_approver_id = route_rec.approver_id.id
                    
                    update_vals = {}
                    if route_rec.branch_id: 
                        update_vals['processing_branch_id'] = route_rec.branch_id.id
                        proc_branch_id = route_rec.branch_id # Update local variable
                    if route_rec.company_id: 
                        update_vals['processing_company_id'] = route_rec.company_id.id
                    
                    if update_vals: 
                        request_record.sudo().write(update_vals)

                # 3. User selected a DISTRICT
                elif selected_district_id:
                    branch_rec = request.env['multi.branch'].sudo().browse(selected_district_id)
                    vals = {'processing_branch_id': selected_district_id}
                    
                    if branch_rec.company_id:
                        vals['processing_company_id'] = branch_rec.company_id.id
                    
                    request_record.sudo().write(vals)
                    
                    proc_branch_id = branch_rec
                    routing_mode = 'auto' 

               
                if not final_approver_id:
                    
                    if routing_mode == 'auto':
                        if proc_branch_id:
                             branch_approvers = potential_approvers.filtered(lambda e: e.branch_id.id == proc_branch_id.id)
                             count = len(branch_approvers)
                             
                             if count == 1:
                                 final_approver_id = branch_approvers[0].id
                             elif count > 1:
                                 approver_list = [{'id': app.id, 'name': f"{app.name} ({app.job_id.name or 'Staff'})"} for app in branch_approvers]
                                 return {
                                     "status": False, 
                                     "manual_select": True, 
                                     "approvers": approver_list, 
                                     "message": f"Multiple approvers found in {proc_branch_id.name}. Please select one."
                                 }
                             else: 
                                 approver_list = [{'id': app.id, 'name': f"{app.name} ({app.branch_id.name or 'HQ'})"} for app in potential_approvers]
                                 return {
                                     "status": False, 
                                     "manual_select": True, 
                                     "approvers": approver_list, 
                                     "message": f"No approver found in {proc_branch_id.name}. Please select manually."
                                 }
                        else:
                             routing_mode = 'manual'

                    if routing_mode == 'manual':
                        stage_option = next_stage.routing_option
                        
                        # Option A: Sub-Approvers
                        if stage_option == 'sub_approver':
                            if next_stage.route_ids:
                                routes_data = [{'id': r.id, 'name': r.name} for r in next_stage.route_ids]
                                return {
                                    "status": False, 
                                    "route_select": True, 
                                    "routes": routes_data, 
                                    "message": "Please select the destination."
                                }
                            else:
                                return {"status": False, "message": "Config Error: No Sub-Approvers found for this stage."}
                        
                        # Option B: Districts
                        elif stage_option == 'district':
                            if proc_branch_id:
                                stage_option = 'standard'
                            else:
                                domain = []
                                if not request_record.memo_setting_id.allow_cross_company_requests:
                                    domain = [('company_id', '=', request.env.user.company_id.id)]
                                    
                                if request_record.branch_id:
                                    domain.append(('id', '!=', request_record.branch_id.id))
                                
                                districts = request.env['multi.branch'].sudo().search(domain)
                                districts_data = [{'id': d.id, 'name': d.name} for d in districts]
                                
                                return {
                                    "status": False, 
                                    "district_select": True, 
                                    "districts": districts_data, 
                                    "message": "Please select the destination district."
                                }
                        
                        # Option C: Standard Staff List
                        if stage_option == 'standard':
                            approver_list = [{'id': app.id, 'name': app.name} for app in potential_approvers]
                            if next_stage.no_popup_if_one_approver and len(approver_list) == 1:
                                final_approver_id = approver_list[0]['id']
                            else:
                                return {
                                    "status": False, 
                                    "manual_select": True, 
                                    "approvers": approver_list, 
                                    "message": "Please select an approver"
                                }

                    if routing_mode == 'standard':
                        final_approver_id = random.choice(potential_approvers.ids) if potential_approvers else False

                # Prevent Self-Approval
                if final_approver_id and final_approver_id == request_record.employee_id.id:
                     others = potential_approvers.filtered(lambda e: e.id != request_record.employee_id.id)
                     if others: final_approver_id = others[0].id

                if not final_approver_id:
                     return {"status": False, "message": f"No approver found for stage {next_stage.name}"}

                # --- Prepare Followers ---
                current_employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
                
                employee_followers_update = []
                
                # Standard Routing: Add all stage approvers as followers
                if next_stage.approver_ids and routing_mode == 'standard':
                    for emp in next_stage.approver_ids:
                        employee_followers_update.append((4, emp.id))
                    
                if final_approver_id:
                    employee_followers_update.append((4, final_approver_id))
                
                if current_employee:
                    employee_followers_update.append((4, current_employee.id))

                invoices, documents = request_record.generate_required_artifacts(next_stage, request_record, request_record.code)
                
                vals = {
                    'stage_id': next_stage_id,
                    'approver_id': final_approver_id,
                    'set_staff': final_approver_id,
                    'direct_employee_id': final_approver_id,
                    'approver_ids': [(4, final_approver_id)],
                    'users_followers': employee_followers_update, 
                    'res_users': [(4, request.env.user.id)],
                    'invoice_ids': [(4, iv) for iv in invoices],
                    'attachment_ids': [(4, dc) for dc in documents]
                }

                request_record.generate_sub_stage_artifacts(next_stage)

                if next_stage.is_approved_stage:
                    if request_record.memo_type_key == 'material_request':
                         request_record.enable_edit_mode()
                    
                    if request_record.memo_type_key in ["Payment", 'loan', 'cash_advance', 'soe']:
                        vals['state'] = "Approve"
                    else:
                        vals['state'] = "Approve2"
                
                if request_record.memo_setting_id and request_record.memo_setting_id.stage_ids:
                    last_stage = request_record.memo_setting_id.stage_ids[-1]
                    
                    if last_stage.id == next_stage_id:
                        if vals.get('state') == 'Approve' and request_record.memo_type_key in ["Payment", 'loan', 'cash_advance', 'soe']:
                            pass 
                        else:
                            vals['state'] = 'Done'
                            final_user_emp = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.uid)], limit=1)
                            if final_user_emp:
                                vals['approver_id'] = final_user_emp.id
                                vals['approver_ids'] = [(4, final_user_emp.id)]

                request_record.sudo().write(vals)

                request_record._log_action(
                    action='approved', 
                    comments='Approved via portal', 
                    next_stage=next_stage
                )
                
                body_msg = f"""Dear Sir/Madam, Request approved by {request.env.user.name}"""
                request_record.mail_sending_direct(body_msg)
                
                return {"status": True, "message": "Record updated successfully"}

            else:
                return {"status": False, "message": "Request must have a status"}
        else:
            return {"status": False, "message": "No matching record found"}
        
    
    # @http.route('/save/data', type='json', auth="user", website=True)
    # def save_data(self, **post):
    #     memo = request.env['memo.model'].sudo()
    #     domain = [
    #         ('id', '=', int(post.get('memo_id'))),
    #     ]
    #     request_record = memo.search(domain, limit=1)
    #     DataItems = post.get('Dataitem')
    #     _logger.info(f"""retriving memo update {request_record}...
    #            POST DATAITEMS {post.get('Dataitem')}""")
    #     message = []
    #     if request_record:
    #         leave_start_date = self.compute_date_format(post.get("leave_start_date",''))
    #         leave_end_date = self.compute_date_format(post.get("leave_end_date",''))
    #         # _logger.info(f"""Let us see {int(post.get('source_location_id'))} ==== {int(post.get('dest_location_id'))}""")
    #         Data_inputFollowers = post.get('inputFollowers') # [{'id': 342233}]
    #         _logger.info(f"""SEE FOLLOWERS HERE {post.get('inputFollowers')} ---{type(Data_inputFollowers)}""")
    #         inputFollowers = [r.get('id') for r in Data_inputFollowers] if Data_inputFollowers else [] 
    #         values = {
    #             'leave_type_id': int(post.get('leave_type_id') or 0) if post.get('leave_type_id') else False,
    #             'leave_start_date': leave_start_date,
    #             'leave_end_date': leave_end_date,
    #             "leave_Reliever": int(post.get("leave_Reliever")) if post.get("leave_Reliever") else False,
    #             'description': post.get('description'),
    #             'source_location_id': int(post.get('source_location_id')) if post.get('source_location_id') else False,
    #             'dest_location_id': int(post.get('dest_location_id')) if post.get('dest_location_id') else False,
    #             'vendor_id': int(post.get('vendor_id')) if post.get('vendor_id') else False,
    #             'users_followers': [(4, fol) for fol in inputFollowers],
                
    #         }
    #         request_record.update(values)
            
    #         if not request_record.stage_id and request_record.memo_setting_id.stage_ids:
    #             values['stage_id'] = request_record.memo_setting_id.stage_ids[0].id
    #             if not request_record.state:
    #                 values['state'] = 'submit' 
                    
    #         # updated_request = self.update_request_line(DataItems, request_record)
    #         for rec in DataItems:
    #             desc = rec.get('description', '')
    #             _logger.info(f"UPDATING REQUESTS INCLUDES=====> MEMO IS {request_record} -ID {request_record.id} ---{rec}")
    #             request_vals = { 
    #                     'quantity_available': float(str(rec.get('qty')).replace(',', '').strip()) if rec.get('qty') else 0,
    #                     'description': BeautifulSoup(desc, features="lxml").get_text(),
    #                     'used_qty': rec.get('used_qty'),
    #                     # 'amount_total': float(rec.get('amount_total').replace(',', '')) if rec.get('amount_total') and type(rec.get('amount_total').replace(',', '')) in [float, int] else 0,
    #                     'used_amount': rec.get('used_amount'),
    #                     'note': rec.get('note'),
    #                     # 'request_line_id': int(rec.get('request_line_id')) if rec.get('request_line_id') else 0,
    #                     # 'code': rec.get('code') if rec.get('code') else f"{memo_id.code} - {counter}",
    #                     'to_retire': True if rec.get('line_checked') in ['on', 'On'] else False,
    #                     'distance_from': rec.get('distance_from'),
    #                     'distance_to': rec.get('distance_to'),
    #                 }
                
    #             _amt = rec.get('amount_total')
    #             if _amt not in (None, ''):
    #                 try:
    #                     request_vals['amount_total'] = float(str(_amt).replace(',', '').strip())
    #                 except Exception:
    #                     _logger.warning('Could not parse amount_total for memo %s line %s: %s', request_record.id, rec.get('request_line_id'), _amt)
    #                     request_vals['amount_total'] = 0.0
    #             _logger.info(f"UPDATED REQUESTS with VALS =====> {request_vals} ")
    #             # productid = 0 if rec.get('product_id') in ['false', False, 'none', None] or not rec.get('product_id').isdigit() else rec.get('product_id') 
                
    #             request_line = request.env['request.line'].sudo().search([('id', '=', int(rec.get('request_line_id'))), ('memo_id', '=', request_record.id)])
    #             if not request_line:
    #                 message=f"No request line with this memo ID {request_record.id} found on the system"
    #                 return {
    #                     "status": False,
    #                     "message": message,
    #                     }
    #             if rec.get('product_id') and rec.get('product_id').isdigit():
    #                 # raise ValidationError(f"{rec.get('product_id')}")
    #                 product_id = request.env['product.product'].sudo().browse([int(rec.get('product_id'))])
    #                 if product_id:
    #                     request_vals.update({
    #                         'product_id': product_id.id, 
    #                     })
    #                 else:
    #                     message = f"No product with ID {rec.get('product_id')} found on the system"
    #             request_line.update(request_vals)
            
    #         return {
    #                 "status": True,
    #                 "message": "Data successfully Updated",
    #                 }
    #     else:
    #         return {
    #                 "status": False,
    #                 "message": "No match memo record to save records",
    #                 }
    
    # @http.route('/save/data', type='http', auth="user", methods=['POST'], website=True, csrf=False)
    # def save_data(self, **post):
    #     """
    #     Handles saving data WITH file attachments via standard HTTP POST
    #     """
    #     try:
    #         memo_id = int(post.get('memo_id'))
    #         request_record = request.env['memo.model'].sudo().browse(memo_id)
            
    #         if not request_record.exists():
    #             return json.dumps({'status': False, 'message': "Record not found"})

    #         leave_start = self.compute_date_format(post.get("leave_start_date",''))
    #         leave_end = self.compute_date_format(post.get("leave_end_date",''))
            
    #         followers_raw = post.get('inputFollowers')
    #         inputFollowers = []
    #         if followers_raw:
    #             try:
    #                 followers_json = json.loads(followers_raw)
    #                 inputFollowers = [int(r.get('id')) for r in followers_json if r.get('id')]
    #             except:
    #                 pass

    #         vals = {
    #             'description': post.get('description'),
    #             'leave_start_date': leave_start,
    #             'leave_end_date': leave_end,
    #             'leave_type_id': int(post.get('leave_type_id')) if post.get('leave_type_id') else False,
    #             'leave_Reliever': int(post.get('leave_Reliever')) if post.get('leave_Reliever') else False,
    #             'source_location_id': int(post.get('source_location_id')) if post.get('source_location_id') else False,
    #             'dest_location_id': int(post.get('dest_location_id')) if post.get('dest_location_id') else False,
    #             'vendor_id': int(post.get('vendor_id')) if post.get('vendor_id') else False,
    #             'payment_reference': post.get('payment_reference'),
    #         }
            
    #         if inputFollowers:
    #             vals['users_followers'] = [(4, fol) for fol in inputFollowers]

    #         if not request_record.stage_id and request_record.memo_setting_id.stage_ids:
    #             vals['stage_id'] = request_record.memo_setting_id.stage_ids[0].id
    #             if not request_record.state:
    #                 vals['state'] = 'submit'

    #         request_record.write(vals)

    #         data_items_raw = post.get('Dataitem')
    #         if data_items_raw:
    #             DataItems = json.loads(data_items_raw)
    #             # Call your existing logic to update lines
    #             # Note: You might need to adapt 'update_request_line' to work here
    #             # Or reuse logic from save_data
    #             for rec in DataItems:
    #                 # ... (Your existing line update logic) ...
    #                 # Copy-paste the logic from your old save_data method here
    #                 desc = rec.get('description', '')
    #                 _logger.info(f"UPDATING REQUESTS INCLUDES=====> MEMO IS {request_record} -ID {request_record.id} ---{rec}")
                    
    #                 request_line_id = int(rec.get('request_line_id'))
    #                 line = request.env['request.line'].sudo().browse(request_line_id)
    #                 if line.exists():
    #                     line_vals = {
    #                         'quantity_available': float(str(rec.get('qty',0)).replace(',', '')),
    #                         'description': BeautifulSoup(desc, features="lxml").get_text(),
    #                         'used_qty': rec.get('used_qty'),
    #                         'used_amount': rec.get('used_amount'),
    #                         'note': rec.get('note'),
    #                         'to_retire': True if rec.get('line_checked') in ['on', 'On'] else False,
    #                         'distance_from': rec.get('distance_from'),
    #                         'distance_to': rec.get('distance_to'),
    #                     }
    #                     _amt = rec.get('amount_total')
    #                     if _amt not in (None, ''):
    #                         try:
    #                             line_vals['amount_total'] = float(str(_amt).replace(',', '').strip())
    #                         except Exception:
    #                             _logger.warning('Could not parse amount_total for memo %s line %s: %s', request_record.id, rec.get('request_line_id'), _amt)
    #                             line_vals['amount_total'] = 0.0
    #                     _logger.info(f"UPDATED REQUESTS with VALS =====> {line_vals} ")
                        
    #                     if rec.get('product_id') and rec.get('product_id').isdigit():
    #                         product_id = request.env['product.product'].sudo().browse([int(rec.get('product_id'))])
    #                         if product_id:
    #                             line_vals.update({
    #                                 'product_id': product_id.id, 
    #                             })
    #                         else:
    #                             message = f"No product with ID {rec.get('product_id')} found on the system"
    #                     line.write(line_vals)

    #         # 4. HANDLE FILES
    #         if 'other_docs' in request.httprequest.files:
    #             attached_files = request.httprequest.files.getlist('other_docs')
    #             for attachment in attached_files:
    #                 if attachment.filename:
    #                     file_name = attachment.filename
    #                     datas = base64.b64encode(attachment.read())
    #                     # Reuse your generate_attachment method
    #                     self.generate_attachment(request_record.code, file_name, datas, request_record.id)

    #         return json.dumps({'status': True, 'message': "Data saved successfully"})

    #     except Exception as e:
    #         _logger.exception("Error saving multipart data")
    #         return json.dumps({'status': False, 'message': str(e)})
    
    @http.route('/save/data', type='http', auth="user", methods=['POST'], website=True, csrf=False)
    def save_data(self, **post):
        """
        Handles saving data WITH file attachments via standard HTTP POST (Multipart)
        """
        try:
            memo_id_raw = post.get('memo_id')
            if not memo_id_raw:
                 return json.dumps({'status': False, 'message': "Missing Memo ID"})
                 
            memo_id = int(memo_id_raw)
            request_record = request.env['memo.model'].sudo().browse(memo_id)
            
            if not request_record.exists():
                return json.dumps({'status': False, 'message': "Record not found"})

            leave_start = self.compute_date_format(post.get("leave_start_date",''))
            leave_end = self.compute_date_format(post.get("leave_end_date",''))
            
            followers_raw = post.get('inputFollowers')
            inputFollowers = []
            if followers_raw:
                try:
                    followers_json = json.loads(followers_raw)
                    inputFollowers = [int(r.get('id')) for r in followers_json if r.get('id')]
                except Exception:
                    _logger.warning("Failed to parse followers JSON")
                    pass

            vals = {
                'description': post.get('description'),
                'leave_start_date': leave_start,
                'leave_end_date': leave_end,
                'leave_type_id': int(post.get('leave_type_id')) if post.get('leave_type_id') else False,
                'leave_Reliever': int(post.get('leave_Reliever')) if post.get('leave_Reliever') else False,
                'source_location_id': int(post.get('source_location_id')) if post.get('source_location_id') else False,
                'dest_location_id': int(post.get('dest_location_id')) if post.get('dest_location_id') else False,
                'vendor_id': int(post.get('vendor_id')) if post.get('vendor_id') else False,
                'payment_reference': post.get('payment_reference'),
            }
            
            if inputFollowers:
                vals['users_followers'] = [(6, 0, inputFollowers)]

            if not request_record.stage_id and request_record.memo_setting_id.stage_ids:
                vals['stage_id'] = request_record.memo_setting_id.stage_ids[0].id
                if not request_record.state:
                    vals['state'] = 'submit'

            request_record.write(vals)

            data_items_raw = post.get('Dataitem')
            if data_items_raw:
                try:
                    DataItems = json.loads(data_items_raw)
                    
                    for rec in DataItems:
                        if not rec.get('request_line_id'):
                            continue
                            
                        request_line_id = int(rec.get('request_line_id'))
                        line = request.env['request.line'].sudo().browse(request_line_id)
                        
                        if line.exists():
                            desc = rec.get('description', '')
                            clean_desc = BeautifulSoup(desc, features="lxml").get_text() if desc else ''
                            
                            qty_str = str(rec.get('qty', 0)).replace(',', '').strip()
                            try:
                                qty_val = float(qty_str) if qty_str else 0.0
                            except:
                                qty_val = 0.0

                            line_vals = {
                                'quantity_available': qty_val,
                                'description': clean_desc,
                                'used_qty': rec.get('used_qty'),
                                'used_amount': rec.get('used_amount'),
                                'note': rec.get('note'),
                                'to_retire': True if rec.get('line_checked') in ['on', 'On', 'true', True] else False,
                                'distance_from': rec.get('distance_from'),
                                'distance_to': rec.get('distance_to'),
                            }
                            
                            _amt = rec.get('amount_total')
                            if _amt not in (None, ''):
                                try:
                                    amt_str = str(_amt).replace(',', '').strip()
                                    line_vals['amount_total'] = float(amt_str)
                                except Exception:
                                    _logger.warning(f'Could not parse amount_total for memo {memo_id} line {request_line_id}: {_amt}')
                                    line_vals['amount_total'] = 0.0
                            
                            prod_id_raw = rec.get('product_id')
                            if prod_id_raw and str(prod_id_raw).isdigit():
                                product_id = int(prod_id_raw)
                                if request.env['product.product'].sudo().browse(product_id).exists():
                                    line_vals['product_id'] = product_id
                                else:
                                    _logger.warning(f"Product ID {product_id} not found")
                            
                            _logger.info(f"UPDATING REQUEST LINE {request_line_id} with VALS =====> {line_vals}")
                            line.write(line_vals)
                            
                except json.JSONDecodeError:
                    _logger.error("Failed to decode Dataitem JSON")
                    return json.dumps({'status': False, 'message': "Invalid data format for lines"})

            if 'other_docs' in request.httprequest.files:
                attached_files = request.httprequest.files.getlist('other_docs')
                for attachment in attached_files:
                    if attachment.filename:
                        file_name = attachment.filename
                        datas = base64.b64encode(attachment.read())
                        self.generate_attachment(request_record.code, file_name, datas, request_record.id)

            return json.dumps({'status': True, 'message': "Data saved successfully"})

        except Exception as e:
            _logger.exception("Error saving multipart data")
            return json.dumps({'status': False, 'message': str(e)})
   
   
    def compute_date_format(self, date_format):
        date = False
        
        if not date_format or date_format == 'undefined' or date_format == 'null':
            return False

        try:
            if '-' in date_format:
                # Handle YYYY-MM-DD
                if ':' in date_format: # Handle YYYY-MM-DD HH:MM:SS
                    datefmt = datetime.strptime(date_format, "%Y-%m-%d %H:%M:%S")
                    date = datetime.strptime(datefmt.strftime('%m/%d/%Y'), '%m/%d/%Y')
                else:
                    date = datetime.strptime(date_format, "%Y-%m-%d")
            else:
                # Handle MM/DD/YYYY
                date = datetime.strptime(date_format, "%m/%d/%Y")
        except ValueError:
            return False
            
        return date

    @http.route('/update/data', type='json', auth="user", website=True)
    def update_my_request_status(self, **post):
        request_id = request.env['memo.model'].sudo()
        domain = [
            ('id', '=', int(post.get('memo_id'))),
        ]
        request_record = request_id.search(domain, limit=1)
        _logger.info(f"retriving memo update {request_record}...")
        if request_record:
            # TODO some kind of repeatation was done here. COnsider rewriting
            supervisor_message = request_record.supervisor_comment or ""
            manager_message = request_record.manager_comment or ""
            message, body = "", ""
            status = post.get('status', '')
            _logger.info(f"retriving memo update {post.get('supervisor_comment')}...")
            if post.get('supervisor_comment', ''):
                body = plaintext2html(post.get('supervisor_comment'))
                value = {
                    'is_supervisor_commented': True,
                    'state': 'Refuse' if status == 'Refuse' else request_record.state,
                    'stage_id': request.env.ref("company_memo.memo_refuse_stage").id if status == 'Refuse' else request_record.stage_id.id,
                    }
                
                if request_record.employee_id.administrative_supervisor_id:
                    message = supervisor_message +"\n"+ "By: " + request.env.user.name + ':'+ body
                    value.update({
                        'supervisor_comment': message
                        })
                else:
                    message = manager_message +"\n"+ "By: " + request.env.user.name + ':'+ body
                    value.update({
                        'manager_comment': message
                        })
                request_record.write(value)
                body_msg = f"""
                    Dear Sir / Madam, <br/>
                    I wish to notify you that a memo with the reference #{request_record.code} \n <br/>\
                    has been commented by the supervisor / manager. <br/>\
                    Kindly {get_url(request_record.id)}"""
                request_record.mail_sending_direct(body_msg) 
                request_record.message_post(body=body)
                return {
                        "status": True,
                        "message": "Comment successfully Updated",
                        }
            elif post.get('manager_comment'):
                body = plaintext2html(post.get('manager_comment'))
                message = manager_message +"\n"+ "By: " + request.env.user.name +':'+ body
                request_record.write({
                    'manager_comment': message,
                    'state': 'Refuse' if status == 'Refuse' else request_record.state,
                    'stage_id': request.env.ref("company_memo.memo_refuse_stage").id if status == 'Refuse' else request_record.stage_id.id,
                    })
                body_msg = f"""
                    Dear Sir / Madam, <br/>
                    I wish to notify you that a request with description \n <br/>\
                    has been commented by the Manager. <br/>\
                    Kindly {get_url(request_record.id)}"""
                request_record.message_post(body=body)
                return {
                        "status": True,
                        "message": "Comment successfully Updated",
                        }
            else:
                _logger.info(f"xxxxxx not updated")
                return {
                    "status": False, 
                    "message": "Please Provide a write up in the comment section", 
                }
                
    
        else:
            return {
                "status": False, 
                "message": "No matching memo record found. Contact Admin", 
            }
