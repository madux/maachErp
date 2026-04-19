from odoo import http
from odoo.http import request
from odoo.addons.eha_website.controllers.controllers import EhaWebsite
from odoo.addons.eha_telehealth.controllers.main import get_telehealth_data
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.controllers.main import Website


class Website(Website):
    
    @http.route('/not_to_used', type='http', auth="public", website=True)
    def index(self, **kw):
        # homepage = request.website.homepage_id
        payment_acquirers, booking_service_id, location_id, state_ids, insurance_ids = get_telehealth_data()
        context = {
            "payment_acquirers": payment_acquirers,
            "booking_service": booking_service_id,
            "location": location_id,
            "state_ids": state_ids,
            "insurance_ids": insurance_ids,
        }
        # CONSIDER 23 - 37 Uncommenting if telehealth is still needed
        # homepage = homepage.with_context(context)
        # if homepage and (homepage.sudo().is_visible or request.env.user.has_group('base.group_user')) and homepage.url != '/':
        #     return request.env['ir.http'].with_context(context).reroute(homepage.url)

        # website_page = request.env['ir.http'].with_context(context)._serve_page(context)
        # if website_page:
        #     return website_page
        # else:
        #     top_menu = request.website.menu_id
        #     first_menu = top_menu and top_menu.child_id and top_menu.child_id.filtered(lambda menu: menu.is_visible)
        #     if first_menu and first_menu[0].url not in ('/', '', '#') and (not (first_menu[0].url.startswith(('/?', '/#', ' ')))):
        #         return request.with_context(context).redirect(first_menu[0].url)

        # raise request.not_found()


class EHAWebsite(EhaWebsite):
    
    @http.route()
    def service_telehealth(self, **kw):
        self.clear_cart()
        payment_acquirers, booking_service_id, location_id, state_ids, insurance_ids = get_telehealth_data()
        context = {
            "payment_acquirers": payment_acquirers,
            "booking_service": booking_service_id,
            "location": location_id,
            "state_ids": state_ids,
            "insurance_ids": insurance_ids,

        }
        return http.request.render('eha_website.service_telehealth', qcontext=context)
    
    # @http.route()
    # def get_care(self, *args, **kwargs):
    #     payment_acquirers, booking_service_id, location_id,state_ids, insurance_ids = get_telehealth_data()
    #     context = {
    #         "payment_acquirers": payment_acquirers,
    #         "booking_service": booking_service_id,
    #         "location": location_id
    #     }
    #     return request.render("eha_telehealth.get_care", context)
    
    
# class WebsiteSale(WebsiteSale):
    
    # def _prepare_product_values(self, product, category, search, **kwargs):
    #     add_qty = int(kwargs.get('add_qty', 1))

    #     product_context = dict(request.env.context, quantity=add_qty,
    #                            active_id=product.id,
    #                            partner=request.env.user.partner_id)
    #     ProductCategory = request.env['product.public.category']

    #     if category:
    #         category = ProductCategory.browse(int(category)).exists()

    #     attrib_list = request.httprequest.args.getlist('attrib')
    #     attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
    #     attrib_set = {v[1] for v in attrib_values}

    #     keep = QueryURL('/shop', category=category and category.id, search=search, attrib=attrib_list)

    #     categs = ProductCategory.search([('parent_id', '=', False)])

    #     pricelist = request.website.get_current_pricelist()

    #     if not product_context.get('pricelist'):
    #         product_context['pricelist'] = pricelist.id
    #         product = product.with_context(product_context)
    #     payment_acquirers, booking_service_id, location_id, state_ids, insurance_ids = get_telehealth_data()

    #     # Needed to trigger the recently viewed product rpc
    #     view_track = request.website.viewref("website_sale.product").track

    #     return {
    #         'search': search,
    #         'category': category,
    #         'pricelist': pricelist,
    #         'attrib_values': attrib_values,
    #         'attrib_set': attrib_set,
    #         'keep': keep,
    #         'categories': categs,
    #         'main_object': product,
    #         'product': product,
    #         'add_qty': add_qty,
    #         'view_track': view_track,
    #         "payment_acquirers": payment_acquirers,
    #         "booking_service": booking_service_id,
    #         "location": location_id,
    #         "insurance_ids": insurance_ids,
    #     }
