# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

import json
import logging
from odoo import http
from odoo import fields
from odoo.http import request
from odoo.tools import file_path
from odoo.modules.module import get_resource_path

class OdooExperienceAfricaLanding(http.Controller):
    """Controller exposing the Odoo Experience Africa 2026 landing page."""

    @http.route('/landing-page', type='http', auth='user')
    def show_html_page(self, **kw):
        # Get actual file path inside the module
        file_path = get_resource_path(
            'website_africa',  # your module name
            'static/src/html_files',          # folder path inside module
            'landing_page.html'          # file name
        )
        # website_africa/static/src/html_files/landing_page.html
        if not file_path:
            return "HTML file not found."

        # Read HTML file content
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
        user = request.env.user

        data = {
            'user_id':   user.id,
            'user_name': user.name,
            'user_email': user.email or '',
        }
        # Return raw HTML content
        return request.make_response(
            html,
            headers=[('Content-Type', 'text/html'),('defaultData', json.dumps(data))],
            
        )
    # @http.route(
    #     ['/landing-page'],
    #     type='http',
    #     auth='public',
    #     website=True,
    #     sitemap=True,
    # )
    # def website_landing_page(self, **kwargs):
    #     return request.render(
    #         'website_africa.landing_page',
    #         {}
    #     )

