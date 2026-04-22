# -*- coding: utf-8 -*-
import base64
import json
import logging
import random
from multiprocessing.spawn import prepare
import urllib.parse
from odoo import http, fields
from odoo.exceptions import ValidationError
from odoo.tools import consteq, plaintext2html
from odoo.http import request
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
import odoo
import odoo.addons.web.controllers.home as main
from odoo.addons.web.controllers.utils import ensure_db, _get_login_redirect_url, is_user_internal
from odoo.tools.translate import _
_logger = logging.getLogger(__name__)


class PortalDashboard(http.Controller):
    @http.route(["/my/portal/dashboard/<int:user_id>"], type='http', auth='user', website=True, website_published=True)
    def dashboardPortal(self, user_id): 
        try:
            user = request.env['res.users'].sudo().browse([user_id])
            # user_id
            current_time = datetime.now() 
            memo = request.env['memo.model'].sudo()
            memo_ids = memo.search([
                ('employee_id', '=', user.employee_id.id),
            ], order="id desc")
            vals = {  
                "user": user,
                "image": user.employee_id.image_512 or user.image_1920,
                "memo_ids": memo_ids,
                "closed_request": len(self.closed_files(memo_ids)),
                "open_request": len(self.closed_files(memo_ids)),
                "approved_request": len(self.approved_files(memo_ids)),
                "leave_remaining":  user.employee_id.allocation_remaining_display,
                "template_name":  'portal_dashboard_template_id',
                "performance_y_data_chart": json.dumps(
                    {"performance_y_data_chart": ["KRA","Functional Competence","Leadership Competence"]}
                    ),
                "performance_x_data_chart": self.get_pms_performance(user),
            }
            # _logger.info(f"{vals.get('performance_y_data_chart')} and the x is {vals.performance_x_data_chart}")
            return request.render("portal_request.portal_dashboard_template_id", vals)
        except Exception as e:
            return request.not_found() 

    def closed_files(self, memo):
        closed_memo_ids = memo.filtered(lambda se: se.state in ['Done'])
        return closed_memo_ids
    
    def open_files(self, memo):
        open_memo_ids = memo.filtered(lambda se: se.state not in ['Refuse', 'Done'])
        return open_memo_ids
    
    def approved_files(self, memo):
        approved_memo_ids = memo.filtered(lambda se: se.state not in ['Refuse', 'submit', 'Sent'])
        return approved_memo_ids
    
    def get_pms_performance(self, user):
        try:
            appraisee = request.env['pms.appraisee'].sudo()
            employee_appraisee = appraisee.search([(
                'employee_id', '=', user.employee_id.id,
            )])
            performance_x_data_chart = [0,0,0]
            if employee_appraisee:
                emp_app = None
                today_year = fields.Date.today().year
                _logger.info(f"apprasia  {employee_appraisee}")
                for app in employee_appraisee:
                    _logger.info(f"APPRAISAL YEAR {app.pms_year_id.date_from.strftime('%Y')} == TODAY YEAR {today_year}")
                    if app.pms_year_id.date_from.strftime("%Y") == str(today_year):
                        emp_app = app
                        _logger.info(f"DID NOT SEE ANY {emp_app} == YEAR {app.pms_year_id.date_from.strftime('%Y')}")
                        break
                if emp_app:
                    performance_x_data_chart = [emp_app.final_kra_score, emp_app.final_fc_score, emp_app.final_lc_score]
                
            return json.dumps({'performance_x_data_chart': performance_x_data_chart})
            
        except ModuleNotFoundError as e:
            return json.dumps({'performance_x_data_chart': performance_x_data_chart})