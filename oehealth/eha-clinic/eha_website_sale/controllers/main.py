import json
import logging
import threading
from odoo import http, fields, tools, _
from werkzeug.exceptions import Forbidden, NotFound
import werkzeug.wrappers
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug, unslug
from odoo.addons.web.controllers.main import ensure_db
from odoo.addons.website_sale.controllers.main import WebsiteSale, TableCompute, QueryURL
# from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from datetime import datetime, date 
from datetime import timedelta
import requests
from requests.auth import HTTPBasicAuth
import json

_logger = logging.getLogger(__name__)


class WebsiteSale(WebsiteSale):

    def clear_cart(self):
        ''' clear cart if user'''
        try:
            order = request.website.sale_get_order()
            if order:
                for line in order.website_order_line:
                    line.unlink()
        except Exception as ex:
            _logger.exception(ex)

    # MANDO

    def sitemap_shop(env, rule, qs):
        if not qs or qs.lower() in '/shop':
            yield {'loc': '/shop'}

        Category = env['product.public.category']
        dom = sitemap_qs2dom(qs, '/shop/category', Category._rec_name)
        dom += env['website'].get_current_website().website_domain()
        for cat in Category.search(dom):
            loc = '/shop/category/%s' % slug(cat)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    @http.route([
        '''/shop''',
        '''/shop/page/<int:page>''',
        '''/shop/category/<model("product.public.category"):category>''',
        '''/shop/category/<model("product.public.category"):category>/page/<int:page>'''
    ], type='http', auth="public", website=True, sitemap=sitemap_shop)
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        add_qty = int(post.get('add_qty', 1))

        Category = request.env['product.public.category']
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = Category

        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg or 20

        ppr = request.env['website'].get_current_website().shop_ppr or 4

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")]
                         for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        domain = self._get_search_domain(search, category, attrib_values)

        keep = QueryURL('/shop', category=category and int(category),
                        search=search, attrib=attrib_list, order=post.get('order'))

        pricelist_context, pricelist = self._get_pricelist_context()

        request.context = dict(
            request.context, pricelist=pricelist.id, partner=request.env.user.partner_id)

        url = "/shop"
        if search:
            post["search"] = search
        if attrib_list:
            post['attrib'] = attrib_list

        Product = request.env['product.template'].with_context(bin_size=True)

        search_product = Product.search(
            domain, order=self._get_search_order(post))
        website_domain = request.website.website_domain()
        categs_domain = [('parent_id', '=', False)] + website_domain
        if search:
            search_categories = Category.search(
                [('product_tmpl_ids', 'in', search_product.ids)] + website_domain).parents_and_self
            categs_domain.append(('id', 'in', search_categories.ids))
        else:
            search_categories = Category
        categs = Category.search(categs_domain)

        if category:
            url = "/shop/category/%s" % slug(category)

        product_count = len(search_product)
        pager = request.website.pager(
            url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        offset = pager['offset']
        products = search_product[offset: offset + ppg]

        ProductAttribute = request.env['product.attribute']
        if products:
            # get all products without limit
            attributes = ProductAttribute.search(
                [('product_tmpl_ids', 'in', search_product.ids)])
        else:
            attributes = ProductAttribute.browse(attributes_ids)

        layout_mode = request.session.get('website_sale_shop_layout_mode')
        if not layout_mode:
            if request.website.viewref('website_sale.products_list_view').active:
                layout_mode = 'list'
            else:
                layout_mode = 'grid'

        EcommerceBranches = request.env['eha.branch'].search(
            [('is_online_store', '=', True)])
        values = {
            'ecommerce_branches': EcommerceBranches,
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'add_qty': add_qty,
            'products': products,
            'search_count': product_count,  # common for all searchbox
            'bins': TableCompute().process(products, ppg, ppr),
            'ppg': ppg,
            'ppr': ppr,
            'categories': categs,
            'attributes': attributes,
            'keep': keep,
            'search_categories_ids': search_categories.ids,
            'layout_mode': layout_mode,
        }
        if category:
            values['main_object'] = category
        # raise ValidationError(','.join([rec.pricelist_id for rec in values.get('ecommerce_branches'))
        return request.render("website_sale.products", values)

    @http.route('/shop/topics/healthtests', type='http', auth="public", website=True)
    def health_tests(self, **kw):

        hsWomen_category = http.request.env['product.public.category'].sudo().search([
            ('code', '=', 'HSF')])
        hsMen_category = http.request.env['product.public.category'].sudo().search([
            ('code', '=', 'HSM')])
        hsDiagnosis_category = http.request.env['product.public.category'].sudo().search([
            ('code', '=', 'HSG')])
        hsPackages_category = http.request.env['product.public.category'].sudo().search([
            ('code', '=', 'HSHP')])

        hsWomen_products = http.request.env['product.product'].sudo().search(
            [('is_featured', '=', True), ('public_categ_ids', 'in', [hsWomen_category.id])])  # health Screening products
        hsMen_products = http.request.env['product.product'].sudo().search(
            [('is_featured', '=', True), ('public_categ_ids', 'in', [hsMen_category.id])])  # Blood Typing products
        hsDiagnosis_products = http.request.env['product.product'].sudo().search(
            [('is_featured', '=', True), ('public_categ_ids', 'in', [hsDiagnosis_category.id])])  # Pregnancy Test products
        hsPackages_product = http.request.env['product.product'].sudo().search(
            [('is_featured', '=', True), ('public_categ_ids', 'in', [hsPackages_category.id])])  # Pre-marital Package

        context = {
            "hsWomen_products": hsWomen_products,
            "hsMen_products": hsMen_products,
            "hsDiagnosis_products": hsDiagnosis_products,
            "hsPackages_product": hsPackages_product
        }
        return http.request.render('eha_website_sale.topic_healthtests', context)

    def _get_mandatory_billing_fields(self):
        return ["name", "email", "street", "city", "country_id", "zip"]

    def _get_mandatory_shipping_fields(self):
        return ["name", "street", "city", "country_id", "zip"]

    @http.route('/shop/plans/compare', type='http', auth="public", website=True)
    def compare_plans(self, **kw):
        return http.request.render('eha_website_sale.compare_plans')

    @http.route('/shop/terms', type='http', auth="public", website=True)
    def terms(self, **kw):
        # self.clear_cart()
        return http.request.render('eha_website_sale.terms')

    def _get_plan_features(self, myplan, product=False, include_others=False):
        '''get distinct features for each plan from the products that belong to the plan , 
         this is only neccessary for conforming to sabeen's membership overview page design'''

        features = False
        feature_set = []

        if not product:
            products = request.env['product.template'].sudo().search(
                [('is_published', '=', True), ('recurring_invoice', '=', True)])
            filtered_products = products.filtered(
                lambda p: p.plan_id.name == myplan)
            features = filtered_products.mapped(
                'product_feature_ids') if filtered_products else False

        # if product is provided, the features that would be returned would be that of the product
        if product:
            features = product.mapped('product_feature_ids')
            include_others = True

        def feature_filter_domain(
            f): return f.category != 'others' if include_others == False else lambda f: f
        categories = sorted(set(features.filtered(
            feature_filter_domain).mapped('category')) if features else [])
        for category in categories:
            mydict = dict()
            mydict['category'] = category
            mydict['features'] = features.filtered(
                lambda f: f.category == category).mapped('name')
            feature_set.append(mydict)
        return feature_set

    def _is_membership(self, product):
        return product and product.categ_id.name.lower() == 'direct care membership'

    @http.route('/shop/membership', auth='public', website=True)
    def membership(self, **kw):
        ''' Author: Ohia George. subscription plans '''

        # self.clear_cart()
        # #set session membership to false
        request.session['is_sub_membership'] = False

        ensure_db()
        plans_with_products = []

        for plan in request.env['sale.subscription.plan'].sudo().search([]):
            d = dict()
            d['name'] = plan.name
            d['descriptions'] = plan.description.split(
                ';') if plan.description else []

            # get subcription products
            products = request.env['product.template'].sudo().search(
                [('is_published', '=', True), ('plan_id', '=', plan.id)], order="sequence")
            d['products'] = products
            plans_with_products.append(d)

        standard_features = self._get_plan_features('Standard')
        premium_features = self._get_plan_features('Premium')
        international_features = self._get_plan_features('International')

        plans_features = dict(standard_features=standard_features,
                              premium_features=premium_features, international_features=international_features)

        return request.render('eha_website_sale.membership2', {
            'plans': plans_with_products,
            'plans_features': plans_features
        })

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        if 'family' in product.name.lower():
            if product.plan_id.name == 'Standard':
                return request.redirect('/family-standard-membership')
            if product.plan_id.name == 'Premium':
                return request.redirect('/family-premium-membership')
            if product.plan_id.name == 'International':
                return request.redirect('/family-premium-international-membership')
        if not product.can_access_from_current_website():
            raise NotFound()

        # ''' clear the cart if its a membership product'''
        if self._is_membership(product):
            self.clear_cart()

        # save the source of the business
        request.session['src'] = None  # unset to clear carry-over sessions
        request.session.src = request.params.get('src', 'EHA')
        # set session membership to false
        request.session['is_sub_membership'] = None
        request.session['covid19_patient_list'] = None

        return request.render("website_sale.product", self._prepare_product_values(product, category, search, **kwargs))

    def _prepare_product_values(self, product, category, search, **kwargs):
        add_qty = int(kwargs.get('add_qty', 1))

        product_context = dict(request.env.context, quantity=add_qty,
                               active_id=product.id,
                               partner=request.env.user.partner_id)
        ProductCategory = request.env['product.public.category']

        if category:
            category = ProductCategory.browse(int(category)).exists()

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")]
                         for v in attrib_list if v]
        attrib_set = {v[1] for v in attrib_values}

        keep = QueryURL('/shop', category=category and category.id,
                        search=search, attrib=attrib_list)

        categs = ProductCategory.search([('parent_id', '=', False)])

        pricelist = request.website.get_current_pricelist()

        if not product_context.get('pricelist'):
            product_context['pricelist'] = pricelist.id
            product = product.with_context(product_context)

        # Needed to trigger the recently viewed product rpc
        view_track = request.website.viewref("website_sale.product").track

        # added by Ohia George
        # please negelect the first parameter 'standard', it will be neglected by the method
        # and only features of the product would be returned
        features = self._get_plan_features('Standard', product=product)
        product_features = [
            feat.name for feat in product.mapped('product_feature_ids')]
        EcommerceBranches = request.env['eha.branch'].search(
            [('is_online_store', '=', True)])
        return {
            'ecommerce_branches': EcommerceBranches,
            'search': search,
            'category': category,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'keep': keep,
            'categories': categs,
            'main_object': product,
            'product': product,
            'product_features': product_features,
            'add_qty': add_qty,
            'view_track': view_track,
            'configurable_text': request.env['ir.config_parameter'].sudo().get_param("eha_website_sale.website_product_tagline", "")
        }

    @http.route(['/shop/family_product_price/<id>'], type='http', auth="public", website=True, methods=['GET'], csrf=False)
    def family_product_price(self, id=None, **kw):
        # add_qty = int(post.get('add_qty', 1))
        code_pricelist = request.env['product.pricelist'].sudo().search(
            [('code', '=', 'FAMEM001')], limit=1)
        product = request.env['product.product'].sudo().browse([4280])
        product_context = dict(request.env.context, quantity=1,
                               active_id=4280,
                               partner=request.env.user.partner_id,
                               pricelist=code_pricelist.id)
        product2 = product.with_context(product_context)
        _logger.info('PRICE FAM %s' % product.list_price)

        return json.dumps({'price': product2.list_price})

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, access_token=None, revive='', **post):
        """
        Main cart management + abandoned cart revival
        access_token: Abandoned cart SO access token
        revive: Revival method when abandoned cart. Can be 'merge' or 'squash'
        """
        order = request.website.sale_get_order()
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()
        values = {}
        if access_token:
            abandoned_order = request.env['sale.order'].sudo().search(
                [('access_token', '=', access_token)], limit=1)
            if not abandoned_order:  # wrong token (or SO has been deleted)
                return request.render('website.404')
            if abandoned_order.state != 'draft':  # abandoned cart already finished
                values.update({'abandoned_proceed': True})
            # restore old cart or merge with unexistant
            elif revive == 'squash' or (revive == 'merge' and not request.session['sale_order_id']):
                request.session['sale_order_id'] = abandoned_order.id
                return request.redirect('/shop/cart')
            elif revive == 'merge':
                abandoned_order.order_line.write(
                    {'order_id': request.session['sale_order_id']})
                abandoned_order.action_cancel()
            # abandoned cart found, user have to choose what to do
            elif abandoned_order.id != request.session['sale_order_id']:
                values.update({'access_token': abandoned_order.access_token})

        if order:
            from_currency = order.company_id.currency_id
            to_currency = order.pricelist_id.currency_id
            def compute_currency(price): return from_currency._convert(
                price, to_currency, request.env.user.company_id, fields.Date.today())
        else:
            def compute_currency(price): return price

        values.update({
            'website_sale_order': order,
            'compute_currency': compute_currency,
            'date': fields.Date.today(),
            'suggested_products': [],
        })
        if order:
            _order = order
            if not request.env.context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()

        if post.get('type') == 'popover':
            # force no-cache so IE11 doesn't cache this XHR
            return request.render("website_sale.cart_popover", values, headers={'Cache-Control': 'no-cache'})

        return request.render("website_sale.cart", values)

    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        ''' Ohia George
            process family membership
        '''
        if kw.get('is_sub_membership') == 'True':
            """ Ohia George
            Clear the cart before adding a new product"""
            self.clear_cart()
            # sale_order= request.website.sale_get_order(force_create = True, code='FAMEM001')
            sale_order = request.website.sale_get_order(force_create=True)
            if sale_order.state != 'draft':
                request.session['sale_order_id'] = None
                # sale_order= request.website.sale_get_order(force_create = True, code='FAMEM001')
                sale_order = request.website.sale_get_order(force_create=True)
            # save is_sub_membership flag in session, will be used to determine
            # the display of the beneficiaries form
            request.session['is_sub_membership'] = True
            # _logger.info("FAMILY MEMEBERSHIP %s %s %s " % ( kw.get('youth-qty'), kw.get('adult-qty'), kw.get('senior-qty') ))
            youth_qty, adult_qty, senior_qty = int(kw.get(
                'youth-qty', 0)), int(kw.get('adult-qty', 0)), int(kw.get('senior-qty', 0))
            product = request.env['product.product'].sudo().browse([
                int(product_id)])
            children = product.mapped('child_product_ids')
            if children:
                for product in children:
                    if 'youth' in product.name.lower():
                        sale_order._cart_update(
                            product_id=product.id, add_qty=youth_qty, set_qty=youth_qty)
                    elif 'adult' in product.name.lower():
                        sale_order._cart_update(
                            product_id=product.id, add_qty=adult_qty, set_qty=adult_qty)
                    else:  # senior
                        sale_order._cart_update(
                            product_id=product.id, add_qty=senior_qty, set_qty=senior_qty)
            return request.redirect("/shop/checkout?express=1")

        """This route is called when adding a product to cart (no options)."""
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)

        product_custom_attribute_values = None
        if kw.get('product_custom_attribute_values'):
            product_custom_attribute_values = json.loads(
                kw.get('product_custom_attribute_values'))

        no_variant_attribute_values = None
        if kw.get('no_variant_attribute_values'):
            no_variant_attribute_values = json.loads(
                kw.get('no_variant_attribute_values'))

        sale_order._cart_update(
            product_id=int(product_id),
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_values=no_variant_attribute_values
        )
        return request.redirect("/shop/cart?src=%s" % request.session.get('src', 'EHA'))

    def _get_default_country(self):
        ''' added by Ohia George'''
        # 163 is the default country id for Nigeria in odoo
        # TODO: Refactor to make this a bit more dynamic
        return request.env['res.country'].sudo().browse([163])

    def beneficairy_form_validate(self, data):
        error = dict()
        error_message = []
        for k, v in data.items():
            if "email" in k and not tools.single_email_re.match(data.get('email')):
                error["beneficiary_email"] = 'error'
                error_message.append(
                    _('Invalid Beneficiary Email! Please enter a valid email address.'))

        return error, error_message

    @http.route(['/shop/address'], type='http', methods=['GET', 'POST'], auth="public", website=True)
    def address(self, **kw):
        Partner = request.env['res.partner'].with_context(
            show_address=1).sudo()
        order = request.website.sale_get_order()
        is_sub_membership = request.session.get('is_sub_membership', False)

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        mode = (False, False)
        can_edit_vat = False
        def_country_id = order.partner_id.country_id
        values, errors = {}, {}

        partner_id = int(kw.get('partner_id', -1))

        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            mode = ('new', 'billing')
            can_edit_vat = True
            def_country_id = self._get_default_country()
        # IF ORDER LINKED TO A PARTNER
        else:
            if partner_id > 0:
                if partner_id == order.partner_id.id:
                    mode = ('edit', 'billing')
                    can_edit_vat = order.partner_id.can_edit_vat()
                else:
                    shippings = Partner.search(
                        [('id', 'child_of', order.partner_id.commercial_partner_id.ids)])
                    if partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                    else:
                        return Forbidden()
                if mode:
                    values = Partner.browse(partner_id)
                    values['email'] = values['email'] if values['email'] else kw.get(
                        'email')
            elif partner_id == -1:
                mode = ('new', 'shipping')
            else:  # no mode - refresh without post?
                return request.redirect('/shop/checkout')

        # Added by Ohia George
        # get order subsrciption product
        sub_product = False
        if order and order.order_line:
            sub_product = order.order_line[0].product_id

        # IF POSTED
        if 'submitted' in kw:
            pre_values = self.values_preprocess(order, mode, kw)
            errors, error_msg = self.checkout_form_validate(
                mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(
                order, mode, pre_values, errors, error_msg)

            state_id = kw.get('beneficiary_state_adult1')
            if state_id:
                state_obj = http.request.env['res.country.state'].sudo().search([
                    ('id', '=', state_id)])
                request.session['state_id'] = state_obj.id

            # added by Ohia George
            # save beneficairies and partner details in session
            # this would be used later to create the beneficiaries when purchase is successful
            request.session.beneficiaries = kw
            _logger.info('BENE %s' % kw)
            _logger.info('BENE ERRORS %s' % errors)
            if errors:
                errors['error_message'] = error_msg
                values = kw
            else:
                # _checkout_form_save returns None if partner with same number exists

                partner_id = self._checkout_form_save(mode, post, kw)
                if partner_id != None:
                    if mode[1] == 'billing':
                        order.partner_id = partner_id
                        order.onchange_partner_id()
                    #    if not kw.get('use_same'):
                    #       kw['callback'] = kw.get('callback') or \
                    #            (not order.only_services and (mode[0] == 'edit' and '/shop/checkout' or '/shop/address'))
                    elif mode[1] == 'shipping':
                        order.partner_shipping_id = partner_id

                    order.message_partner_ids = [
                        (4, partner_id), (3, request.website.partner_id.id)]
                else:
                    errors['error_message'] = [
                        'A partner with phone no [%s] already exists. Please use another phone no. or visit any of our Clinics to complete registration.' % kw.get('phone')]
                if not errors:
                    if is_sub_membership:
                        return request.redirect('/shop/beneficiaries')
                    return request.redirect(kw.get('callback') or '/shop/confirm_order')

        country = 'country_id' in values and values['country_id'] != '' and request.env['res.country'].browse(
            int(values['country_id']))
        # country = country and country.exists() or
        # 163 is the default country id for Nigeria in odoo
        # TODO: Refactor to make this a bit more dynamic
        country = country or self._get_default_country()
        branches = request.env['eha.branch'].sudo().search([], order="name")
        airliners_config = request.env['ir.config_parameter'].sudo(
        ).get_param('airliners')
        airliners = airliners_config.split(',') if airliners_config else []

        render_values = {
            'dcountry_id': def_country_id,
            'website_sale_order': order,
            'sub_product': sub_product,
            'partner_id': partner_id,
            'mode': mode,
            'checkout': values,
            'can_edit_vat': can_edit_vat,
            'country': country,
            'countries': country.get_website_sale_countries(mode=mode[1]),
            "states": country.get_website_sale_states(mode=mode[1]),
            "branches": branches,
            'error': errors,
            'callback': kw.get('callback'),
            'only_services': order and order.only_services,
            'webpartner': request.website.user_id.sudo().partner_id.id,
            'opartner': order.partner_id.id,
            'is_sub_membership': is_sub_membership,
            'airliners': airliners,
            'zip_code_link': request.env['ir.config_parameter'].sudo().get_param('eha_website_sale.ecommerce_zip_code_link', ''),
        }
        _logger.info("CHECKOUT %s" % render_values.get('checkout'))
        return request.render("eha_website_sale.address_ext", render_values)

    @http.route(['/shop/beneficiaries'], type='http', methods=['GET', 'POST'], auth="public", website=True)
    def beneficiaries(self, **kw):
        order = request.website.sale_get_order()
        values = kw
        mode = (False, False)
        errors = {}

        country = 'country_id' in values and values['country_id'] != '' and request.env['res.country'].browse(
            int(values['country_id']))
        country = country or self._get_default_country()

        # get family child products
        products = []
        fields_dict = {
            'name': '',
            'gender': '',
            'dob': '',
            'email': '',
            'phone': '',
            'street': '',
            'city': '',
            'country_id': 163,
            'state': '',
            'myself': False,
            'completed': False,  # add to track when the form is completed on the UI
        }
        sn = 1
        for line in order.order_line:
            if 'senior' in line.product_id.name.lower():
                for i in range(int(line.product_uom_qty)):
                    senior = {
                        'sn': sn,
                        'qty': int(line.product_uom_qty),
                        'product_name': line.product_id.name,
                        'product_short_name': 'Senior',
                    }
                    data = dict(fields_dict, **senior)
                    products.append(data)
                    sn += 1
            elif 'adult' in line.product_id.name.lower():
                for i in range(int(line.product_uom_qty)):
                    adult = {
                        'sn': sn,
                        'product_name': line.product_id.name,
                        'qty': int(line.product_uom_qty),
                        'product_short_name': 'Adult'
                    }
                    data = dict(fields_dict, **adult)
                    products.append(data)
                    sn += 1
            else:
                for i in range(int(line.product_uom_qty)):
                    youth = {
                        'sn': sn,
                        'product_name': line.product_id.name,
                        'qty': int(line.product_uom_qty),
                        'product_short_name': 'Youth'
                    }
                    data = dict(fields_dict, **youth)
                    products.append(data)
                    sn += 1
        _logger.info('PRODUCTSM %s' % products)
        render_values = {
            'website_sale_order': order,
            'checkout': values,
            'country': country,
            # 'countries': country.get_website_sale_countries(mode=mode[1]),
            "states": country.get_website_sale_states(mode=mode[1]),
            'error': errors,
            'callback': kw.get('callback'),
            'products': products,
            'products_json': json.dumps(products)
        }

        _logger.info("PLANS %s " % products)
        return request.render("eha_website_sale.beneficiaries", render_values)

    def _checkout_form_save(self, mode, checkout, all_values):

        partner_id = None
        Partner = request.env['res.partner']
        if mode[0] == 'new':
            ''' added by Ohia George
            if phone number exists and name matches, handle gracefully by '''
            try:
                #datetime.strptime(cif.get('dob'), '%d/%m/%Y')
                partner_exists = Partner.sudo().search(
                    [('phone', '=', all_values.get('phone'))], limit=1)
                if partner_exists and partner_exists.name == all_values.get('name'):
                    partner_id = partner_exists.id
                # elif partner_exists and partner_exists.name != all_values.get('name'):
                #     partner_id = None
                else:
                    partner_id = Partner.sudo().create(checkout).id
            except ValidationError as ex:
                _logger.exception(ex)
                _logger.info(
                    "Nothing to worry about, it is handled gracefully")

            ''' end added by Ohia George '''

        elif mode[0] == 'edit':
            partner_id = int(all_values.get('partner_id', 0))
            if partner_id:
                # double check
                order = request.website.sale_get_order()
                shippings = Partner.sudo().search(
                    [("id", "child_of", order.partner_id.commercial_partner_id.ids)])
                if partner_id not in shippings.mapped('id') and partner_id != order.partner_id.id:
                    return Forbidden()
                Partner.browse(partner_id).sudo().write(checkout)
        return partner_id

    def _get_mandatory_beneficiary_fields(self, post_data):
        ''' dynamically return compulsory beneficiary fields
            Author: Ohia George
         '''
        def dictfilt(data): return [k for k, v in data.items(
        ) if 'beneficiary' in k and 'email' not in k]
        return dictfilt(post_data)

    def checkout_form_validate(self, mode, all_form_values, data):
        # mode: tuple ('new|edit', 'billing|shipping')
        # all_form_values: all values before preprocess
        # data: values after preprocess
        error = dict()
        error_message = []

        # Required fields from form
        required_fields = [f for f in (all_form_values.get(
            'field_required') or '').split(',') if f]

        # added by Ohia George
        # required beneficiaries fields
        required_fields += self._get_mandatory_beneficiary_fields(
            all_form_values)

        # Required fields from mandatory field function
        required_fields += mode[1] == 'shipping' and self._get_mandatory_shipping_fields(
        ) or self._get_mandatory_billing_fields()
        # Check if state required
        country = request.env['res.country']
        if data.get('country_id'):
            country = country.browse(int(data.get('country_id')))
            if 'state_code' in country.get_address_fields() and country.state_ids:
                required_fields += ['state_id']

        # error message for empty required fields
        for field_name in required_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(
                _('Invalid Email! Please enter a valid email address.'))

        # vat validation
        Partner = request.env['res.partner']
        if data.get("vat") and hasattr(Partner, "check_vat"):
            if data.get("country_id"):
                data["vat"] = Partner.fix_eu_vat_number(
                    data.get("country_id"), data.get("vat"))
            partner_dummy = Partner.new({
                'vat': data['vat'],
                'country_id': (int(data['country_id'])
                               if data.get('country_id') else False),
            })
            try:
                partner_dummy.check_vat()
            except ValidationError:
                error["vat"] = 'error'

        if [err for err in error.values() if err == 'missing']:
            error_message.append(
                _('The fields highlighted in red are required!'))

        return error, error_message

    @http.route(['/shop/checkout'], type='http', auth="public", website=True)
    def checkout(self, **post):
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            return request.redirect('/shop/address') 

        for f in self._get_mandatory_billing_fields():
            if not order.partner_id[f]:
                return request.redirect('/shop/address?partner_id=%d' % order.partner_id.id)

        values = self.checkout_values(**post)

        if post.get('express'):
            # commented by Ohia George
            # to ensure the beneficiaries form is always displayed when checking out
            # return request.redirect('/shop/confirm_order')
            # return request.redirect('/shop/address')
            return request.redirect('/shop/address?partner_id=%d' % order.partner_id.id)

        values.update({'website_sale_order': order})

        # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'
        return request.render("website_sale.checkout", values)

    def format_return_name(self, name):
        fname = ''
        lname = ''
        if name and len(name) > 0:
            name_arr = name.split() or []
            arrlen = len(name_arr)
            if arrlen >= 1:
                fname = name_arr[0]
            if arrlen > 1:
                lname = ', '.join(name_arr[1:])
        return fname, lname

    @http.route(['/shop/payment'], type='http', auth="public", website=True, sitemap=False)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :
         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling

        """
        order = request.website.sale_get_order()
        ##############################################
        """We need to reconsider this option as it might affect other features i.e i am 
        currently picking the state_id because it is stored under beneficiaries object,
        I am not certain about membership features:

        Rules: Ensure that user current company has a default warehouse, 
        Ensure that warehouses has the partner state set under it
        """
        product_order_line = order.mapped('order_line')
        if product_order_line:
            wrh_found = False
            # using this method because i really need to default to admin user warehouse if no
            # warehouse is found at all
            admin_user = request.env['res.users'].sudo().search(
                [('id', '=', 2)], limit=1)
            admin_user_company = admin_user and admin_user.company_id
            user_company = request.env.user.company_id or admin_user_company  # Safe
            default_warehouse = request.env['stock.warehouse'].sudo().search([
                ('company_id', '=', user_company.id)
            ], limit=1)
            state_id = post.get("state_id", None)
            if request.session.get('beneficiaries'):
                state_id = request.session.get('beneficiaries').get('state_id')
            else:
                state_id = order.partner_invoice_id.state_id.id or request.env.user.partner_id.state_id.id
            if state_id:
                whs = request.env['stock.warehouse'].sudo().search([])
                for wr in whs:
                    warehouse_id = wr.mapped('state_ids').filtered(
                        lambda s: s.id == int(state_id))
                    if warehouse_id:
                        _logger.info(F"Hahahahahahahahahaha: ==> {wr.name}")
                        wrh_found = wr.id
                        break
                _logger.info(f"WAREHOUSSE FOUND: ==> {wrh_found}")
                order.write(
                    {"warehouse_id": wrh_found or default_warehouse.id})
            else:
                order.write(
                    {"warehouse_id": wrh_found or default_warehouse.id})
                _logger.info("LOGGING HERE TO CHECK IF STATE NOT AVAILABLE")
        else:
            _logger.info("NO ORDERLINE ON ECOMMERCE OH!")
        ##############################################
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        render_values = self._get_shop_payment_values(order, **post)
        render_values['only_services'] = order and order.only_services or False

        if render_values['errors']:
            render_values.pop('acquirers', '')
            render_values.pop('tokens', '')

        carrier_id = post.get('carrier_id')
        if carrier_id:
            carrier_id = int(carrier_id)
        if order:
            order._check_carrier_quotation(force_carrier_id=carrier_id)
            if carrier_id:
                return request.redirect("/shop/payment")

        return request.render("website_sale.payment", render_values)

    @http.route(['/shop/confirmation'], type='http', auth="public", website=True)
    def payment_confirmation(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)

            '''Added by ohia George. If the order state == 'sale', this means the sale order is confirmed.
                At this point, subscription is already created, we get the reference of the subscription,
                create patient records and add them as beneficiaries to the subscription.
            '''
            # This is to replace the default warehouse in the sale order with the correct warehaouse depending on the state choosen by the user.
            # DISCARDING THIS IMPLEMENTATION FOR TWO REASONS: It attempted write on sale order if multi records found at a time

            # product_order_line = order.mapped('order_line')
            # if product_order_line:
            #     state_id = request.session.get('state_id')
            #     if state_id:
            #         for warehouse in request.env['stock.warehouse'].sudo().search([]):
            #             warehouse_id = warehouse.mapped('state_ids').filtered(
            #                 lambda state: state.id == state_id)
            #             if warehouse_id:
            #                 warehouse = {"warehouse_id": warehouse.id}
            #                 order.write(warehouse)
            #                 break

            if order.state == 'sale':
                try:
                    Patient = request.env['oeh.medical.patient'].sudo()
                    subscription = request.env['sale.order.line'].sudo().search(
                        [('order_id', '=', order.id), ('subscription_id', '!=', False)], limit=1).subscription_id

                    # family membership
                    beneficiary_list = request.session.get(
                        'beneficiary_list', [])
                    if beneficiary_list and beneficiary_list.get('data', []):
                        _logger.info('BENE %s ' %
                                     beneficiary_list.get('data', []))
                        subscription = request.env['sale.order.line'].sudo().search(
                            [('order_id', '=', order.id), ('subscription_id', '!=', False)], limit=1).subscription_id
                        for beneficiary in beneficiary_list.get('data'):
                            st = beneficiary.get('state_id')
                            ct = beneficiary.get('country_id')
                            state_id = int(st) if st is not None else False
                            # 163 is default country id for Nigeria in odoo
                            country_id = int(ct) if ct is not None else 163
                            name_tuple = self.format_return_name(
                                beneficiary.get('name'))
                            """
                                bene_vals = {
                                    'partner_id': pt.partner_id.id, 
                                    'is_staff': is_staff, 
                                    'employee_no': unique_id, 
                                    'company_billing': company_budget, 
                                    'used_budget': 0.0, 
                                    'plan_id': planId,
                                    'role_id': role_id, 
                                    'subscription_id': self.subscription_id.id,
                                    'gender': gender,
                                    'dob': dob,
                                }
                            """

                            vals = {
                                'firstname': name_tuple[0],
                                'lastname': name_tuple[1],
                                'sex': beneficiary.get('gender', '').title(),
                                'dob': datetime.strptime(beneficiary.get('dob'), '%d/%m/%Y'),
                                'email': beneficiary.get('email'),
                                'phone': beneficiary.get('phone'),
                                'street': beneficiary.get('street'),
                                'city': beneficiary.get('city'),
                                'state_id': state_id,
                                'country_id': country_id,
                            }
                            # check if patient with same phone and dob exits
                            patient = Patient.search(
                                [('phone', '=', vals.get('phone')), ('dob', '=', vals.get('dob'))])
                            if patient.exists():
                                patient_id = patient
                            else:
                                patient_id = Patient.create(vals)
                            subscription.sudo().write(
                                {
                                    'beneficiary_ids': [
                                        (0, 0, {
                                            'partner_id': patient_id.partner_id.id,
                                            # 'company_billing': request.env.user.company_id.id or request.session.comapny_id,
                                            'used_budget': 0.0,
                                            'plan_id': subscription.plan_id.id,
                                            'subscription_id': subscription.id,
                                            'gender': beneficiary.get('gender', '').title(),
                                            'dob': patient_id.dob,
                                        })
                                    ]
                                }
                            )
                        # send subscription  email
                        _logger.info('SUB NAME %s ID %s ' % (
                            subscription.display_name, subscription.id))
                        subscription.send_email()

                    '''non family Membership subscription'''
                    beneficiary = request.session.get('beneficiaries', [])
                    # this seperates this from family product
                    if beneficiary and not beneficiary.get('data'):
                        Subscription = request.env['sale.order.line'].sudo().search(
                            [('order_id', '=', order.id), ('subscription_id', '!=', False)], limit=1).subscription_id
                        subscription_product = Subscription.mapped('recurring_invoice_line_ids')[
                            0] if Subscription and Subscription.recurring_invoice_line_ids else False
                        if subscription_product:
                            # non family membership
                            if 'family' not in subscription_product.name.lower():
                                _logger.info('NAME sess %s' % beneficiary.get(
                                    'beneficiary_name_adult1'))
                                name_tuple = self.format_return_name(
                                    beneficiary.get('beneficiary_name_adult1'))
                                _logger.info('NAME TUPLE %s' %
                                             str(name_tuple[0]))
                                st = beneficiary.get(
                                    'beneficiary_state_adult1')
                                ct = beneficiary.get('country_id')
                                state_id = int(st) if st is not None else 0
                                # 163 is default country id for Nigeria in odoo
                                country_id = int(ct) if ct is not None else 163
                                vals = {
                                    'firstname': name_tuple[0],
                                    'lastname': name_tuple[1],
                                    'sex': beneficiary.get('beneficiary_gender_adult1', '').title(),
                                    'dob': datetime.strptime(beneficiary.get('beneficiary_dob_adult1'), '%d/%m/%Y'),
                                    'email': beneficiary.get('beneficiary_email_adult1'),
                                    'phone': beneficiary.get('beneficiary_phone_adult1'),
                                    'street': beneficiary.get('beneficiary_street_adult1'),
                                    'city': beneficiary.get('beneficiary_city_adult1'),
                                    'state_id': state_id,
                                    'country_id': country_id,
                                }
                                # check if patient with same phone and dob exits
                                patient = Patient.search([('phone', '=', vals.get(
                                    'phone')), ('dob', '=', vals.get('dob'))], order='id desc', limit=1)
                                if patient.exists():
                                    patient.write(vals)
                                    patient_id = patient
                                else:
                                    patient_id = Patient.create(vals)
                                subscription.sudo().write(
                                    {
                                        'beneficiary_ids': [
                                            (0, 0, {
                                                'partner_id': patient_id.partner_id.id,
                                                # 'company_billing': request.env.user.company_id.id or request.session.comapny_id,
                                                'used_budget': 0.0,
                                                'plan_id': subscription.plan_id.id,
                                                'subscription_id': subscription.id,
                                                'gender': beneficiary.get('beneficiary_gender_adult1', '').title(),
                                                'dob': patient_id.dob,
                                            })
                                        ]
                                    }
                                )
                        # send subscription  email
                        Subscription.send_email()
                except Exception as ex:
                    _logger.exception(
                        "An error occured while creating COVID-19/Membership records: %s" % ex)

            # remove beneficiaries from session
            request.session.beneficiaries = {}
            request.session.covid19_patient_list = {}
            request.session.beneficiary_list = {}
            request.session.src = None
            # clear the cart
            self.clear_cart()

            return request.render("website_sale.confirmation", {'order': order})
        else:
            return request.redirect('/shop')

    @http.route('/shop/patient/exists', type='json', website=True, auth="public", csrf=False)
    def patient_exists(self, phone, **post):
        ''' Check if patient with same phone number exists 
            This is called via ajax when filling beneficiaries form
        '''
        patient = request.env['oeh.medical.patient'].sudo().search(
            [('phone', '=', phone)], limit=1)
        if patient:
            return True
        return False

    @http.route(['/shop/patient/add_session'], type='json', website=True, auth="public", methods=["POST"],  csrf=False)
    # @http.route('/shop/patient/add_session', type='json', website=True, methods=['POST'], auth="public", csrf=False)
    def patient_add_to_session(self, **post):
        ''' 
            This is called via ajax when filling beneficiaries form
        '''
        if post.get('is_membership') == True:
            request.session.beneficiary_list = post
            return json.dumps(request.session.get('beneficiary_list', []))
        else:
            request.session.covid19_patient_list = post
            return json.dumps(request.session.get('covid19_patient_list', []))

    @http.route(['/shop/patient/get_session'], type='json', website=True, auth="public", methods=["POST"], csrf=False)
    def patient_get_session(self, **post):
        ''' 
            This is called via ajax when filling beneficiaries form
        '''
        return json.dumps(request.session.get('covid19_patient_list', []))

    @http.route(['/shop/patient/clear_session'], type='json', website=True, auth="public", methods=["POST"], csrf=False)
    def patient_clear_session(self, **post):
        ''' 
            This is called via ajax when filling beneficiaries form
        '''
        request.session.covid19_patient_list = {}
        return json.dumps({'data': True})

    # This controller is implemented for prescription booking - Get Care

    @http.route('/shop/prescription_booking', type='http', auth="public", website=True)
    def shop_prescription_booking(self, **kw):
        values = {
            'is_public': request.env.user.id == request.env.ref('base.public_user').id,
        }
        return request.render('eha_website_sale.website_prescription_booking', values)

    @http.route(['/find_my_prescription'], type='json', auth="public", website=True, methods=["post"])
    def verify_prescription(self, prescription_id):
        prescription_id = request.env['oeh.medical.prescription'].sudo().search(
            [('name', '=', prescription_id)], limit=1)

        if prescription_id:
            lines = []
            for line in prescription_id.prescription_line:
                lines.append({
                    'prescription_id': prescription_id.id,
                    "id": line.id,
                    "patient_id": line.patient.id,
                    "patient": line.patient.name,
                    "product_id": line.name.id,
                    "name": line.name.name,
                    "description_sale": line.name.description_sale,
                    "purchased_qty": line.purchased_qty,
                    "product_url": line.name.website_url,
                    "product_tmpl_id": line.name.product_tmpl_id.id,
                    "indication": line.indication,
                    "dose": line.dose,
                    "dose_unit": line.dose_unit.name,
                    "dose_form": line.dose_form.name,
                    "common_dosage": line.common_dosage.name,
                    "qty": line.qty,
                    "is_refillable": line.is_refillable,
                    "refill_qty": line.refill_qty,
                    "duration": line.duration,
                    "duration_period": line.duration_period,
                    "info": line.info,
                    "price": line.name.list_price,
                    "currency_id": request.website.currency_id.id,
                    "expired": line.next_refill_date > date.today() if line.next_refill_date else True
                })
            return {
                'prescription_id': prescription_id.name,
                'id': prescription_id.id,
                'date': prescription_id.date,
                'dob': prescription_id.patient.dob,
                'prescribed_by': prescription_id.prescriber.name,
                'prescription_lines': lines
            }

    @http.route(['/verify_dob'], type='json', auth="public", website=True, methods=["post"])
    def verify_dob(self, prescription_id, dob):
        prescription_id = request.env['oeh.medical.prescription'].sudo().search(
            [('id', '=', prescription_id)], limit=1)
        if prescription_id and dob:
            if str(prescription_id.patient.dob) == dob:
                return True
        return False

    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update_json(self, product_id, prescription={}, line_id=None, add_qty=None, set_qty=None, display=True):
        """This route is called when changing quantity from the cart or adding
        a product from the wishlist."""
        order = request.website.sale_get_order(force_create=1)
        # @author Hiren : This code is for updating prescription line
        if (order and prescription) or (order and order.prescription_id):
            prescription_id = prescription and prescription.get(
                'prescription_id') or order.prescription_id.id
            prescription_id = request.env['oeh.medical.prescription'].sudo().search(
                [('id', '=', prescription_id)], limit=1)
            order.write({'prescription_id': prescription_id})
            # :/ some peeps have named product as name so conside k.name as k.product_id
            line_vals = {}
            line = prescription_id.prescription_line.filtered(
                lambda k: k.name.id == product_id)
            if (prescription and prescription.get('is_refillable')) or (prescription_id and line.is_refillable):
                next_refill_date = False
                if line.next_refill_date:
                    days = 0
                    if line.refill_duration_unit == 'Days':
                        days = line.refill_duration
                    elif line.refill_duration_unit == 'Weeks':
                        days = line.refill_duration * 7
                    elif line.refill_duration_unit == 'Months':
                        days = line.refill_duration * 30

                    if add_qty:
                        next_refill_date = line.next_refill_date + \
                            timedelta(days=days)
                    elif add_qty == 0 or add_qty == None or not add_qty:
                        next_refill_date = line.next_refill_date - \
                            timedelta(days=days)
                line_vals.update(
                    {'refill_qty': add_qty, 'next_refill_date': next_refill_date})
            else:
                line_vals.update({'purchased_qty': add_qty})
            line.write(line_vals)

        if order.state != 'draft':
            request.website.sale_reset()
            return {}

        value = order._cart_update(product_id=int(
            product_id), add_qty=add_qty, set_qty=set_qty)
        if not order.cart_quantity:
            request.website.sale_reset()
            return value

        order = request.website.sale_get_order()
        value['cart_quantity'] = order.cart_quantity

        if not display:
            return value

        value['website_sale.cart_lines'] = request.env['ir.ui.view'].render_template("website_sale.cart_lines", {
            'website_sale_order': order,
            'date': fields.Date.today(),
            'suggested_products': order._cart_accessories()
        })
        value['website_sale.short_cart_summary'] = request.env['ir.ui.view'].render_template("website_sale.short_cart_summary", {
            'website_sale_order': order,
        })
        return value
