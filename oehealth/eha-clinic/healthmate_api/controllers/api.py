import json
import logging
import re
import werkzeug.wrappers
import pyotp
import requests
from datetime import datetime, timedelta
from odoo import fields

from odoo import http, _
from odoo.http import request, Response
from odoo.addons.eha_auth.controllers.helpers import validate_token, validate_secret_key, invalid_response, valid_response
from odoo.addons.auth_signup.models.res_partner import SignupError
from requests.auth import HTTPBasicAuth
from odoo.exceptions import AccessDenied
from odoo.addons.phone_validation.tools import phone_validation
from .main import APIController
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)
MAX_OTP_TIME = 5.0  # maximum otp time before expiration


class ApiController(APIController):

    @validate_token
    @http.route(['/api/v1/create_payment'], type="http", auth="none", methods=["POST"], csrf=False)
    def create_payment(self, **post):
        """Register payment for existing invoice

        Args:
            dict: post data

        Returns:
            json: Returns json doc containing status of payment registration
        Sample Request:
            url = "http://localhost:8069/api/v1/create_payment"
            payload = {
                "invoice_no": "INV-0000011",
                "user_id": 21,
                "payment_reference": "REF-0009999", #(ref from flutterwave)
                "payment_gateway": "rave",
            }

            headers =  {
                "token":"my_lovely_and_highly_secure_token"}
            req = requests.post(url, data=payload, headers=headers)
            req.json()
        """
        invoiceno = post.get('invoice_no', '').strip()
        # this is actually a user id not partner id
        user_id = post.get('user_id', '').strip()
        payment_gateway = post.get('payment_gateway', '').strip()
        payment_reference = post.get('payment_reference', '').strip()
        company_id = request.env.user.company_id.id
        _logger.info(
            f"Registering payment for invoice {invoiceno} with user id {user_id}")

        _parameters = all(
            [invoiceno, user_id, payment_gateway, payment_reference])
        if not _parameters:
            return invalid_response(
                "missing_parameter",
                "either of the following are missing"
                " [invoice_no, user_id, payment_gateway, payment_date, payment_reference]",
                400,
            )

        # ensure the partner ID exists
        user = user = request.env['res.users'].sudo().search(
            [('id', '=', int(user_id))])
        if not user:
            return invalid_response(
                "user_not_found",
                f"User with ID {user_id} not found.",
                400
            )
        partner = user.partner_id
        # partner = request.env['res.partner'].sudo().browse(int(partner_id))
        if not partner:
            return invalid_response(
                "partner_not_found",
                f"User with ID {user_id} don't have a related partner",
                400,
            )

        invoice = (request.env['account.move'].sudo().search(
            [("name", "=", invoiceno), ]))
        if not invoice:
            return invalid_response(
                "invoice_not_found",
                f"Invoice with number {invoiceno} not found.",
                400,
            )

        if not invoice.state == "posted":
            return invalid_response(
                "invalid_invoice_state",
                f"You can only register payment for posted invoices.",
                400,
            )

        if invoice.payment_state == "paid":
            return valid_response(
                data={},
                status=200,
                message="Invoice is already paid"
            )

        acquirer = request.env['payment.provider'].sudo().search(
            [('code', '=', payment_gateway)],
            limit=1
        )

        if not acquirer:
            return invalid_response(
                "payment_gateway_not_found",
                f"Payment gateway '{payment_gateway}' not found or configured in odoo",
                400,
            )
        if acquirer.state not in ['enabled', 'test']:
            return invalid_response(
                "payment_gateway_not_enabled",
                f"Payment gateway '{payment_gateway}' not enabled in odoo",
                400,
            )
        default_journal = request.env['account.journal'].sudo().search(
            [
                ('type', '=', 'bank'),
                ('company_id', '=', company_id)
            ],
            limit=1
        )
        journal = acquirer.journal_id and acquirer.journal_id or default_journal

        payment_method = request.env['account.payment.method'].sudo().search(
            [
                ('code', '=', 'manual'),
                ('payment_type', '=', 'inbound')
            ],
            limit=1
        )
        vals = {
            'payment_date': fields.Date.today(),
            'move_id': invoice.id,
            # 'invoice_ids': [(4, invoice.id)],
            'amount': invoice.amount_residual_signed,
            'ref': payment_reference,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': journal.id,
            'payment_method_id': payment_method and payment_method.id or 1,
            'partner_id': partner.id,
        }
        payment = request.env['account.payment'].sudo().create(vals)
        payment.post()

        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "status_code": 200,
                    "message": "successful"
                }
            )
        )

    @validate_token
    @http.route(['/api/v1/subscription/create_payment'], type="json", auth="none", methods=["POST"], csrf=False)
    def create_subscription_payment(self, **kw):
        """Register payment for new/existing subscription

        Args:
            dict: post data

        Returns:
            json: Returns json doc containing status of payment registration

        params = {"user_id":219,"payment_reference":"4pmstlz2bn","payment_gateway":"paystack",
           "is_subscription_renewal":False,
          "isDiscounted": False,
           "product_ids":[3660],
           "discounts":[{"product_id":3660,"perc_discount":14.280000000000001}],
           "plan":"Standard","beneficiaries":[
               {"name":"Jude Fsa","phone":"+2349081158719","email":"refas@gmail.com","gender":"Female","dob":"2011-12-23"}
               ]
           }

        Sample Request:
            url = "http://localhost:8069/api/v1/create_payment"
            payload = {
                "user_id": 21,
                "payment_reference": "REF-0009999", #(ref from flutterwave)
                "payment_gateway": "rave",
                "is_subscription_renewal": True,
                "isDiscounted": True, # true if single membership
            }
            if is_subscription_renewal
                payload = {
                    ...
                    "subscription_id": 11,
                }
            if not is_subscription_renewal
                payload = {
                    ...
                    "product_ids": [13, 15],
                    "plan": "standard",
                    "beneficiaries": [
                        {
                            'name': 'full_name',
                            'phone': 'phone_number',
                            'email': 'email address',
                            'gender': 'gender',
                            'dob': 'date of birth', yy-mm-dd mm/dd/yy
                            'is_primary_beneficiary': True,
                            'is_staff': '',
                            'address': '',
                            'plan': '',
                        }, {}, {},
                    ]
                }
            headers =  {
                "token":"my_lovely_and_highly_secure_token"}
            req = requests.post(url, data=payload, headers=headers)
            req.json()
        """
        # this is to remove the default json typed endpoints response format to normal response object
        # request._json_response = self.alternative_json_response.__get__(request, JsonRequest)
        # Response.status = '400'

        post = json.loads(request.httprequest.data.decode("utf8"))
        discounts_from_payload = post.get("discounts")
        # this is actually a user id not partner id
        user_id = post.get('user_id', '')
        payment_gateway = post.get('payment_gateway', '').strip()
        payment_reference = post.get('payment_reference', '').strip()
        company_id = request.env.user.company_id.id
        is_subscription_renewal = post.get('is_subscription_renewal', '')
        subscription = False
        isDiscounted = post.get('isDiscounted')
        user = request.env['res.users'].sudo().search([('id', '=', user_id)])
        subscription_beneficiaries = []
        if not user:
            return {
                "error": "user_not_found",
                "message": f"User with id {user_id} not found.",
                "status_code": 400
            }

        billing_partner = user.partner_id
        # ensure the partner ID exists
        if not billing_partner:
            return {
                "error": "partner_not_found",
                "message": f"User with ID {user_id} don't have a related partner",
                "status_code": 400
            }

        if is_subscription_renewal:
            subscription_id = post.get('subscription_id', '')
            # _parameters = all([user_id, payment_gateway, payment_reference, is_subscription_renewal, subscription_id])
            _parameters = all([user_id, payment_gateway, payment_reference,
                              is_subscription_renewal, subscription_id])
            if not _parameters:
                return {
                    "error": "missing_parameter values",
                    "message": "either of the following are missing [user_id, payment_gateway, payment_reference, is_subscription_renewal, subscription_id]",
                    "status_code": 400
                }

            _logger.info(
                f"Renewing subscription with id: {subscription_id} with user id {user_id}")
            subscription = request.env['sale.order'].sudo().search(
                [('id', '=', int(subscription_id))])
            if not subscription:
                return {
                    "error": "Invalid Subscription Id",
                    "message": f"No valid subscription record with subscription id: {subscription_id}",
                    "status_code": 400
                }

            # get the the current end date before renewing the subscription
            curr_end_date = subscription.current_end_date or subscription.end_date

            # renew the subscription by creating renewal sale order and invoice
            sale_order = subscription.create_renewal_order()
            sale_order.action_confirm()
            sale_order.sudo()._send_order_confirmation_mail() # Sending mail message removed
            invoice = sale_order.sudo()._create_invoices()[0]
            invoice.post()

            # handle the neccessary logics after renewing the subscription
            progress_stage = request.env['sale.order.stage'].sudo().search(
                [('sequence', '=', 20)], limit=1)
            subscription.update({'partner_id': billing_partner,
                                'start_date': curr_end_date, 'stage_id': progress_stage.id})
            new_current_end_date = subscription.current_end_date or subscription.end_date
            recurring_next_date = new_current_end_date + timedelta(days=1)
            subscription.update({'recurring_next_date': recurring_next_date})
            beneficiaries = request.env['sale.subscription.beneficiaries'].sudo().search(
                [('subscription_id', '=', subscription.id)])
            Patient = request.env['oeh.medical.patient'].sudo()
            for beneficiary in beneficiaries:
                patient = False
                Patient = request.env['oeh.medical.patient'].sudo()
                dob = beneficiary.dob
                related_patient = Patient.search(
                    [('partner_id', '=', beneficiary.partner_id.id)], limit=1)
                if related_patient:
                    patient = related_patient
                    subscription_beneficiaries.append(
                        beneficiary.partner_id.id)
                else:
                    if beneficiary.phone and dob:
                        patient = self.get_patient(beneficiary.phone, dob)
                if patient:
                    # sync patient to firebase
                    request.env['firebase.connector'].sudo(
                    ).firebase_sync_patients(patient)
        else:
            primary_beneficiary_role = request.env.ref(
                'sale_subscription_extension.subscription_role_primary_beneficiary')
            dependent_role = request.env.ref(
                'sale_subscription_extension.subscription_role_dependent')
            product_ids = post.get('product_ids', [])
            plan = post.get('plan', '')
            beneficiaries = post.get('beneficiaries')
            _parameters = all(
                [user_id, payment_gateway, payment_reference, product_ids, plan, beneficiaries])
            if not _parameters:
                return {
                    "error": "missing_parameter",
                    "message": "either of the following are missing [user_id, billing_details, payment_gateway, payment_date, payment_reference, product_ids, plan, beneficiaries]",
                    "status_code": 400
                }

            # billing_partner = request.env['res.partner'].sudo().browse(partner.id)
            if not billing_partner:
                return {
                    "error": "billing_partner_not_fount",
                    "message": f"Billing partner cannot be found using the user id {user_id}",
                    "status_code": 400
                }

            pricelist = request.env['product.pricelist'].sudo().search(
                [('plan_code', 'ilike', plan)], limit=1)
            if not pricelist:
                return {
                    "error": "Pricelist not found",
                    "message": "Pricelist cannot be fount",
                    "status_code": 400
                }

            sale_value = {
                'partner_id': billing_partner.id,
                'payer_id': billing_partner.id,
                'partner_invoice_id': billing_partner.id,
                'pricelist_id': pricelist.id
            }
            sale_order_line_list = []
            for product_id in product_ids:
                discount = 0
                if isDiscounted:
                    disc_val = list(filter(lambda discount_val: discount_val.get(
                        'product_id') == product_id, discounts_from_payload))
                    discount = disc_val and disc_val[0].get("perc_discount")
                product = request.env['product.product'].sudo().search(
                    [('id', '=', int(product_id))])
                if not product:
                    return {
                        "error": "Invalid Product Id",
                        "message": f"No valid product record with product id: {product_id}",
                        "status_code": 400
                    }
                so_line_val = {
                    'product_id': product.id,
                    'name': product.name,
                    'product_uom_qty': 1.000,
                    'product_uom': product.uom_id.id,
                    'discount': discount,
                    'price_unit': product.list_price,
                    'display_type': False
                }
                sale_order_line_list.append((0, 0, so_line_val))
            sale_value.update({'order_line': sale_order_line_list})
            sale_order = request.env['sale.order'].sudo().create(sale_value)
            sale_order.action_confirm()
            sale_order.sudo()._send_order_confirmation_mail()

            # subscription_id will be create if the product is a subscription product
            # subscription = sale_order.order_line.mapped('subscription_id')[
            #     0] if sale_order.order_line.mapped('subscription_id') else False
            subscription = sale_order.subscription_id
            if not subscription:
                return {
                    "error": "subscription not created",
                    "message": "Subscription could not be created! Make sure the provided product is a subscription product",
                    "status_code": 400
                }

            for beneficiary in beneficiaries:
                if not beneficiary.get('dob'):
                    return {
                        "error": "Empty date of birth",
                        "message": "Empty date of birth, provide date of birth",
                        "status_code": 400
                    }
                dob = self.get_dob(beneficiary.get('dob'))
                formatted_dob = self.validate_format_date(dob)
                Patient = request.env['oeh.medical.patient'].sudo()
                pure_phone = beneficiary.get('phone')
                patient = self.get_patient(pure_phone, dob)
                if not patient:
                    fname, lastname2, lastname = self.format_return_name(
                        beneficiary.get('name'))
                    patient_vals = {
                        "firstname": fname,
                        "lastname2": lastname2,
                        "lastname": lastname,
                        "sex": 'Male' if beneficiary.get('gender').lower() == 'male' else 'Female',
                        "dob": formatted_dob,
                        "email": beneficiary.get('email'),
                        "gender": beneficiary.get('gender'),
                        "phone": pure_phone,
                        "street": beneficiary.get('address'),
                        "city": beneficiary.get('city'),
                        "property_product_pricelist": pricelist.id,
                        "active_subscription": [subscription.id]
                    }
                    patient = Patient.create(patient_vals)
                subscriptions = patient.active_subscription.ids
                # subscriptions.append(subscription.id)
                # patient.update({"is_synced_to_firebase": True,
                patient.update({"property_product_pricelist": pricelist.id, 
                                "active_subscription": subscriptions})
                beneficiary_line_vals = {
                    "subscription_id": subscription.id,
                    "partner_id": patient.partner_id.id,
                    "dob": formatted_dob,
                    "gender": beneficiary.get("gender"),
                    "phone": pure_phone,
                    "plan_id": product.plan_id.id,
                    "role_id": primary_beneficiary_role.id if beneficiary.get('is_primary_beneficiary') else dependent_role.id
                }
                beneficiaryrec = request.env['sale.subscription.beneficiaries'].sudo().create(
                    beneficiary_line_vals)
                subscription_beneficiaries.append(beneficiaryrec.partner_id.id)
                # sync patient to firebase
                # request.env['firebase.connector'].sudo(
                # ).firebase_sync_patients(patient)
            invoice = sale_order.sudo()._create_invoices()[0]
            invoice.post()
        acquirer = request.env['payment.provider'].sudo().search(
            [('code', '=', payment_gateway)], limit=1)
        if not acquirer:
            return {
                "error": "payment_gateway_not_found",
                "message": f"Payment gateway '{payment_gateway}' not found or configured in odoo",
                "status_code": 400
            }
        if acquirer.state not in ['enabled', 'test']:
            return {
                "error": "payment_gateway_not_enabled",
                "message": f"Payment gateway '{payment_gateway}' not enabled in odoo",
                "status_code": 400
            }
        default_journal = request.env['account.journal'].sudo().search(
            [
                ('type', '=', 'bank'),
                ('company_id', '=', company_id)
            ],
            limit=1
        )
        journal = acquirer.journal_id and acquirer.journal_id or default_journal

        payment_method = request.env['account.payment.method'].sudo().search(
            [
                ('code', '=', 'manual'),
                ('payment_type', '=', 'inbound')
            ],
            limit=1
        )

        vals = {
            'payment_date': fields.Date.today(),
            'invoice_ids': [(4, invoice.id)],
            'amount': invoice.amount_residual_signed,
            'ref': payment_reference,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': journal.id,
            'payment_method_id': payment_method and payment_method.id or 1,
            'partner_id': billing_partner.id,
        }
        payment = request.env['account.payment'].sudo().create(vals)
        payment.post()

        invoice_details = {
            'id': invoice.id,
            # INV-2021-14001
            'invoice_code': "-".join((invoice.name).split("/")),
            'reference_number': invoice.name,
            'invoice_date': datetime.strftime(invoice.invoice_date, '%Y-%m-%d') if invoice.invoice_date else None,
            'due_date': datetime.strftime(invoice.invoice_date_due, '%Y-%m-%d') if invoice.invoice_date_due else None,
            'source': 'Healthmate',
            'total': invoice.amount_total,
            'amount_due': invoice.amount_residual,
            'bank': invoice.partner_bank_id.bank_id.name or None,
            'account_number': invoice.partner_bank_id.acc_number or None,
            'lines': [{
                'product': line.product_id.name,
                'quantity': line.quantity,
                'unit_price': line.price_unit,
                'amount': line.price_subtotal,
            } for line in invoice.invoice_line_ids]
        }
        line = subscription.mapped('recurring_invoice_line_ids')[0]
        current_end_date = subscription.current_end_date or subscription.end_date
        subscription_details = {
            'subscription_id': subscription.id,
            'code': subscription.code,
            'start_date': fields.Date.to_string(subscription.start_date) if subscription.start_date else None,
            'renewal_date': fields.Date.to_string(current_end_date) if current_end_date else None,
            'price': subscription.recurring_total,
            'plan': line.product_id.plan_id and line.product_id.plan_id.name or None,
        }
        request.env['firebase.connector'].sudo(
        ).firebase_sync_invoice(user, invoice_details)
        Response.status = '200'
        return {"status_code": 200, "message": "successful", "invoice": invoice_details, "subscription": subscription_details,
                "beneficiaries": subscription_beneficiaries}

    @validate_secret_key
    @http.route(['/api/v1/users/<email>', '/api/v1/users'], type="http", auth="none", csrf=False)
    def check_user(self, email=None):
        """
        Verifies if a user with same email exists.  
        Args:
            **id: refers to the patient_id (the odoo system generated Id).
        Returns:
            bool : Returns True if user with login as email exists
        Sample Request:
            url = "http://localhost:8069/api/v1/users/ohi@mail.com"
            headers =  {
                "secret-key":"my secret key"}
            req = requests.get(url, headers=headers)
            req.json()
        """

        if not email:
            return invalid_response(
                "bad_request",
                "Bad Request",
                400,
            )

        model = "res.users"
        user = (
            request.env[model].sudo().search([("login", "=", email)])
        )
        if not user:
            return invalid_response(
                "user_not_found",
                "User with email %s was not found." % email,
                400,
            )
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "status_code": 200,
                    "status": True
                }
            )
        )

    @validate_token
    @http.route(['/api/v1/patients/search'], type="http", methods=["GET"], auth="none", csrf=False)
    def search_patient(self):
        """
        Returns patients that meet search criteria
        Sample Request:
            url = "http://localhost:8069/api/v1/patients/search?pno=HP0001&dob=2021-12-31&phone=+2348035279367"
            headers =  {"token":"token_962d374c024c0cc56c21eeba9ae2fa03b6d191c0"}
            req = requests.get(url, headers=headers)
            req.json()
        """

        patient_no = request.params.get('pno', '')
        dob = request.params.get('dob', False)  # date format yyyy-mm-dd
        phone_no = request.params.get('phone', '').strip()
        unique_no = patient_no or phone_no
        Patient = request.env['oeh.medical.patient'].sudo()
        _logger.info(f"searching patient with ID or Phone {unique_no} ...")

        if patient_no:
            patient = (Patient.search([
                ('identification_code', '=', patient_no), ('dob', '=', dob)
            ]))
        else:
            # try to search patient with phone or mobile no
            formatted_phone = phone_no if phone_no.startswith(
                "+") else f"+{phone_no}"
            patient = Patient.find_patient_by_phone_dob(formatted_phone, dob)
            # patient = Patient.browse([patient_dict['id']]) if patient_dict else False

            # most of our patients do not have their phone in international format
            # if patient is not found, and phone number is Nigerian no.
            # lets strip the first 4 digits and replace with 0 and try again
            phone = f"0{phone_no[4:]}" if len(phone_no) > 4 else False
            if not patient and phone:
                patient = Patient.find_patient_by_phone_dob(phone, dob)
                # patient = Patient.browse([patient_dict['id']]) if patient_dict else False

        if not patient:
            return invalid_response(
                "patient_not_found",
                f"patient with ID or phone {unique_no} and dob {dob} was not found.",
                400,
            )

        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "status_code": 200,
                    "data": {
                        "patient_id": patient.id,
                        "patient_no": patient.identification_code,
                        "dob": fields.Date.to_string(patient.dob) or None,
                        "first_name": patient.firstname,
                        "last_name": patient.lastname,
                        "middle_name": patient.lastname2 or None,
                        "email": patient.email or patient.secondary_email or None,
                        "phone": patient.phone or patient.mobile or None,
                    }
                }
            )
        )

    @validate_token
    @http.route(['/api/v1/users/link_patient'], type="http", auth="none", methods=["POST"], csrf=False)
    def link_patient(self, **post):
        """
        Link patient to a user
        {
            "patient_no": "patient_id",
            "email": "email"
            "dob": "dob",
            "otp": "123456",
        }
        Args:
            **post: the request payload
        Sample Request:
            url = "http://localhost:8069/api/v1/users/link_patient"
            headers =  {"token":"token_962d374c024c0cc56c21eeba9ae2fa03b6d191c0"}
            req = requests.post(url, data=post, headers=headers)
            req.json()
        """

        patient_no = post.get('patient_id')
        phone_no = post.get('phone_no', '').replace(' ', '')
        dob = post.get('date_of_birth')
        otp = post.get('otp')
        email = post.get("email")
        unique_no = patient_no or phone_no
        Patient = request.env['oeh.medical.patient'].sudo()

        _logger.info(f"Linking patient with ID or Phone {unique_no} ...")

        if patient_no:
            patient = (request.env['oeh.medical.patient'].sudo().search([
                ('identification_code', '=', patient_no), ('dob', '=', dob)
            ]))
        else:
            # try to link with patient phone or mobile no
            formatted_phone = phone_no if phone_no.startswith(
                "+") else f"+{phone_no}"
            patient = Patient.find_patient_by_phone_dob(formatted_phone, dob)

            # most of our patients do not have their phone in international format
            # if patient is not found, and phone number is Nigerian no.
            # lets strip the first 4 digits and replace with 0 and try again
            phone = f"0{phone_no[4:]}" if len(phone_no) > 4 else False
            if not patient and phone:
                patient = Patient.find_patient_by_phone_dob(phone, dob)

        if not patient:
            return invalid_response(
                "patient_not_found",
                f"patient with ID or phone {unique_no} and dob {dob} was not found.",
                400,
            )

        if not otp:
            return invalid_response(
                "missing_parameter",
                "Missing OTP. Please provide an OTP and try again.",
                400,
            )

        if not email:
            return invalid_response(
                "missing_parameter",
                "Missing email. Please provide the email and try again.",
                400,
            )

        try:
            res = self.handle_otp(otp, email=email)
            if res.get("status") != "otp_verification_pass":
                return invalid_response(
                    res.get("status"),
                    res.get("message"),
                    400,
                )

            user = request.env["res.users"].sudo().browse([request.uid])
            user.write({'linked_patient_ids': [(4, patient.id)]})
            patient_details, evaluations, lab_tests, allergies, prescriptions, vaccinations, current_medications = request.env["firebase.connector"].extract_patient_fields(
                patient)
            # request.env["firebase.connector"].cron_sync_firebase()
            # flag patient record as synced to firebase
            patient.is_synced_to_firebase = True

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                headers=[("Cache-Control", "no-store"),
                         ("Pragma", "no-cache")],
                response=json.dumps(
                    {
                        "status_code": 200,
                        "data": {
                            "patient": patient_details[0] if patient_details else {},
                            "evaluations": evaluations,
                            "labtests": lab_tests,
                            "allergies": allergies,
                            "prescriptions": prescriptions,
                            "vaccinations": vaccinations,
                            "current_medications": current_medications
                        }
                    }
                )
            )
        except Exception as ex:
            return invalid_response(
                "bad_request",
                "Unable to Link Patient: %s" % str(ex),
                400,
            )

    @validate_token
    @http.route(['/api/v1/users/unlink_patient'], type="http", auth="none", methods=["POST"], csrf=False)
    def unlink_patient(self, **post):
        """
        unlink patient from user
        Args:
            **post: request payload
        Sample Request:
            url = "http://localhost:8069/api/v1/patients/1"
            headers =  {
                "token":"token_962d374c024c0cc56c21eeba9ae2fa03b6d191c0"}
            data = {
                'otp': 878890,
                'email': 'email'
            }
            req = requests.post(url, data=data, headers=headers)
            req.json()
        """

        patient_no = post.get('patient_id')
        dob = post.get('date_of_birth')

        patient = (request.env['oeh.medical.patient'].sudo().search([
            ('identification_code', '=', patient_no),
            ('dob', '=', dob)
        ]))
        if not patient:
            return invalid_response(
                "patient_not_found",
                "patient with no %s and date of birth %s was not found." % (
                    patient_no, dob),
                404,
            )

        try:

            user = request.env["res.users"].sudo().browse([request.uid])
            # (3, id, _) remove item from many many without deleting it
            user.write({'linked_patient_ids': [(3, patient.id)]})
            patient.is_synced_to_firebase = False

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                headers=[("Cache-Control", "no-store"),
                         ("Pragma", "no-cache")],
                response=json.dumps(
                    {
                        "status_code": 200,
                        "message": "Patient Unlinked successfuly!"
                    }
                )
            )
        except Exception as ex:
            return invalid_response(
                "bad_request",
                "Unable to Link Patient: %s" % str(ex),
                400,
            )

    @validate_token
    @http.route(['/api/v1/users/refresh_token'], type="http", auth="none", methods=["POST"], csrf=False)
    def refresh_token(self, **post):
        """
        Refresh Firebae JWT token
        Args:
            **post: request payload
        Sample Request:
            url = "http://localhost:8069/api/v1/patients/1"
            headers =  {
                "token":"token_962d374c024c0cc56c21eeba9ae2fa03b6d191c0"}
            data = {
                'jwt': base_64 string,
            }
            req = requests.post(url, data=data, headers=headers)
            req.json()
        """
        try:
            user = request.env["res.users"].sudo().browse([request.uid])
            custom_token = request.env['firebase.connector'].create_token_uid(
                user.login)
            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                headers=[("Cache-Control", "no-store"),
                         ("Pragma", "no-cache")],
                response=json.dumps(
                    {
                        "status_code": 200,
                        "jwt": custom_token
                    }
                ),
            )
        except Exception as ex:
            _logger.exception(ex)
            return invalid_response(
                "bad_request",
                "Unable to refresh firebase JWT: %s" % str(ex),
                400,
            )

    @validate_secret_key
    @http.route("/api/v1/auth/otp_confirm", methods=["POST"], type="http", auth="none", csrf=False)
    def confirm_otp(self, **post):
        ''' 
        Sample Request:
        Note: do not specify headers in the request
        url = "http://localhost:8069/api/v1/auth/otp_confirm"
        data = {
        'otp': '090099',
        'email': 'email',
        }
        '''
        current_time = datetime.now()
        otp = post.get("otp")
        if not otp:
            return invalid_response(
                "missing_parameter",
                "Missing OTP. Please provide an OTP and try again.",
                400,
            )

        email = post.get("email")
        if not email:
            return invalid_response(
                "missing_parameter",
                "Missing Counter. Please provide the eamil and try again.",
                400,
            )
        try:
            otp_secret = http.request.env['ir.config_parameter'].sudo(
            ).get_param('eha_website_hr_recruitment.otp_secret_key1', '')
            otp_record = request.env['otp.log'].sudo().search(
                [('email', '=', email), ('otp', '=', otp)])

            if not otp_record:
                return invalid_response(
                    "otp_verification_failed",
                    "OTP Verification failed. Invalid OTP. Please check and try again.",
                    400
                )

            time_difference = current_time - otp_record.timestamp
            time_difference_minutes = time_difference.seconds / 60

            if time_difference_minutes >= MAX_OTP_TIME:
                # delete otp record
                otp_record.unlink()
                return invalid_response(
                    "otp_verification_failed",
                    "OTP Verification failed. OTP has expired. Please request for another one.",
                    400,
                )

            _logger.info('OTP CONFIRM CALLED!')
            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                headers=[("Cache-Control", "no-store"),
                         ("Pragma", "no-cache")],
                response=json.dumps(
                    {
                        "status_code": 200,
                        "status": True
                    }
                ),
            )
        except Exception as ex:
            _logger.exception(ex)
            return invalid_response(
                "bad_request",
                "Unable to send OTP: %s" % str(ex),
                400,
            )

    @validate_secret_key
    @http.route("/api/v1/auth/otp_send", methods=["POST"], type="http", auth="none", csrf=False)
    def send_otp(self, **post):
        ''' 
        Sample Request: 
        Note: do not specify headers in the request
        url = "http://localhost:8069/api/v1/auth/otp_send"
        data = {
        'email': 'ohiageorge@gmail.com',
        }
        '''

        email = post.get("email")
        if not email:
            return invalid_response(
                "missing_parameter",
                "Missing Email. Please provide a valid email and try again.",
                400,
            )

        email_re = re.compile(r"""
        ([a-zA-Z][\w\.-]*[a-zA-Z0-9]     # username part
        @                                # mandatory @ sign
        [a-zA-Z0-9][\w\.-]*              # domain must start with a letter
         \.
         [a-z]{2,3}                      # TLD
        )
        """, re.VERBOSE)

        if not email_re.match(email):
            return invalid_response(
                "invalid_email",
                "Invalid Email. Please enter a valid email address",
                400,
            )

        try:
            otp_secret = http.request.env['ir.config_parameter'].sudo(
            ).get_param('eha_website_hr_recruitment.otp_secret_key1', '')
            totp = pyotp.TOTP(otp_secret, interval=1)
            otp = totp.now()
            OTPLog = request.env["otp.log"].sudo()

            # check if an OTP related to the giving number exist, if yes delete it before creating a new one
            otp_record = request.env['otp.log'].sudo().search(
                [('email', '=', email)])
            if otp_record:
                otp_record.unlink()
            OTPLog.create({"email": email, "otp": otp})
            vals = {
                'subject': 'Healthmate: Sign Up Verification Code',
                'body_html': "Here is your verification Code <strong>{}</strong>".format(otp),
                'email_to': email,
                'auto_delete': False,
                'email_from': '"EHA Clinics Ltd"<info@eha.ng>',
            }

            mail_id = request.env['mail.mail'].sudo().create(vals)
            mail_id.send()
            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                headers=[("Cache-Control", "no-store"),
                         ("Pragma", "no-cache")],
                response=json.dumps(
                    {
                        "status_code": 200,
                        "otp": otp,
                    }
                ),
            )
        except Exception as ex:
            _logger.exception(ex)
            return invalid_response(
                "bad_request",
                "Unable to send OTP: %s" % str(ex),
                400,
            )

    @validate_secret_key
    @http.route("/api/v1/auth/register", methods=["POST"], type="http", auth="public", csrf=False)
    def register(self, **post):
        ''' 
        Sample Request: 
        Note: do not specify headers in the request
        url = "http://localhost:8069/api/v1/auth/register"
        data = {
            'first_name': 'George',
            'last_name': 'Ohia',
            'email': 'admin@mail.com', 
            'password': 'admin',
            'confirm_password': 'admin',
        }
        '''

        email = post.get('email')
        first_name = post.get('first_name')
        last_name = post.get('last_name')
        passwd = post.get('password')
        confirm_passwd = post.get('confirm_password')
        try:
            if not email:
                raise SignupError(_('No email given for new user'))
            if not first_name:
                raise SignupError(_('No first_name given for new user'))
            if not last_name:
                raise SignupError(_('No last_name given for new user'))
            if not passwd:
                raise SignupError(_('No password given for new user'))
            if not confirm_passwd:
                raise SignupError(_('No confirm_password given for new user'))
            if passwd != confirm_passwd:
                raise SignupError(
                    _("Passwords do not match; please retype them."))

            if request.env["res.users"].sudo().search([("login", "=", email)]):
                raise SignupError(
                    _("Another user is already registered using this email address."))

            custom_token = request.env['firebase.connector'].create_token_uid(
                email)
            _logger.info('FB TOKEN '+custom_token)
            # signup user in odoo
            company_id = request.env.user.company_id.id
            user = request.env['res.users'].sudo().with_context(no_reset_password=True)._create_user_from_template({
                'email': email,
                'firstname': first_name,
                'lastname': last_name,
                'name': first_name + ' '+last_name,
                'login': email,
                'password': passwd,
                'company_id': company_id,
                'company_ids': [(6, 0, [company_id])],
                'is_healthmate_user': True
            })
            uid = user.id
            # retrieve or create a tokens
            token = request.env["api.token"].find_one_or_create_token(
                user_id=uid, create=True)

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                headers=[("Cache-Control", "no-store"),
                         ("Pragma", "no-cache")],
                response=json.dumps(
                    {
                        "status_code": 200,
                        "uid": uid,
                        "name": user.name,
                        'first_name': user.firstname,
                        'last_name': user.lastname,
                        "email": user.email or None,
                        "phone_number": user.partner_id.phone or None,
                        "linked_ids": None,
                        "company_id": request.env.user.company_id.id if uid else None,
                        "token": token,
                        "jwt": custom_token
                    }
                ),
            )
        except Exception as ex:
            _logger.exception(ex)
            return invalid_response(
                "bad_request",
                "Unable to Register User: %s" % str(ex),
                400,
            )

    @validate_secret_key
    @http.route("/api/v1/auth/login", methods=["POST"], type="http", auth="none", csrf=False)
    def signin(self, **post):
        ''' 
        Sample Request: 
        Note: do not specify headers in the request
        url = "http://localhost:8069/api/v1/auth/login"
        data = {
        'login': 'admin', 
        'password': 'admin'
        }
        req = requests.post(url, data=data)
        req.json()
        '''

        _token = request.env["api.token"]
        db = post.get("db")
        if not db:
            db = http.request.env['ir.config_parameter'].sudo(
            ).get_param('healthmate_api.db_name', '')
        username, password = (
            post.get("login"),
            post.get("password"),
        )
        _logger.error([db, username, password])
        _credentials_includes_in_body = all([db, username, password])
        if not _credentials_includes_in_body:
            # check the headers to see if credentials were passed via the header.
            headers = request.httprequest.headers
            username = headers.get("login")
            password = headers.get("password")
            _credentials_includes_in_headers = all([db, username, password])
            if not _credentials_includes_in_headers:
                return invalid_response(
                    "missing_parameter",
                    "either of the following are missing [username, password] db = %s" % db,
                    400,
                )

        # Login in odoo database:
        try:
            request.session.authenticate(db, username, password)
            _logger.error("Authentication Successful")
        except Exception as e:
            # Invalid database:
            info = "Invalid Login {}".format((e))
            error = "invalid_login"
            _logger.error(info)
            return invalid_response("wrong login credentials: "+str(e), error, 400)

        uid = request.session.uid
        # if odoo session uid is not set, then login failed:
        if not uid:
            info = "Login failed because the session UID was not set"
            error = "session_uid_not_found"
            _logger.error(info)
            return invalid_response(400, error, info)

        # # retrieve or create a tokens
        token = _token.find_one_or_create_token(user_id=uid, create=True)
        custom_token = request.env['firebase.connector'].create_token_uid(
            username)
        user = request.env['res.users'].sudo().search([('id', '=', uid)])
        user.write({"is_healthmate_user": True})
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "status_code": 200,
                    "uid": uid,
                    "name": user and user.name or None,
                    'first_name': user and user.firstname or None,
                    'last_name': user and user.lastname or None,
                    "email": user and user.email or None,
                    "phone_number": user and user.partner_id.phone or None,
                    "linked_ids": None,
                    "user_context": {}, #request.session.get_context() if uid else {},
                    "company_id": request.env.user.company_id.id if uid else None,
                    "token": token,
                    "jwt": custom_token
                }
            ),
        )

    @validate_secret_key
    @http.route("/api/v1/auth/change_password", methods=["POST"], type="http", auth="none", csrf=False)
    def change_password(self, **post):
        """
        data = {
            'login': 'abcd@domain.com',
            'old_password': 'abcdefg@9876',
            'new_password': 'abcdefg@1234',
            'confirm_password': 'abcdefg@1234',
        }
        """
        login = post.get("login")
        old_password = post.get("old_password")
        new_password = post.get("new_password")
        confirm_password = post.get("confirm_password")

        if not login or not old_password or not new_password or not confirm_password:
            return invalid_response(
                "missing_parameter",
                "either of the following are missing [login, old_password, new_password, confirm_password]",
                400,
            )

        if new_password != confirm_password:
            return invalid_response(
                "Passwords mismatch",
                "New password and confirm password did not match",
                400,
            )

        user = request.env['res.users'].sudo().search([('login', '=', login)])
        if not user:
            return invalid_response(
                "User could not be found",
                "User with email: {} could not be found".format(login),
                400,
            )

        try:
            user.with_user(user)._check_credentials(old_password)
        except AccessDenied:
            return invalid_response(
                "Wrong password",
                "The provided old password is not correct",
                400,
            )

        user.update({"password": new_password})
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "status_code": 200,
                    "status": "success"
                }
            ),
        )

    @validate_secret_key
    @http.route("/api/v1/auth/reset_password", methods=["POST"], type="http", auth="none", csrf=False)
    def reset_password(self, **post):
        """
        data = {
        'email': 'email',
        'new_password': 'abcdefg@98765',
        'confirm_password': 'abcdefg@98765',
        'otp': '123456',
        }
        """

        email = post.get("email")
        new_password = post.get("new_password")
        confirm_password = post.get("confirm_password")
        otp = post.get("otp")

        if not email or not new_password or not confirm_password or not otp:
            return invalid_response(
                "missing_parameter",
                "either of the following are missing [email, new_password, confirm_password, otp, email]",
                400,
            )

        if new_password != confirm_password:
            return invalid_response(
                "Passwords mismatch",
                "New password and confirm password did not match",
                400,
            )

        res = self.handle_otp(otp, email=email)
        if res.get("status") != "otp_verification_pass":
            return invalid_response(
                res.get("status"),
                res.get("message"),
                400,
            )

        user = request.env['res.users'].sudo().search([('login', '=', email)])
        user.update({"password": new_password})
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "status_code": 200,
                    "status": "success"
                }
            ),
        )

    @validate_secret_key
    @http.route("/api/v1/auth/request_phone_otp", methods=["POST"], type="http", auth="none", csrf=False)
    def request_phone_otp(self, **post):
        """
        API Endpoint for phone number verification. It send an otp to the provided user's phone number for verification.

        data = {
            "phone": "09068387166",
            "dial_code": "+234"
        }

        Returns: JSON object containing request status and the otp sent to the user's phone number
        """

        try:
            phone = post.get("phone")
            dial_code = post.get("dial_code")

            if not phone or not dial_code:
                return invalid_response(
                    "missing_parameter",
                    "One of these parameters are missing [phone number, dailing code]",
                    400,
                )

            if not dial_code.startswith("+") or len(dial_code) < 2:
                return invalid_response(
                    "Invalid parameter",
                    "Invalid dialing code",
                    400,
                )
        except:
            return invalid_response(
                "Invalid parameters",
                "One of these parameters are invalid [phone number, dailing code]",
                400,
            )

        phone_number = dial_code + phone

        try:
            otp_secret = http.request.env['ir.config_parameter'].sudo(
            ).get_param('eha_website_hr_recruitment.otp_secret_key1', '')
            totp = pyotp.TOTP(otp_secret, interval=1)
            otp = totp.now()
            OTPLog = request.env["otp.log"].sudo()

            # check if an OTP related to the giving number exist, if yes delete it before creating a new one
            otp_record = request.env['otp.log'].sudo().search(
                [('phone', '=', phone_number)])
            if otp_record:
                otp_record.unlink()

            OTPLog.create({"otp": otp, "phone": phone_number})
            otp_record = request.env['otp.log'].sudo().search(
                [('phone', '=', phone_number)])

            # send sms
            url = request.env['ir.config_parameter'].sudo(
            ).get_param('bulksms.api')
            token_id = request.env['ir.config_parameter'].sudo(
            ).get_param('bulksms.token.id')
            token_secret = request.env['ir.config_parameter'].sudo(
            ).get_param('bulksms.token.secret')
            headers = {"Content-Type": "application/json"}
            text = "{} is your verification code for Healthmate app".format(
                otp)
            vals = {
                "to": [phone_number],
                "body": text
            }

            res = requests.post(url, data=vals, auth=HTTPBasicAuth(
                token_id, token_secret), timeout=15)
            _logger.info('data %s' % res.json())

            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                headers=[("Cache-Control", "no-store"),
                         ("Pragma", "no-cache")],
                response=json.dumps(
                    {
                        "status_code": res.status_code,
                        "otp": otp,
                    }
                ),
            )
        except Exception as ex:
            _logger.exception(ex)
            return invalid_response(
                "bad_request",
                "Unable to send OTP: %s" % str(ex),
                400,
            )

    @validate_secret_key
    @http.route("/api/v1/auth/confirm_phone_otp", methods=["POST"], type="http", auth="none", csrf=False)
    def confirm_phone_otp(self, **post):
        """
        API Endpoint for verifying phone OTP.

        Sample Request:
        Note: do not specify headers in the request
        url = "http://localhost:8069/api/v1/auth/confirm_phone_otp"
        data = {
        'otp': '090099',
        'phone': '09068387166',
        }

        Returns: Json object containing request status and status of the given OTP verification.
        """

        otp = post.get("otp")
        phone_number = post.get("phone")

        if not otp or not phone_number:
            return invalid_response(
                "missing_parameter",
                "either of the following parameters are missing [OTP, phone]",
                400,
            )

        try:
            res = self.handle_otp(otp, phone=phone_number)
            if res.get("status") != "otp_verification_pass":
                return invalid_response(
                    res.get("status"),
                    res.get("message"),
                    400,
                )

            _logger.info('OTP CONFIRM CALLED!')
            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/json; charset=utf-8",
                headers=[("Cache-Control", "no-store"),
                         ("Pragma", "no-cache")],
                response=json.dumps(
                    {
                        "status_code": 200,
                        "status": True
                    }
                ),
            )
        except Exception as ex:
            _logger.exception(ex)
            return invalid_response(
                "bad_request",
                "Unable to send OTP: %s" % str(ex),
                400,
            )

    @validate_token
    @http.route(['/api/v1/patients/<id>'], type="http", auth="none", methods=["PATCH"], csrf=False)
    def patch(self, id=None, **payload):
        """
        Updates specific columns in patient record
        Args:
            **id: refers to the patient_id (the odoo system generated Id).
        Sample Request:
            url = "http://localhost:8069/api/v1/patients/1"
            headers =  {
                "token":"token_962d374c024c0cc56c21eeba9ae2fa03b6d191c0"}
            data = {
                'healthmate_is_registered_user': True,
                'healthmate_registration_date': datetime.now()
            }
            req = requests.patch(url, data=data, headers=headers)
            req.json()
        """
        model = "oeh.medical.patient"
        try:
            _id = int(id)
        except Exception as e:
            return invalid_response(
                "invalid object id", "invalid literal %s for id with base " % id
            )
        patient = (
            request.env[model].sudo().browse(_id)
        )
        if not patient:
            return invalid_response(
                "patient_not_found",
                "patient with %s was not found." % id,
                404,
            )
        try:
            patient.write(payload)
        except Exception as ex:
            return invalid_response("exception", ex.name, 401)
        else:
            return valid_response(
                "Successful",
                200
            )

    @validate_secret_key
    @http.route('/api/v1/labtest/search', methods=["GET"], type="http", auth="none", csrf=False)
    def labtest_search(self, **kw):
        """
            Sample Request: 
            Note: do not specify headers in the request
            url = "http://localhost:8069/api/v1/labtest/search"
            data = {
            'full_name': 'Ahmad Ameen', 
            'labtest_no': 'admin'
            }
            req = requests.post(url, data=data)
            req.json()
        """
        full_name = request.params.get("full_name", "").strip()
        labtest_no = request.params.get("labtest_no").strip().upper()
        if not full_name or not labtest_no:
            return invalid_response(
                "missing_parameter",
                "either of the following are missing"
                " [full_name, labtest_no]",
                400,
            )

        labtest_record = http.request.env['oeh.medical.lab.test'].sudo().search(
            [('name', '=', labtest_no)], limit=1)
        if not labtest_record:
            return invalid_response(
                "labtest_not_found",
                f"Labtest with number {labtest_no} not found.",
                400,
            )
        if not labtest_record.test_type.is_covid_19:
            return invalid_response(
                "labtest_not_covid19",
                "Labtest must be a covid19 test",
                400,
            )

        emr_full_name_list = [name.lower() for name in (
            labtest_record.patient.name).split(" ")]
        full_name_list = [name.lower() for name in full_name.split(" ")]
        if len(full_name_list) == 1:
            return invalid_response(
                "invalid_name",
                "At least two names must be provided",
                400,
            )
        counter = 0
        for name in full_name_list:
            if name in emr_full_name_list:
                counter += 1

        if counter < 2:
            return invalid_response(
                "labtest_not_found",
                "No record for the provided name",
                400,
            )

        if not labtest_record.state in ["Completed", "Reviewed"]:
            return invalid_response(
                "labtest_not_complited",
                "Test result is not yet available",
                400,
            )

        if labtest_record.sample_collection_date:
            display_date = labtest_record.sample_collection_date
        else:
            display_date = labtest_record.date_requested

        analysis_date = str(labtest_record.date_analysis).split(' ')[0]
        date = str(display_date).split(' ')[0]
        result_interpretation = labtest_record.mapped('lab_test_criteria').filtered(
            lambda name: name.name.startswith('Result Interpretation'))
        summary = {
            "labtest_no": labtest_no,
            "full_name": labtest_record.patient.name,
            "dob": str(labtest_record.patient.dob),
            "sample_collection_date": date,
            "analysis_date": analysis_date,
            "result": result_interpretation[0].result if result_interpretation else None,
            "passport_no": labtest_record.patient.passport_no if labtest_record.patient.passport_no else None,
            "location": labtest_record.branch_id.name if labtest_record.branch_id else None
        }
        base_url = request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        eha_labtest_report_url = base_url + \
            "/services/check-test-results/view-report?labtest_no={}".format(
                labtest_no)
        commonpass_labtest_report_url = base_url + \
            "/services/check-test-results/get-commonpass?format=pdf&labtest_no={}".format(
                labtest_no)
        commonpass_qrcode_url = base_url + \
            "/services/check-test-results/get-commonpass?format=qrcode&labtest_no={}".format(
                labtest_no)
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "status_code": 200,
                    "eha_labtest_report_url": eha_labtest_report_url,
                    "commonpass_labtest_report_url": commonpass_labtest_report_url if labtest_record.qr_code_commonpass else None,
                    "commonpass_qrcode_url": commonpass_qrcode_url if labtest_record.qr_code_commonpass else None,
                    "summary": summary,
                }
            ),
        )

    def handle_otp(self, otp, email=False, phone=False):
        """
            This returns the time difference between OTP time stamp and the current time in minutes

            Params str:otp, str:email or str:phone

            Returns int
        """

        current_time = datetime.now()

        otp_secret = http.request.env['ir.config_parameter'].sudo(
        ).get_param('eha_website_hr_recruitment.otp_secret_key1', '')
        otp_record = False

        if email:
            otp_record = request.env['otp.log'].sudo().search(
                [('email', '=', email), ('otp', '=', otp)])
        else:
            otp_record = request.env['otp.log'].sudo().search(
                [('phone', '=', phone), ('otp', '=', otp)])

        if not otp_record:
            return {
                "status": "otp_verification_failed",
                "message": "OTP Verification failed. Invalid OTP. Please check and try again.",
            }

        time_difference = current_time - otp_record.timestamp
        time_difference_minutes = time_difference.seconds / 60

        if time_difference_minutes >= MAX_OTP_TIME:
            # delete otp record
            otp_record.unlink()
            return {
                "status": "otp_verification_failed",
                "message": "OTP Verification failed. OTP has expired. Please request for another one.",
            }

        # delete otp record after verification to avoid reusing of the otp
        otp_record.unlink()

        return {
            "status": "otp_verification_pass",
            "message": "OTP verified successfully",
        }

    def get_dob(self, dob):
        dob_arr = dob.split('-')
        yy, mm, dd = dob_arr[0], dob_arr[1], dob_arr[2]
        return "{}/{}/{}".format(mm, dd, yy)

    def get_patient(self, phone, dob):
        Patient = request.env['oeh.medical.patient'].sudo()
        pure_phone = phone
        formated_phone = phone_validation.phone_format(
            phone, country_code=None, country_phone_code=None)
        no_dialcode_phone = f"0{pure_phone[4:]}" if len(
            pure_phone) > 4 else False

        # first search using the pure phone number
        patient = Patient.find_patient_by_phone_dob(pure_phone, dob)
        if not patient:
            # search using the formated phone number
            patient = Patient.find_patient_by_phone_dob(formated_phone, dob)

        if not patient:
            # search using the no dialing code phone number
            patient = Patient.find_patient_by_phone_dob(no_dialcode_phone, dob)

        return patient

    @validate_token
    @http.route('/api/v1/products/quantities', methods=["POST"], auth="public", crsf=False, website=True, type="json")
    def get_product_warehouse_quantities(self, product_details=[]):
        # required_fields = ['product_id', 'warehouse_id']
        product_details = request.jsonrequest.get("product_details")
        if not product_details:
            return ({
                "msg": "No products sent"
            })
        for product_detail in product_details:
            detail = self.get_product_quantity_in_warehouse(
                product_int_id=int(product_detail['product_id']),
                warehouse_int_id=int(product_detail['warehouse_id'])
            )
            product_detail.update(detail)
        return ({
            'product_details': product_details
        })

    def get_product_quantity_in_warehouse(self, product_int_id, warehouse_int_id):
        if not isinstance(product_int_id, int):
            product_id = int(product_int_id)
        if not isinstance(warehouse_int_id, int):
            product_id = int(warehouse_int_id)
        warehouse_id = request.env['stock.warehouse'].sudo().search(
            [('id', '=', warehouse_int_id)])
        location_id = warehouse_id and warehouse_id.view_location_id
        product_id = request.env['product.product'].sudo().search(
            [('id', '=', product_int_id)])
        errors = []
        resp = {
            'errors': "",
            'quantity': 0,
        }
        if not warehouse_id:
            errors.append(f"Warehouse {warehouse_int_id} does not exist")
        if not product_id:
            errors.append(f"Product {product_int_id} does not exist")
        if errors:
            resp["errors"] = ", ".join(errors)
            return resp
        else:
            quantity = product_id.with_context(
                warehouse=warehouse_int_id).virtual_available
            resp["quantity"] = quantity
        return resp
