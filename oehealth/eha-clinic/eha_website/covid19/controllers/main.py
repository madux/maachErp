# -*- coding: utf-8 -*-
from datetime import datetime
import json
import logging
from odoo import http, fields, _
from werkzeug.exceptions import Forbidden, NotFound
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
# from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.eha_website.utils import get_payment_providers_details
import base64
import pprint
import requests
import os
import pyotp
import time
from odoo.addons.phone_validation.tools import phone_validation

_logger = logging.getLogger(__name__)


class EhaCovid19Controller(http.Controller):

    def clear_cart(self):
        ''' clear cart'''
        try:
            order = request.website.sale_get_order()
            if order:
                for line in order.website_order_line:
                    line.unlink()
        except Exception as ex:
            _logger.exception(ex)

    @http.route(['/covid/params', '/covid/params/<string:flag>'], type='json', website=True, auth="public", csrf=False)
    def get_covid_data(self, code=None, flag=None):
        code_applied = False
        promotion_id = False
        
        if flag and (flag == 'home'):
            product = http.request.env['product.product'].sudo().search([('default_code', '=', 'HOME')], limit=1)
            if product:
                return {"product": {'id': product.id, 'name': product.name, 'code': product.default_code,
                                    'price': product.list_price}}

        # pick the price list for Direct Care Membership - Standard as all the subscription have same discount price 
        members_prices = http.request.env['product.pricelist'].sudo().search(
            [('name', '=', 'Direct Care Membership - Standard')])
        members_covid_products_prices = members_prices.mapped('item_ids').filtered(
            lambda self: self.product_tmpl_id.categ_id.name == 'COVID-19 Services')

        products = http.request.env['product.product'].sudo().search([('categ_id.name', '=', 'COVID-19 Services')])
        product_list = []
        promotion = False
        promotion_id = False
        if products:
            # if code:
            #     promotion = request.env['sale.coupon.program'].sudo()
            #     promotion_id = promotion.search([('promo_code', '=', code)], limit=1)
            for p in products:
                discounted_price = 0
                if promotion_id:
                    discounted_price = promotion_id.discount_fixed_amount
                    code_applied = True
                product_list += [{'id': p.id,
                                  'name': p.name,
                                  'code': p.default_code,
                                  'price': (p.list_price - discounted_price)}]
        for pl in product_list:
            for mp in members_covid_products_prices:
                if pl.get('name') == (mp.name).split("]")[-1].strip():
                    pl['members_price'] = mp.fixed_price
                    break
        
        if promotion_id:
            return {"data": product_list, "promo": code_applied, "promo_id": promotion_id and promotion_id.id}
        _logger.info(f"Product listsss {product_list}")
        return {"data": product_list}

    @http.route(['/services/buy-covid19-test',
                 '/services/buy-covid19-test/<partner_code>',
                 # '/shop/product/covid-19-pcr-eha-clinics-covid19-pcr-test-for-international-travel-7662',
                 # '/shop/product/covid-19-pcr2-eha-clinics-covid19-pcr-test-5886',
                 ],
                type='http',
                auth="public",
                website=True,
                csrf=False)
    def buy_covid19_landing(self, partner_code=None, **kw):
        self.clear_cart()
        partner = False
        if partner_code:
            partner = http.request.env['res.partner'].sudo().search(
                [('default_code', 'ilike', partner_code)], limit=1)
            # if partner code is not valid, redirect to our buy covid-19 page
            if not partner:
                return request.redirect("/services/buy-covid19-test")
        partner_id = partner.id if partner else ''
        values = {"thirdparty_partner_id": partner_id}
        return http.request.render('eha_website.buytest-overview', values)

    @http.route('/covid/check/membership', type='json', website=True, methods=['POST'], auth="public", csrf=False)
    def check_membership(self, phone, name):
        name_list = name.split(' ')
        Partner = http.request.env['res.partner'].sudo()
        formated_phone = phone_validation.phone_format(phone, country_code=None, country_phone_code=None)

        Subscription = http.request.env['sale.subscription'].sudo()
        SubscriptionStage = http.request.env['sale.subscription.stage'].sudo()
        in_progress = SubscriptionStage.search([('name', '=', 'In Progress')])
        to_upsale = SubscriptionStage.search([('name', '=', 'To Upsell')])
        active_subscriptions = Subscription.search(
            ['|', ('stage_id', '=', in_progress.id), ('stage_id', '=', to_upsale.id)])

        partner = Partner.search([('phone', '=', formated_phone)])
        if not partner:
            # partner not found
            return {"is_success": False, "msg": "Partner not found"}

        if partner.firstname not in name_list and partner.lastname not in name_list:
            # partner found
            return {"is_success": False, "msg": "Partner not found"}

        # first level check
        subscription = active_subscriptions.search([('partner_id', '=', partner.id)])
        if not subscription:
            # second level check
            for subs in active_subscriptions:
                beneficary = subs.mapped('beneficiary_ids').filtered(lambda self: self.phone == formated_phone)
                if beneficary:
                    subscription = subs
                    break

            if not subscription:
                # subscription not found
                return {"is_success": False, "msg": "Can't find a subscription"}

        # valid subscription found
        return {"is_success": True}

    @http.route('/services/buy-covid19-patientinfo', type='http', auth="public", website=True, csrf=False)
    def buy_covid19Patientinfo(self):
        countries = http.request.env['res.country'].sudo().search([])
        nigeria = http.request.env['res.country'].sudo().search([('code', '=', 'NG')])
        ng_states = nigeria.state_ids
        airliners_config = http.request.env['ir.config_parameter'].sudo().get_param('airliners')
        airliners = airliners_config.split(',') if airliners_config else []
        airlines = [airline.strip() for airline in airliners]

        context = {"ng_states": ng_states, "countries": countries, "airlines": airlines}
        return http.request.render('eha_website.buytest-step1', context)

    @http.route(['/services/buy-covid19-patientsummary'], type='http', auth="public", website=True, csrf=False)
    def capture_persons_summary(self, **kw):
        countries = http.request.env['res.country'].sudo().search([])
        nigeria = http.request.env['res.country'].sudo().search([('code', '=', 'NG')])
        ng_states = nigeria.state_ids
        airliners_config = http.request.env['ir.config_parameter'].sudo().get_param('airliners')
        airliners = airliners_config.split(',') if airliners_config else []
        airlines = [airline.strip() for airline in airliners]

        context = {"ng_states": ng_states, "countries": countries, "airlines": airlines}
        return http.request.render('eha_website.buytest-step1-summary', context)

    @http.route(['/services/buy-covid19-appointmenttype'], type='http', methods=["POST", "GET"], auth="public",
                website=True, csrf=False)
    def preferred_appointment_type(self, **kw):
        home_service_product = http.request.env['product.template'].sudo().search([('default_code', '=', 'HOME')],
                                                                                  limit=1)
        context = {'home_price': f"{home_service_product.list_price:,}" if home_service_product else 0.00}
        return http.request.render('eha_website.buytest-step2', context)

    @http.route(['/services/buy-covid19-checkout'], type='http', auth="public", website=True, csrf=False)
    def buy_covid19_checkout(self, **kw):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_url = '{}/services/buy-covid19-confirmation'.format(base_url)

        payment_provider_info = get_payment_providers_details(request)
        payment_provider = payment_provider_info.get("provider")
        public_key = payment_provider_info.get("public_key")

        if not payment_provider:
            return request.redirect("/services/buy-covid19-checkout?error=1")

        return http.request.render('eha_website.buytest-step3', {
            'redirect_url': redirect_url,
            'public_key': public_key,
            'provider': payment_provider
        })

    @http.route(['/services/buy-covid19-confirmation'], type='http', auth="public", website=True, csrf=False)
    def buy_covid19_confirmation(self, **kw):
        # Do not allow request without valid transaction id to access the confirmation page
        txn_id = request.params.get('txnid', 0)
        if txn_id:
            cifs = http.request.env['oeha.covid19.cif'].sudo().search([('payment_transaction_id', '=', txn_id)],
                                                                      limit=1)
            if not cifs:
                return http.request.render('eha_website.buytest-confirmation', {'error': True})
        return http.request.render('eha_website.buytest-confirmation')

    @http.route(['/send/otp', '/send/otp/<couponcode>'], type='json', website=True, auth="public", csrf=False)
    def otp_send_sms(self, couponcode):
        param_obj = http.request.env['ir.config_parameter']
        otp_key = param_obj.sudo().get_param('eha_website.otp_secret_key1', '')  # HELP: base32ehaotp5432
        _logger.info("SECRET CODE IS " + otp_key)
        totp = pyotp.TOTP(otp_key, interval=300)  # 300 seconds is equivalent to 5 minutes of expiry
        otp_code = totp.now()  # e.g => '492039'
        partner_rec = self.get_partner_by_coupon(couponcode)  # true or false
        valid_coupon = partner_rec if partner_rec else False
        partner_phone = partner_rec.phone or partner_rec.mobile if partner_rec else ''
        formated_phone = partner_phone.replace(' ', '')
        phone = [formated_phone] if formated_phone else []
        if phone and valid_coupon:
            http.request.env['bulk.sms']._send_sms(phone, otp_code)
            return formated_phone if valid_coupon else False

    @http.route(['/verify/otp', '/verify/otp/<otp>'], type='json', website=True, auth="public", csrf=False)
    def otp_verification(self, otp):
        _logger.info("OTP RESULT= {} ".format(otp))
        param_obj = http.request.env['ir.config_parameter']
        otp_key = param_obj.sudo().get_param('eha_website.otp_secret_key1',
                                             '')  # changed the id because of conflict with non update record id
        totp = pyotp.TOTP(otp_key, interval=300)
        if totp.verify(otp):
            _logger.info("VALID OTP")
            return True
        else:
            _logger.info("INVALID OTP")
            return False

    def get_partner_by_coupon(self, code):
        partner_ref = http.request.env['res.partner'].sudo().search([('coupon_code', '=', code)], limit=1)
        return partner_ref
