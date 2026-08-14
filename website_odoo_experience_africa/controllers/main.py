# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class OdooExperienceAfricaLanding(http.Controller):
    """Controller exposing the Odoo Experience Africa 2026 landing page."""

    @http.route(
        ['/odoo-experience-africa'],
        type='http',
        auth='public',
        website=True,
        sitemap=True,
    )
    def odoo_experience_africa_landing(self, **kwargs):
        return request.render(
            'website_odoo_experience_africa.landing_page',
            {}
        )
