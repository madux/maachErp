# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
from werkzeug.exceptions import Forbidden, NotFound

from odoo import fields, http, tools, _
from odoo.http import request
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.addons.http_routing.models.ir_http import slug
# from odoo.addons.payment.controllers.portal import PaymentProcessing
# from odoo.addons.website.controllers.main import QueryURL
# from odoo.exceptions import ValidationError
# from odoo.addons.website.controllers.main import Website
# from odoo.addons.website_form.controllers.main import WebsiteForm
# from odoo.osv import expression
from datetime import datetime 
import random
from dateutil import parser


class FamilyMembership(http.Controller):

    @http.route(['/find_member'], type='json', auth="public", website=True, methods=["post"])
    def find_member(self, id, dob):
        if id:
            patient = request.env['oeh.medical.patient'].sudo().search(
                [('identification_code', '=', id), ('dob', '=', dob)]
            )
            if patient:
                vals = {}
                partner = patient and patient.partner_id
                vals.update({
                    'id': partner.id,
                    'patient_id': patient.id,
                    'family_class': partner.family_class,
                    'lastname': patient.lastname or '',
                    'firstname': patient.firstname or '',
                    'middlename': patient.lastname2 or '',
                    'gender': patient.sex or '',
                    'lga': patient.lga or '',
                    'dob': patient.dob or '',
                    'email': partner.email or '',
                    'phone': partner.phone or '',
                    'street': partner.street or '',
                    'city': partner.city or '',
                    'state': partner.state_id.id or '',
                })
                return vals
        return False

    @http.route(['/membership-step1', '/membership-step1/<type>',
                 '/membership-step2', '/membership-step2/<type>',
                 '/membership-step3', '/membership-step3/<type>'],
                type='http', auth="public",
                website=True, methods=["POST", "GET"])
    def first_page(self, type='', **post):
        country_id = request.env['res.country'].sudo().search([('code', '=', 'NG')], limit=1)
        vals = {
            'pricing': [],
            'products': False,
            'discount': 0,
            'total': 0,
            'type': 'premium',
        }
        vals['country_id'] = country_id
        vals['state_ids'] = request.env['res.country.state'].sudo().search([('country_id', '=', country_id.id)])
        vals['subscription_id'] = False
        vals['primary'] = False
        vals['child_ids'] = []
        vals['rules'] = []
        vals['membership_type'] = type or 'standard'
        path = request.httprequest.path
        if type == 'standard':
            vals.update(self.get_package_details('standard'))
        elif type == 'premium':
            vals.update(self.get_package_details('premium'))
        elif type == 'international':
            vals.update(self.get_package_details('international'))
        if path in ['/membership-step1', '/membership-step1/' + type]:
            return request.render('sale_subscription_extension.t_secondpage', vals)
        elif path in ['/membership-step2', '/membership-step2/' + type]:
            return request.render('sale_subscription_extension.t_thirddpage', vals)
        elif path in ['/membership-step3', '/membership-step3/' + type]:
            return request.render('sale_subscription_extension.t_fourthpage', vals)
        return request.render('sale_subscription_extension.t_secondpage', vals)

    def get_package_details(self, package_name):
        vals = {
            'pricing': [],
            'products': False,
            'discount': 0,
            'total': 0,
            'type': 'standard',
        }
        if package_name == 'standard':
            products = request.env['product.template'].sudo().search(
                [('default_code', 'in', ['STAND-ADULT', 'STAND-YOUTH', 'STAND-SENIOR'])])
            for p in products:
                items = request.env["product.pricelist.item"].sudo().search(
                    [('product_tmpl_id', '=', p.id)])
                pricelist_items = items.filtered(lambda x: 'direct care' in x.pricelist_id.name.lower())
                if len(pricelist_items) > 1:
                    pricelist_items = pricelist_items[0]
                pricelist = pricelist_items.pricelist_id
                price = pricelist.get_product_price(p, 1, False)
                if not price:
                    price = p.list_price
                vals['pricing'].append(price)
            vals['products'] = products.mapped('id') or [0, 0, 0]
            vals['discount'] = products.mapped('subscription_discount') or [0, 0, 0]
            vals['discount_type'] = products.mapped('subscription_discount_type') or ['perc','perc','perc']
            vals['total'] = sum(products.mapped('list_price')) or 0
            vals['type'] = 'standard'
            return vals
        elif package_name == 'premium':
            products = request.env['product.template'].sudo().search(
                [('default_code', 'in', ['PREM-ADULT', 'PREM-YOUTH', 'PREM-SENIOR'])])
            for p in products:
                items = request.env["product.pricelist.item"].sudo().search(
                    [('product_tmpl_id', '=', p.id)])
                pricelist_items = items.filtered(lambda x: 'direct care' in x.pricelist_id.name.lower())
                if len(pricelist_items) > 1:
                    pricelist_items = pricelist_items[0]
                pricelist = pricelist_items.pricelist_id
                price = pricelist.get_product_price(p, 1, False)
                if not price:
                    price = p.list_price
                vals['pricing'].append(price)
            vals['products'] = products.mapped('id') or [0, 0, 0]
            vals['discount'] = products.mapped('subscription_discount') or [0, 0, 0]
            vals['discount_type'] = products.mapped('subscription_discount_type') or ['perc', 'perc', 'perc']
            vals['total'] = sum(products.mapped('list_price')) or 0
            vals['type'] = 'premium'
            return vals
        elif package_name == 'international':
            products = request.env['product.template'].sudo().search(
                [('default_code', 'in', ['INT-ADULT', 'INT-YOUTH', 'INT-SENIOR'])])
            for p in products:
                items = request.env["product.pricelist.item"].sudo().search(
                    [('product_tmpl_id', '=', p.id)]) 
                pricelist_items = items.filtered(lambda x: 'direct care' in x.pricelist_id.name.lower())
                if len(pricelist_items) > 1: 
                    pricelist_items = pricelist_items[0]
                pricelist = pricelist_items.pricelist_id
                price = pricelist.get_product_price(p, 1, False)
                if not price:
                    price = p.list_price
                vals['pricing'].append(price)
            vals['products'] = products.mapped('id') or [0, 0, 0]
            vals['discount'] = products.mapped('subscription_discount') or [0, 0, 0]
            vals['discount_type'] = products.mapped('subscription_discount_type') or ['perc', 'perc', 'perc']
            vals['total'] = sum(products.mapped('list_price')) or 0
            vals['type'] = 'international'
            return vals

    @http.route(
        ['/family-standard-membership', '/family-premium-membership', '/family-premium-international-membership'],
        type='http', auth="public", website=True, methods=["POST", "GET"])
    def membership_standard(self, **post):
        vals = {
            'pricing': [],
            'products': False,
            'discount': 0,
            'total': 0,
            'type': 'standard',
        }
        path = request.httprequest.path
        if path == '/family-standard-membership':
            template = 'sale_subscription_extension.template_family_standard_pricing'
            vals = self.get_package_details('standard')
        elif path == '/family-premium-membership':
            template = 'sale_subscription_extension.template_family_premium_pricing'
            vals = self.get_package_details('premium')
        elif path == '/family-premium-international-membership':
            template = 'sale_subscription_extension.template_family_prem_international_pricing'
            vals = self.get_package_details('international')
        return request.render(template, vals)

    @http.route(['/get_paystack_aquirer_data'], type='json', auth="public", website=True, methods=["POST", "GET"])
    def get_paystack_aquirer_data(self, **post):
        acquirer = request.env['payment.provider'].sudo().search(
            [('code', '=', post.get('provider', 'paystackAcquirer'))], limit=1)
        return {
            'acquirer_id': acquirer.id,
            'merchant': request.env.user.company_id.name,
            'return_url': '/family/payment/done',
            'currency': 'NGN',
            'currency_id': request.env['res.currency'].sudo().search([('name', '=', 'NGN')], limit=1).id,
            'invoice_num': random.randrange(999, 10000, 1),
            'paystack_public_key': acquirer.paystack_public_key,
            'environment': acquirer.environment,
        }

    @http.route(['/get_rave_aquirer_data'], type='json', auth="public", website=True, methods=["POST", "GET"])
    def get_rave_aquirer_data(self, **post):
        acquirer = request.env['payment.provider'].sudo().search(
            [('code', '=', post.get('provider', 'rave'))], limit=1)

        return {
            'acquirer_id': acquirer.id,
            'merchant': request.env.user.company_id.name,
            'return_url': '/family/payment/done',
            'currency': 'NGN',
            'currency_id': request.env['res.currency'].sudo().search([('name', '=', 'NGN')], limit=1).id,
            'invoice_num': random.randrange(999, 10000, 1),
            'rave_pub_key': acquirer.rave_public_key,
            'environment': acquirer.environment,
        }

    @http.route(['/membership_payment/process'], methods=['POST', 'GET'], type='json', auth='public')
    def payment_membership_process(self, **post):
        SaleOrder = request.env['sale.order'].sudo()
        SubBeneficiary = request.env['sale.subscription.beneficiaries'].sudo()
        membership_data = post.get('membership_data')
        partner = False
        adult, youth, senior = 0, 0, 0

        try:
            # count number of package bought for each class
            if membership_data.get('members'):
                adult = sum(x.get('family_class') == 'adult' for x in membership_data.get('members'))
                youth = sum(x.get('family_class') == 'youth' for x in membership_data.get('members'))
                senior = sum(x.get('family_class') == 'senior' for x in membership_data.get('members'))

            # check the class of beneficiary and add it to package
            beneficiary = membership_data.get('beneficiary')
            if beneficiary and beneficiary.get('family_class'):
                if beneficiary.get('family_class') == 'adult':
                    adult = adult + 1
                elif beneficiary.get('family_class') == 'youth':
                    youth = youth + 1
                elif beneficiary.get('family_class') == 'senior':
                    senior = senior + 1

            # create or update beneficiary
            if beneficiary and beneficiary.get('patientId'):
                patient = self.find_member(membership_data.get('beneficiary').get('patientId'),
                                        membership_data.get('beneficiary').get('verify_dob')
                                        )
                partner = request.env['res.partner'].sudo().browse(patient.get('id'))
            else:
                dob = beneficiary.get("dob")
                dob = parser.parse(dob)
                state = request.env['res.country.state'].sudo()
                if beneficiary.get("state"):
                    state = state.browse([int(beneficiary.get("state"))])
                partner = request.env['res.partner'].sudo().create({
                    'lastname': beneficiary.get("lastname"),
                    'firstname': beneficiary.get("other_name"),
                    'phone': beneficiary.get("phone"),
                    'email': beneficiary.get("email"),
                    'dob': dob,
                    'state_id': state and state.id,
                    'gender': beneficiary.get("gender"),
                    'street': beneficiary.get("street"),
                    'city': beneficiary.get("city"),
                    'country_id': state and state.country_id and state.country_id.id,
                    'lga': beneficiary.get("lga"),
                })

            # create beneficiary record
            SubBeneficiary = SubBeneficiary.create({
                'partner_id': partner.id
            })

            # create empty sales order
            so = SaleOrder.create({
                'partner_id': partner.id,
                'payer_id': partner.id,
            })
            so.onchange_partner_id()

            # create sales order line depending on the packages
            if membership_data.get('membership_type') in ['standard', 'premium', 'international']:
                if membership_data.get('adult') and adult > 0:
                    prod = request.env['product.template'].browse([membership_data.get('adult').get('product_id')])
                    request.env['sale.order.line'].sudo().create({
                        'product_id': prod.product_variant_id.id,
                        'order_id': so.id,
                        'product_uom_qty': adult,
                        'price_unit': membership_data.get('adult').get('price'),
                    })
                if membership_data.get('youth') and youth > 0:
                    prod = request.env['product.template'].browse([membership_data.get('youth').get('product_id')])
                    request.env['sale.order.line'].sudo().create({
                        'product_id': prod.product_variant_id.id,
                        'order_id': so.id,
                        'product_uom_qty': youth,
                        'price_unit': membership_data.get('youth').get('price'),
                    })
                if membership_data.get('senior') and senior > 0:
                    prod = request.env['product.template'].browse([membership_data.get('senior').get('product_id')])
                    request.env['sale.order.line'].sudo().create({
                        'product_id': prod.product_variant_id.id,
                        'order_id': so.id,
                        'product_uom_qty': senior,
                        'price_unit': membership_data.get('senior').get('price'),
                    })

                # create family members or update one
                if membership_data.get('members'):
                    dependent = []
                    for rec in membership_data.get('members'):
                        Partner = request.env['res.partner'].sudo()
                        if rec.get("patientId") and rec.get("verify_dob"):
                            patient = self.find_member(rec.get("patientId"), rec.get("verify_dob"))
                            old_partner = request.env['res.partner'].sudo().browse(patient.get('id'))
                            dependent.append(old_partner.id)
                        else:
                            state = request.env['res.country.state'].sudo()
                            if rec.get("state"):
                                state = state.browse([int(rec.get("state"))])
                            surname = rec.get('lastname', '')
                            firstname = rec.get('firstname', '')
                            middlename = rec.get('middlename', '')
                            dob = rec.get('dob', '')
                            dob = parser.parse(dob)
                            old_partner = Partner.create({
                                'parent_id': partner.id,
                                'lastname': surname,
                                'firstname': firstname,
                                'lastname2': middlename,
                                'phone': rec.get('phone', ''),
                                'email': rec.get('email', ''),
                                'dob': dob,
                                'state_id': state and state.id,
                                'gender': rec.get('gender', ''),
                                'street': rec.get('street', ''),
                                'city': rec.get('city', ''),
                                'country_id': state and state.country_id and state.country_id.id or rec.get('country', ''),
                                'lga': rec.get("lga"),
                            })
                            dependent.append(old_partner.id)
                    SubBeneficiary.write({
                        'dependent_ids': [(6, 0, dependent)]
                    })
                if so:
                    so.sudo().action_confirm()
                    journal_id = http.request.env['account.journal'].sudo().search(
                        [('code', '=', 'INV')], limit=1)
                    move_id = request.env['account.move'].sudo().create({
                        'partner_id': partner.id,
                        'currency_id': request.env.user.company_id.currency_id.id,
                        'type': 'out_invoice',
                        'date': fields.Date.today(),
                        'journal_id': journal_id.id,
                        'invoice_line_ids': [(0, 0, {
                            'name': line.product_id.name,
                            'ref': so.name,
                            'account_id': line.product_id.property_account_income_id.id or line.product_id.categ_id.property_account_income_categ_id.id,
                            'price_unit': line.price_unit,
                            'quantity': line.product_uom_qty,
                            'product_uom_id': line.product_id.uom_id.id,
                            'product_id': line.product_id.id,
                            'sale_line_ids': [(4, line.id)],
                        }) for line in so.order_line]
                    })

                    subscription_id = False
                    for line in so.order_line:
                        if line.subscription_id:
                            subscription_id = line.subscription_id
                    SubBeneficiary.sudo().write({'subscription_id': subscription_id})
                    if subscription_id:
                        subscription_id.sudo().validate_and_send_invoice(move_id)
                        # post payment
                        payment = request.env['account.payment.register'].sudo().with_context(
                            active_ids=move_id.ids,active_model='account.move').create({
                            'payment_date': fields.Date.today(),
                        })
                        payment.create_payments()

            return '/buymembership-final'
        except Exception as e:
            pass