import logging
from odoo import http

_logger = logging.getLogger(__name__)

class EhaGazelleController(http.Controller):

    @http.route(['/shop/gazelle'], type="http", website=True, auth="public")
    def gazelle_product_page(self, **kw):
        return http.request.render('eha_website.gazelle_product_page')
