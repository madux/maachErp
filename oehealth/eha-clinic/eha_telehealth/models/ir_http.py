import os
from odoo import models
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import _guess_mimetype


class Http(models.AbstractModel):
    _inherit = 'ir.http'
    
    # @classmethod
    # def _serve_page(cls, context=None):
    #     req_page = request.httprequest.path
    #     page_domain = [('url', '=', req_page)] + request.website.website_domain()

    #     published_domain = page_domain
    #     # specific page first
    #     page = request.env['website.page'].sudo().search(published_domain, order='website_id asc', limit=1)
    #     qcontext = {
    #         'deletable': True,
    #         'main_object': page,
    #     }
    #     if context is not None:
    #         qcontext.update(context)
    #     if page and (request.website.is_publisher() or page.is_visible):
    #         _, ext = os.path.splitext(req_page)
    #         return request.render(page.get_view_identifier(), qcontext, mimetype=_guess_mimetype(ext))
    #     return False