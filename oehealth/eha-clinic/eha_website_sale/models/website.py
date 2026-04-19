import logging

from odoo import api, fields, models, tools, SUPERUSER_ID

from odoo.http import request
from odoo.addons.website.models import ir_http

_logger = logging.getLogger(__name__)

class Website(models.Model):
    _inherit = 'website'

    def sale_product_domain(self):
        return [("sale_ok", "=", True),("display_product_on_website", "=", True)] + self.get_current_website().website_domain()
    
    def get_current_pricelist(self):
        """
        :returns: The current pricelist record
        """
        # The list of available pricelists for this user.
        # If the user is signed in, and has a pricelist set different than the public user pricelist
        # then this pricelist will always be considered as available
        available_pricelists = self.get_pricelist_available()
        pl = None
        partner = self.env.user.partner_id
        if request and request.session.get('website_sale_current_pl'):
            # `website_sale_current_pl` is set only if the user specifically chose it:
            #  - Either, he chose it from the pricelist selection
            #  - Either, he entered a coupon code
            pl = self.env['product.pricelist'].browse(request.session['website_sale_current_pl'])
            if pl not in available_pricelists:
                pl = None
                request.session.pop('website_sale_current_pl')
        non_member_pricelist_param = request.env['ir.config_parameter'].sudo().get_param('eha_website_sale.non_member_pricelist')
        member_pricelist_param = request.env['ir.config_parameter'].sudo().get_param('eha_website_sale.member_pricelist')
        non_member_pricelist = non_member_pricelist_param and request.env['product.pricelist'].browse(int(non_member_pricelist_param)) or None
        member_pricelist = member_pricelist_param and request.env['product.pricelist'].browse(int(member_pricelist_param)) or None
        pl = non_member_pricelist
        if not request.env.user._is_public():
            patient_id = request.env.user.patient_id
            if patient_id and patient_id.plan_id:
                pl = member_pricelist
        if not pl:
            # If the user has a saved cart, it take the pricelist of this last unconfirmed cart
            pl = partner.last_website_so_id.pricelist_id
            if not pl:
                # The pricelist of the user set on its partner form.
                # If the user is not signed in, it's the public user pricelist
                pl = partner.property_product_pricelist
            if available_pricelists and pl not in available_pricelists:
                # If there is at least one pricelist in the available pricelists
                # and the chosen pricelist is not within them
                # it then choose the first available pricelist.
                # This can only happen when the pricelist is the public user pricelist and this pricelist is not in the available pricelist for this localization
                # If the user is signed in, and has a special pricelist (different than the public user pricelist),
                # then this special pricelist is amongs these available pricelists, and therefore it won't fall in this case.
                pl = available_pricelists[0]
        if not pl:
            _logger.error('Fail to find pricelist for partner "%s" (id %s)', partner.name, partner.id)
        return pl
