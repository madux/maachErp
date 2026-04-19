from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
# from odoo.addons.eha_website.controllers.controllers import EhaWebsite
import logging
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class JobPortal(WebsiteSale):
    
    @http.route()
    def complete_recruitment(self, **post):
        """
        Returns:
            json: JSON reponse
        """
        _logger.info(f'Creating Applicants detailss ...{int(post.get("job_id"))}')
        job_id = post.get("job_id")
        email_from = post.get("email_from")
        job_id = job_id and int(job_id)
        job = request.env['hr.job'].sudo().search([('id', '=', job_id)])
        if not job.allow_to_appy_in_period(email_from):
            return request.render("eha_website_hr_recruitment.job_already_applied")
        else:
            return super().complete_recruitment(**post)