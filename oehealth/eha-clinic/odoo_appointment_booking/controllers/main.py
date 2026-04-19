# -*- encoding: utf-8 -*-
from odoo.addons.eha_website.utils import get_payment_providers_details
from odoo.exceptions import ValidationError
from odoo.addons.phone_validation.tools import phone_validation
import json
import logging
import requests
from odoo import fields, _
from datetime import datetime, timedelta, date
from odoo import http, fields
from odoo.http import request, Controller, Response
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, safe_eval
_logger = logging.getLogger(__name__)


class BookingHome(Controller):

    def get_next_available_slot(self, available_slots=None):
        TimeSlotLines = request.env['time.slot.line'].sudo()
        if not available_slots:
            return TimeSlotLines
        available_slots_copy = available_slots
        available_slots = (slot for slot in available_slots_copy.sorted(
            key=lambda slot: (slot.appointment_slot_id, slot.id)))
        next_available_slot = next(available_slots)
        return next_available_slot

    @http.route("/api/v1/booking/locations", type="http", methods=['GET'], auth="api_token", csrf=False, website=False)
    def get_booking_locations(self):
        headers = [
            ('Content-Type', 'application/json'),
        ]
        locations = request.env['eha.branch'].sudo().search([])
        data = json.dumps({
            "locations": [{
                'id': location.id,
                'name': location.name
            }
                for location in locations], "size": len(locations)
        })
        return request.make_response(data, headers)

    @http.route("/api/v1/booking/locations/<int:location_id>/services", type="json", csrf=False, website=False)
    def get_booking_services(self, location_id):
        location = request.env['eha.branch'].sudo().search(
            [("id", "=", int(location_id))])
        if not location:
            #FIXME Response.status = "404"
            return {
                'error': {
                    'message': "Location not found!",
                    "code": 404
                }
            }

        booking_services = location.service_ids
        data = {
            "locationId": location_id,
            "services": [
                {
                    'id': service.id,
                    'name': service.name
                } for service in booking_services
            ],
            "size": len(booking_services)
        }
        return data

    # @http.route("/api/v1/booking/locations/<int:location_id>/services", type="http", methods=['GET'],
    # # auth="api_token",
    # csrf=False, website=False)
    # def get_booking_services(self, location_id):
    #     headers = [
    #         ('Content-Type', 'application/json'),
    #     ]
    #     location = request.env['eha.branch'].sudo().search(
    #         [("id", "=", int(location_id))])
    #     if not location:
    #         Response.status = "404"
    #         return request.make_response(
    #             data=json.dumps({
    #                 'error': {
    #                     'message': "Location not found!",
    #                     "code": 404
    #                 }
    #             }),
    #             headers=headers)
    #     booking_services = location.service_ids
    #     data = json.dumps({
    #         "locationId": location_id,
    #         "services": {
    #             "renderedServices": [
    #                     {
    #                         'id': service.id,
    #                         'name': service.name
    #                     } for service in booking_services
    #             ],
    #             "size": len(booking_services)
    #         }
    #     })
    #     return request.make_response(data, headers)

    @http.route("/api/v1/booking/locations/<int:location_id>/services/<int:service_id>/slots", auth="public", type="json", csrf=False, website=False)
    def get_booking_slots(self, location_id, service_id, booking_date=None, **kwargs):
        if not booking_date:
            if kwargs.get("booking_date"):
                booking_date = kwargs.get("booking_date")
            else:
                booking_date = request.jsonrequest.get(
                    "params")("booking_date")
        if isinstance(booking_date, str):
            booking_datetime = datetime.strptime(
                booking_date.replace("/", "-"), "%Y-%m-%d")
        if booking_datetime.date() < datetime.today().date():
            return {
                'message': "Date of booking is in the past",
                "code": 400
            }
        location = request.env['eha.branch'].sudo().search(
            [("id", "=", int(location_id))])
        if not location:
            # Response.status = "404"
            return {
                'message': "Location not found!",
                "code": 404
            }
        service = request.env['eha.booking.services'].sudo().search(
            [("id", "=", int(service_id))])
        if not service:
            # Response.status = "404"
            # Response.status = "404"
            return {
                'message': "Service not found!",
                "code": 404
            }
        if service not in location.service_ids:
            # Response.status = "404"
            return {
                'message': "The selected service is not rendered in the location selected!",
                "code": 404
            }
        slots = []
        available_slots = request.env['calendar.event'].sudo(
        ).get_available_time_slots(booking_date, service_id, location_id)
        if available_slots:
            slots = [slot._get_serialized_time_slots()
                     for slot in available_slots]
        data = {
            "status": "200",
            "data": {
                "locationId": location_id,
                "serviceId": service_id,
                "slots": {
                    "availableSlots": slots,
                    "size": len(slots)
                }
            }
        }
        return data

        """
        @http.route("/api/v1/booking/locations/<int:location_id>/services/<int:service_id>/slots", type="http", methods=['GET'], auth="api_token", csrf=False, website=False)
        def get_booking_slots(self, location_id, service_id, booking_date=None, **kwargs):
        headers = [('Content-Type', 'application/json')]
        if booking_date is None:
            booking_date = datetime.today().date()
        if isinstance(booking_date, str):
            booking_date = datetime.strptime(
                booking_date.replace("/", "-"), "%Y-%m-%d")
        if booking_date.date() < datetime.today().date():
            return request.make_response(
                data=json.dumps({
                    'error': {
                        'message': "Date of booking is in the past",
                        "code": 400
                    }
                }),
                headers=headers)
        location = request.env['eha.branch'].sudo().search(
            [("id", "=", int(location_id))])
        if not location:
            # Response.status = "404"
            return request.make_response(
                data=json.dumps({'error': {
                    'message': "Location not found!",
                    "code": 404
                }}),
                headers=headers)
        service = request.env['eha.booking.services'].sudo().search(
            [("id", "=", int(service_id))])
        if not service:
            # Response.status = "404"
            # Response.status = "404"
            return request.make_response(
                data=json.dumps({'error': {
                    'message': "Service not found!",
                    "code": 404
                }}),
                headers=headers)
        if service not in location.service_ids:
            # Response.status = "404"
            return request.make_response(
                data=json.dumps({'error': {
                    'message': "The selected service is not rendered in the location selected!",
                    "code": 404
                }}),
                headers=headers)
        slots = []
        available_slots = request.env['calendar.event'].sudo(
        ).get_available_time_slots(booking_date, service_id, location_id)
        if available_slots:
            slots = [slot._get_serialized_time_slots()
                     for slot in available_slots]
        data = {
            "status": "200",
            "data": {
                "locationId": location_id,
                "serviceId": service_id,
                "slots": {
                    "availableSlots": slots,
                    "size": len(slots)
                }
            }
        }
        return request.make_response(data=json.dumps(data), headers=headers)
        """

    @http.route("/api/v1/booking/locations/<int:location_id>/services/<int:service_id>/slots/<int:slot_id>", type="json", methods=['POST'],
                # auth="api_token",
                csrf=False)
    def book_appointment(self, location_id, service_id, slot_id, **kwargs):
        res = {}
        partner_info = kwargs.get('partnerInfo')
        if not isinstance(partner_info, dict):
            partner_info = safe_eval(partner_info)
        firstname = partner_info.get("firstName")
        secondname = partner_info.get("secondName")
        lastname = partner_info.get("lastName")
        phone = partner_info.get("phone")
        dob = partner_info.get("dob")
        sex = partner_info.get("sex")
        payment_status = kwargs.get("paymentStatus")
        date = kwargs.get("date")
        patient_db_id = kwargs.get("patientDatabaseId", False) and int(kwargs.get("patientDatabaseId", False))

        # validations
        if not partner_info:
            res.update({
                "message": "No partner Info provided",
                "status": "400",
            })
            return res
        if not firstname:
            res.update({
                "message": "Missing partner firstname",
                "status": "400",
            })
            return res
        if not lastname:
            res.update({
                "message": "Missing partner lastname",
                "status": "400",
            })
            return res
        if not phone:
            res.update({
                "message": "Missing partner phone",
                "status": "400",
            })
            return res
        if not safe_eval(payment_status):
            res["message"] = "Please make payment and continue"
            res["status"] = "400"
            return res
        if not date:
            res["message"] = "Please provide a valid date"
            res["status"] = "400"
            return res
        if not sex:
            res["message"] = "Please provide a valid sex"
            res["status"] = "400"
            return res
        service = request.env['eha.booking.services'].sudo().search(
            [("id", "=", int(service_id))])
        service_provider = service.service_providers and service.service_providers[
            0] or False
        if not service_provider:
            res.update({
                "status": "404",
                "message": f"No service provider found for this service!",
            })
            return res
        date_booking = date.replace("/", "-")
        date_booking = datetime.strptime(date_booking, "%Y-%m-%d")
        if date_booking.date() < datetime.today().date():
            res.update({
                'status': "400",
                'message': "You have provided a booking date in the past, please check and correct this",
            })
            return res
        slot = request.env['time.slot.line'].sudo().search(
            [("id", "=", int(slot_id))])

        available_slots = request.env['calendar.event'].sudo(
        ).get_available_time_slots(date_booking, service_id, location_id)
        if not available_slots:
            # Response.status = "404"
            res.update({
                'status': "400",
                'message': "This slot is not available",
            })
            return res

        if slot not in available_slots:
            next_slot = self.get_next_available_slot(available_slots)
            slot = next_slot

        Patient = request.env['oeh.medical.patient'].sudo()
        patient = Patient.search([("id", "=", patient_db_id)])
        if not patient:
            try:
                patient = Patient.create({
                    'firstname': firstname,
                    'lastname2': secondname,
                    'lastname': lastname,
                    'sex': sex,
                    'dob': dob,
                    'phone': phone,
                })
            except Exception as error:
                _logger.error(
                    f"****** Error while creating patient {error} ********")

        appointment_slot_id = slot.appointment_slot_id
        duration = appointment_slot_id.appointment_duration / \
            60 if appointment_slot_id.time_stamp_type == 'hour' else appointment_slot_id.appointment_duration
        start_datetime_str = f"{date_booking.strftime(DEFAULT_SERVER_DATE_FORMAT)} {slot.name}"
        start_datetime = datetime.strptime(
            start_datetime_str, DEFAULT_SERVER_DATETIME_FORMAT)
        stop_time = start_datetime + \
            timedelta(minutes=duration) if appointment_slot_id.time_stamp_type == 'min' else start_datetime + \
            timedelta(hours=duration)
        try:
            booking = request.env['calendar.event'].sudo().create({
                'eha_service_location_id': int(location_id),
                'service_id': int(service_id),
                'service_provider_id': service_provider.id,
                'strt_slot_time': slot.id,
                'strt_slot_time_text': slot.name,
                'booking_start_date': date,
                'partner_ids': [(4, patient.partner_id.id)],
                'start': start_datetime,
                'start_datetime': start_datetime,
                'stop': stop_time,
                'stop_datetime': stop_time,
                'user_id': int(request.env.ref('base.user_admin')),
                'is_online_booking': True,
            })
            Response.status = "201"
            res.update({
                "status": "201",
                "message": f"Booking {booking.sequence} was successfully created! for {date} {slot.name}",
            })
            return res
        except Exception as e:
            Response.status = "500"
            res.update({
                "status": "500",
                "message": f"Error creating booking \n{e}",
            })
            return res

    @http.route("/api/v1/booking/my-events", type="json", methods=['GET'], auth="api_token", csrf=False)
    def retrieve_appointments(self, **kwargs):
        res = {}
        partner_info = kwargs.get("partnerInfo")
        date_from = kwargs.get("from")
        date_to = kwargs.get("to")
        dob = partner_info.get("dob")
        phone = partner_info.get("phone")
        firstname = partner_info.get("firstName")
        lastname = partner_info.get("lastName")
        if not partner_info:
            res.update({
                "status": "400",
                "message": "No partner info provided",
            })
            return res
        if not phone:
            res.update({
                "status": "400",
                "message": "Missing phone number",
            })
            return res
        if not firstname or not lastname:
            res.update({
                "status": "400",
                "message": "First name or Last name missing in the provided payload."
            })
            return res
        if not date_from or not date_to:
            res.update({
                "status": "400",
                "message": "One or both of date 'from' and date 'to' is missing "
            })
            return res
        Patient = request.env['oeh.medical.patient'].sudo()
        patient = Patient.find_patient_by_phone_dob(phone, dob)
        partner = patient.partner_id
        if not partner:
            return {
                "error": "No contact found with the supplied credentials",
                "status": 404
            }
        partner_bookings = request.env['calendar.event'].sudo().search([
            ('partner_ids', 'in', partner.ids),
            ('booking_start_date', '>=', datetime.strptime(
                date_from, "%Y-%m-%d").date()),
            ('booking_start_date', '<=', datetime.strptime(
                date_to, "%Y-%m-%d").date()),
        ])
        serialized_bookings = [
            {
                "name": booking.name,
                "date": booking.booking_start_date
            } for booking in partner_bookings]
        return ({
            'bookings': serialized_bookings or None
        })

    def validate_fields(self, data):
        error_item = []
        productObj = request.env['product.product'].sudo()
        branch = request.env['eha.branch'].sudo()

        testlocation = data.get('order').get('test_location')
        productlist = data.get('order').get('products')
        source = data.get('source')
        partner = data.get('order').get('partner')
        coupon_code = data.get('coupon_code')

        if coupon_code:
            partner_coupon_id = request.env['res.partner'].sudo().search(
                [('coupon_code', '=', coupon_code)], order="id asc", limit=1)
            if partner_coupon_id:
                partner_phone = partner_coupon_id.phone or partner_coupon_id.mobile
                if not partner_phone:
                    error_item.append(
                        "Customer with coupon code Phone must be provided\n ")

        else:
            if not partner['patient_id']:
                if not partner.get('name'):
                    error_item.append("Customer Name must be provided\n ")
                phonecontact = partner.get('phone_contact')
                phonenumb = phonecontact.get(
                    'phone_number') or phonecontact.get('secondary_phone_number')
                if not phonenumb:
                    error_item.append("Customer Phone must be provided\n ")
                if not partner.get('email'):
                    error_item.append("Customer Email must be provided\n ")

        if productlist:
            for pd in productlist:
                product_id = pd.get('product_id') if pd.get(
                    'product_id') else False
                if product_id:
                    prodId = productObj.search(
                        [('id', '=', int(product_id))], limit=1)
                    if not prodId:
                        error_item.append(
                            "Product ID- {} does not exits \n ".format(product_id))

                    if int(pd.get('product_uom_qty')) < 0:
                        error_item.append(
                            "Product Quantity must be greater than 0\n ")

                    if pd.get('price'):
                        if type(pd.get('price')) in [float, int]:
                            if int(pd.get('price')) < 0:
                                error_item.append(
                                    "Product Price must not be lesser than 0\n ")
                        else:
                            error_item.append(
                                "Please Ensure that the product price is of type integer or float \n ")
                else:
                    error_item.append(
                        "No Product value found - Ensure you provide the Value \n ")
        else:
            error_item.append("You must provide at least one product")

        if source != "website":
            if testlocation:
                testlocationid = int(testlocation)
                branchid = branch.search(
                    [('id', '=', testlocationid)], limit=1)
                if not branchid:
                    error_item.append("Test location ID not found!")
            else:
                error_item.append("Please provide Test location!")
        patient_error_validation = self.patient_field_validation(
            data.get('cif_data'))
        error_item += patient_error_validation
        return error_item

    @http.route("/api/v1/calendar-payment", type="json", auth="public", methods=["POST", "GET"], csrf=False)
    def calendar_payment(self, **kw):
        """parameter = {
                "order": {
                    "order_ref": "healthmate order ref to ",
                    "payment_ref": "89jjfjjf",
                    "test_location": 4, #4, #1,
                    "products": [{
                        "product_id": 4, #7933,#4,
                        "product_uom_qty": 5,
                        "price": 653
                    }],
                    "partner":{
                        "patient_id": "", # "HP0001", 
                        "name": "Hicent Okonkwo",
                        "phone_contact": {
                                "dialing_code": "+234",
                                "phone_number": "07081120401",
                                "secondary_phone_number": "",
                                },
                        # "phone": "+2347067979346",  
                        "email":"davidemas@gmail.com" 
                    }
                },
                "source": "website", # healthmate
                "home_sample_collection": {
                    "city": "Abuja",
                    "street": "",
                    "phone": ""
                },
                "booking": {
                    "status": "",
                    "code": "45566",
                    "appointment_date": "12/06/2020 01:00:01",# m/d/Y H:M:S
                },
                "cif_data": [{
                    "name": "George Woman", 
                    "patient_id": "",
                    "dob": "08/12/1978",  
                    "email": "4tre@gmail.com", 
                    "address": "street Avenue",
                    "gender": "Male", # or Female 
                    "city": "Abuja",
                    "is_member": "True",
                    "flight_date": "31/5/2012",
                    "state_id": 12,
                    "phone_contact": {
                                "dialing_code": "+234",
                                "phone_number": "70679722533",
                                "secondary_phone_number": "",
                                }, 
                    "passport_number": "WEyyEURUUUU",
                    "airline": "Air peace",
                    "booking_code": "A187877", 
                    "test_location_id": 11, 
                    "destination": "China",
                    "test_type_tag": 'PCR', # ANTIGEN_ANTIBODY ANTIGEN PCR_ANTIBODY
                    "reasons_for_test": "inbound", # required -- options: non-travel, outbound, inbound  --- 
                }],
                "referring_partner": 12,
                }
        """

        data = json.loads(request.httprequest.data.decode("utf8"))
        _logger.info("API DATA %s" % json.dumps(data, indent=4))
        error_item = ["Error Found: "]

        check_validation_errors = self.validate_fields(data)
        error_item += check_validation_errors

        if len(error_item) > 1:
            _logger.info("VALIDATION ERROR %s" % error_item)
            return {"status": "failure", "message": ',\n'.join(error_item)}

        if data.get('source') == 'website' and not data.get('coupon_code'):
            verification_code = data.get('order').get(
                'payment_verification_code')
            if not self.verify_charge(verification_code):
                return {"status": "failure", "message": 'Payment verification failed!'}
        try:
            coupon_code = data.get('coupon_code', 0)
            invoice_obj = request.env['account.move'].sudo()
            account_journal = request.env['account.journal'].sudo()
            account_payment_obj = request.env['account.payment'].sudo()
            productObj = request.env['product.product'].sudo()
            Patient = request.env['oeh.medical.patient'].sudo()
            Partner = request.env['res.partner'].sudo()

            # Picks the related partner ID
            if coupon_code:
                partner = Partner.search(
                    [('coupon_code', '=', str(coupon_code))], order="id asc", limit=1)
                partner_id = partner.id if partner else False
                _logger.info("PARTNER COUPON IDS %s" % partner)
            else:
                # Double check if partner id is false
                customer_name = data.get('order')['partner']['name']
                phonecontact = data.get('order').get(
                    'partner').get('phone_contact')
                phone = phonecontact.get('phone_number') if phonecontact.get(
                    'phone_number') else phonecontact.get('secondary_phone_number')
                formted_phone = self.format_phone_field(
                    str(phonecontact.get('dialing_code')), phone)
                intl_phone = formted_phone if formted_phone.startswith(
                    "+") else f"+{formted_phone}"
                email = data.get('order').get('partner').get('email')
                partner = self.create_partner(customer_name, intl_phone, email)

            if data.get('source') == 'website':
                location_id = data.get('booking').get('location_id')
                test_location_name = data.get(
                    'booking').get('test_location_name')
                branch = self.get_branch_by_name(test_location_name)
                branch_id = location_id if location_id else branch.id if branch else False
            else:
                branch_id = int(data.get('order').get('test_location')) if data.get(
                    'order').get('test_location') else False

            # Create a sale order
            sale_order = self.create_or_get_sale_order(partner, branch_id)
            if data.get('order') and data.get('order').get('partner').get('code_promo_program_id'):
                sale_order.write({'code_promo_program_id': int(
                    data.get('order').get('partner').get('code_promo_program_id'))})
            for datas in data.get('order')['products']:
                product_id = int(datas['product_id'])
                product_uom_qty = int(datas['product_uom_qty'])
                price = int(datas['price']) if datas['price'] else productObj.browse(
                    [product_id]).list_price
                description = False
                if sale_order.client_order_ref:
                    names = ""
                    for cif in data.get('cif_data'):
                        names = names + cif.get('name') + ", "
                    today = date.today()
                    description = "{} - {}".format(names,
                                                   today.strftime("%d/%m/%y"))

                so_line_val = {
                    'product_id': product_id,
                    'order_id': sale_order.id,
                    'name': description if description else "",
                    'product_uom_qty': product_uom_qty,
                    'price_unit': price,
                }
                request.env['sale.order.line'].sudo().create(so_line_val)
            # so_reference = request.env['sale.order'].sudo().browse([sale_order])
            if coupon_code:
                """
                    Generates invoice, Post and validates it if partner has 
                    an invoicing_required field check
                """
                if partner.is_invoicing_required:
                    # Confirm sale order, create invoice and post the invoice
                    sale_order.action_confirm()
                    inv = sale_order.sudo()._create_invoices()[0]
                    inv.post()
            else:
                # Confirm sale order, create invoice and post the invoice
                sale_order.action_confirm()
                inv = sale_order.sudo()._create_invoices()[0]
                inv.post()
                # Default company payment journal for sales
                sale_payment_method = request.env['account.payment.method'].sudo().search(
                    [('code', '=', 'manual'), ('payment_type', '=', 'inbound')], limit=1)
                journal_id = self.journal_id()
                payment_method = account_journal.browse([journal_id]).inbound_payment_method_ids[0].id if account_journal.browse(
                    [journal_id]).inbound_payment_method_ids else sale_payment_method.id if sale_payment_method else 1

                acc_values = {
                    'invoice_ids': [(6, 0, [inv.id])],
                    'amount': inv.amount_residual_signed,
                    'ref': '[Payment REF: {}, SO REF: {}]'.format(data.get('order').get('payment_ref'), sale_order.name),
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'journal_id': journal_id,
                    'branch_id': branch_id,
                    'payment_method_id': payment_method,
                    'partner_id': sale_order.partner_id.id or partner_id,
                }
                payment = account_payment_obj.create(acc_values)
                payment.post()
                # payment.action_validate_invoice_payment() applicable in v14

            # create home sample collection
            hsc = False
            if data.get('home_sample_collection') is not None:
                hm_sam_val = {
                    'city': data.get('home_sample_collection').get('city'),
                    'phone': data.get('home_sample_collection').get('phone'),
                    'partner_id': partner.id,
                    'street': data.get('home_sample_collection').get('street'),
                    # 'appt_date': datetime.strptime(data.get('booking').get('appointment_date'), '%d/%m/%Y %H:%M:%S'),
                }
                hsc = request.env['oeha.homesample.collection'].sudo().create(
                    hm_sam_val)

            # create CIF records
            cifs = self.create_cif(data, branch_id, hsc, sale_order)
            # send Home sample collection email to support after CIF has been created
            if cifs and hsc:
                hsc._send_email()

            booking = data.get("booking")
            # create booking and send mail to support for each CIF
            location = booking.get("test_location_name")
            service = booking.get("service_id")
            selected_time_id = booking.get("selected_time_id")
            location_id = booking.get("location_id")
            booking_date = booking.get("selected_date")
            isAntibodySelected = booking.get("isAntibodySelected")
            for cif in cifs:
                cif.action_generate_appointment_booking(
                    location_id, service, booking_date, selected_time_id, isAntibodySelected)
                cif.has_booked = True

            # return cif records in response
            http.Response.status = "201"
            return {
                "status": "successful",
                "cif_data": [{'cif_id': c.id, 'name': c.name, 'url_token': c.url_token} for c in cifs]
            }
        except Exception as e:
            _logger.exception(e)
            return {"status": "failure", "message": str(e)}

    def verify_charge(self, verification_code):
        ''' verify payment charge '''
        _logger.info('CIF: Verifying Charge ...')
        
        payment_provider_info = get_payment_providers_details(request)
        payment_provider = payment_provider_info.get("provider")
        secret_key = payment_provider_info.get("secret_key")
        if payment_provider == 'rave':
            url = 'https://api.flutterwave.com/v3/transactions/{}/verify'.format(
                verification_code)
        else:
            url = 'https://api.paystack.co/transaction/verify/{}'.format(
                verification_code)

        headers = {'Authorization': 'Bearer {}'.format(secret_key)}
        try:
            req = requests.get(url, headers=headers, timeout=45)
            res_json = req.json()
            result = res_json.get('data')
            _logger.info('Payment Verification Result %s' % result)
            if result.get('status') == "successful" or result.get('status') == "success":
                return True
            return False
        except Exception as ex:
            _logger.exception(ex)
            return False

    def get_branch_by_name(self, test_location_name):
        """
        Args:
            **test_location_name: name of the test location provided 
        """
        branch_dict = request.env['eha.branch'].sudo().search(
            [('name', '=', test_location_name)], limit=1)
        branch = branch_dict if branch_dict else False
        return branch

    def create_cif(self, data, branch_id, hsc, sale_order):
        # appt_date = datetime.strptime(data.get('booking').get('appointment_date'), '%d/%m/%Y %H:%M:%S')
        _logger.info("CIF: Creating CIF Record ... ")

        ref_partner_id = sale_order.partner_id.id if data.get('coupon_code') else int(
            data.get('referring_partner')) if data.get('referring_partner') else False
        referring_partner = request.env['res.partner'].browse(
            [ref_partner_id]) if ref_partner_id else False
        if not referring_partner:
            # use EHA Clinics as default
            referring_partner = request.env['res.partner'].sudo().search(
                [('default_code', '=', 'EHA')], order="id asc", limit=1)

        cifModel = request.env['oeha.covid19.cif'].sudo()
        cif_ids = []
        error_list = ["Error: "]
        for rec in data.get('cif_data'):
            patient_id = self.create_patient(rec)
            booking_code = rec.get('booking_code') or data.get(
                'booking').get('code')

            vals = {
                'patient_id': patient_id,
                'name': rec.get('name'),
                'phone': self.format_phone_field(rec.get('phone_contact').get('dialing_code'), rec.get('phone_contact').get('phone_number')),
                'email': rec.get('email'),
                'street': rec.get('address'),
                'city': rec.get('city'),
                # int(rec['country_id']) if rec['country_id'] is not None else False,
                'country_id': self.get_country_id(rec.get('phone_contact').get('dialing_code')),
                'state_id': int(rec.get('state_id')) if rec.get('state_id') is not None else False,
                'dob': self.validate_format_date(rec.get('dob')),
                # str(datetime.strptime(rec.get('dob'), '%m/%d/%Y')) if self.validate_format_date(rec.get('dob')) else False,
                'gender': rec.get('gender', '').title(),
                'flight': rec.get('airline'),
                'flight_date': rec.get('flight_date', ''),
                'arrival_date': self.validate_format_date(rec.get('flight_date')),
                'destination': rec.get('destination'),
                'is_outbound_tester': True if rec.get('reasons_for_test') == "outbound" else False,
                'is_non_travel': True if rec.get('reasons_for_test') == "non-travel" else False,
                'covid_19_inbound_tester': True if rec.get('reasons_for_test') == "inbound" else False,
                # "test_type_tag": rec.get('test_type_tag'),
                # int(rec['test_location_id']) if rec['test_location_id'] is not None else False,
                "test_location": rec.get('test_location_name'),
                'test_location_id': branch_id,
                # indicates that the CIF was created from healthmate online purchase. automated action uses this flag to send cIF form email on create
                'source': data.get('source'),
                'id_card': rec.get('passport_number'),
                'id_card_country': rec.get('passport_issuing_country'),
                'simplybookme_appointment_code': booking_code,
                # 'simplybookme_appointment_date': appt_date,
                # 'appointment_date': appt_date,
                'payment_ref': data.get('order').get('payment_ref'),
                'thirdparty_partner_id': [(4, referring_partner.id)] if referring_partner else False,
                'homesample_id': hsc.id if hsc else False,
                'sale_order_id': sale_order.id,
                'payment_transaction_id': rec.get('payment_transaction_id'),
                'payment_status': rec.get('payment_status'),
                'is_appointment_simplybook': rec.get('isSimplybook'),
            }
            _logger.info(f"CIF VALS => {vals}")
            cif_id = cifModel.create(vals)
            cif_ids += [cif_id]
            # branchId = request.env['eha.branch'].sudo().browse([int(data.get('order')['test_location'])]) if data.get('order')['test_location'] else False

            # create evaluation
            eval_id = self.generate_eval(cif_id)
            # create labtest
            self.create_lab_test(eval_id, cif_id)
        return cif_ids

    def validate_format_date(self, date_str):
        """
        Rearranges date if the provided date and month is misplaced 
            :param date_str is date in format mm/dd/yy
            :return date string 'Y-m-d'

        """
        if not date_str or type(date_str) is not str:
            return False

        data = date_str.split('/')
        if len(data) > 2:
            try:
                mm, dd, yy = int(data[0]), int(data[1]), data[2]
                if mm > 12:  # eg 21/04/2021" then reformat to 04/21/2021"
                    dd, mm = mm, dd
                if mm > 12 or dd > 31 or len(yy) != 4:
                    return False
                return "{}-{}-{}".format(yy, mm, dd)
            except Exception as e:
                _logger.exception(e)
                return False

    def patient_field_validation(self, data):
        error_list = []
        for rec in data:
            reasons_for_test = rec.get('reasons_for_test')
            gender = rec.get('gender')
            email = rec.get('email')
            dob = rec.get('dob')
            name = rec.get('name')
            phone = rec.get('phone_contact').get('phone_number')
            secondary_phone_number = rec.get(
                'phone_contact').get('secondary_phone_number')

            dialing_code = rec.get('phone_contact').get('dialing_code')
            if not dialing_code:
                error_list.append(
                    "Please ensure that you provide valid dialing code")
            if not(reasons_for_test):
                error_list.append(
                    "Please ensure that you provide reason for test")
            else:
                if reasons_for_test not in ["outbound", "non-travel", "inbound"]:
                    error_list.append(
                        "Please ensure that reason for testing is in 'outbound', 'non-travel','inbound'")
            if not (gender):
                error_list.append(
                    "Please ensure that you provide patients Gender")
            else:
                if gender.title() not in ["Male", "Female"]:
                    error_list.append(
                        "Please ensure Gender value is set to Female or Male")

            if not (phone or secondary_phone_number):
                error_list.append(
                    "Please ensure that you provide Phone or secondary phone number")

            else:
                phnumber = (phone or secondary_phone_number)
                if not phnumber:
                    error_list.append(
                        "Please ensure that you provide Phone or secondary phone number")

            if not self.get_country_id(dialing_code):
                error_list.append(
                    "No Country found. Please provide a valid country dialing code")

            if not (email):
                error_list.append(
                    "Please ensure that you provide patients email")

            if not (dob):
                error_list.append(
                    "Please ensure that you provide patients DOB")

            if not (name):
                error_list.append(
                    "Please ensure that you provide patients Name")

        return error_list

    def get_country_id(self, dialing_code):

        if dialing_code:
            code = dialing_code.replace('+', '')
            dialing_code = int(code)
            country_id = request.env['res.country'].sudo().search(
                [('phone_code', '=', dialing_code)], limit=1)
            return country_id.id if country_id else False
        else:
            return False

    def format_phone_field(self, dialing_code, phone):
        if dialing_code and phone:
            try:
                if dialing_code:
                    code = dialing_code.replace('+', '')
                    dialing_code = int(code)
                    country_code = request.env['res.country'].sudo().search(
                        [('phone_code', '=', dialing_code)], limit=1)
                    if country_code:
                        return phone_validation.phone_format(phone, country_code.code, country_phone_code=None)
                    else:
                        return phone_validation.phone_format(phone, country_code=None, country_phone_code=None)
                return False
            except Exception as e:
                _logger.exception(e)
                _logger.info(
                    """Invalid Dialing Code or Phone Number provided: {}""".format(e))

    def create_patient(self, rec):
        _logger.info("CIF: Creating CIF patient ...")

        Patient = request.env['oeh.medical.patient'].sudo()
        if rec.get('patient_id'):
            patient = Patient.search(
                [('identification_code', '=', rec.get('patient_id'))])
            return patient.id

        intl_mobile, intl_phone = False, False
        phone = self.format_phone_field(rec.get('phone_contact').get(
            'dialing_code'), rec.get('phone_contact').get('phone_number'))
        mobile = self.format_phone_field(rec.get('phone_contact').get(
            'dialing_code'), rec.get('phone_contact').get('secondary_phone_number'))

        if phone:
            intl_phone = phone if phone.startswith("+") else f"+{phone}"

        if mobile:
            intl_mobile = mobile if mobile.startswith("+") else f"+{mobile}"

        st = rec.get('state_id', 0)
        state_id = int(st) if st else False
        country_id = self.get_country_id(
            rec.get('phone_contact').get('dialing_code'))
        fname, lastname2, lastname = self.format_return_name(rec.get('name'))
        vals = dict(
            firstname=fname,
            lastname2=lastname2,
            lastname=lastname,
            sex=rec.get('gender', '').title(),
            dob=self.validate_format_date(rec.get('dob')),
            email=rec.get('email'),
            phone=intl_phone,
            mobile=intl_mobile,
            street=rec.get('address'),
            city=rec.get('city'),
            state_id=state_id,
            country_id=country_id,
            passport_no=rec.get('passport_number')
        )
        _logger.info(vals)
        # check for existing record
        patient = Patient.find_patient_by_phone_dob(
            intl_phone, vals.get('dob'))
        if not patient:
            patient = Patient.create(vals)
        return patient.id

    def format_return_name(self, name):
        fname = ''
        mname = ''
        lname = ''
        if name and len(name) > 0:
            name_arr = name.split() or []
            arrlen = len(name_arr)
            fname = name_arr[0]
            if arrlen == 2:
                lname = name_arr[1]
            elif arrlen == 3:
                mname = name_arr[1]
                lname = name_arr[-1]
            else:
                lname = ', '.join(name_arr[1:])
        return fname, mname, lname

    def create_partner(self, name, phone, email, gender=False):
        _logger.info("CIF: Creating CIF partner...")

        partner = request.env['res.partner'].sudo(
        ).find_partner_by_phone_and_name(name, phone, email)

        if not partner:
            partner = request.env['res.partner'].sudo().create({
                'name': name,
                'phone': phone,
                'email': email,
                'gender': gender
            })
        return partner

    def create_or_get_sale_order(self, partner, branch_id):
        _logger.info("CIF: Retrieving of Creating Sale Order ...")
        coupon_code = partner.coupon_code
        sale_value = {
            'partner_id': partner.id,
            'payer_id': partner.id,
            'partner_invoice_id': partner.id,
            'branch_id': branch_id,
            'client_order_ref': coupon_code if coupon_code else '',
        }
        if coupon_code and not partner.is_invoicing_required:
            saleOrder = request.env['sale.order'].sudo().search(
                [('state', '=', 'draft'), ('client_order_ref', '=', coupon_code)])
            if not saleOrder:
                saleOrder = request.env['sale.order'].sudo().create(sale_value)
            return saleOrder
        return request.env['sale.order'].sudo().create(sale_value)

    def journal_id(self):
        company_id = request.env.user.company_id.id
        domain = [('type', 'in', ['bank', 'cash']),
                  ('company_id', '=', company_id)]
        journal_id = None
        bnk_journal_id = request.env['account.journal'].sudo().search(
            domain, limit=1).id
        company_journal = (request.env['account.move'].sudo().with_context(company_id=company_id or request.env.user.company_id.id)
                           .default_get(['journal_id'])['journal_id'])

        # rave = request.env['payment.provider'].sudo().search(
        #     [('code', '=', 'rave')], limit=1)
        # Changed to paystack by Olalekan, but journals should not be harcoded like this
        # TODO: rework this to be dynamic and automatically know which journal to pull
        paystack = request.env['payment.provider'].sudo().search([('code', '=', 'paystackAcquirer')], limit=1)
        if paystack:
            journal_id = paystack.journal_id.id
        elif bnk_journal_id:
            journal_id = bnk_journal_id
        else:
            journal_id = company_journal
        return journal_id

    def generate_eval(self, cif):
        _logger.info("CIF: Creating CIF evaluation ...")
        nurse = request.env.user.id  # create_uid.id
        care_provider = request.env.ref(
            'oehealth_extension.user_external_lab').id
        evaluation_type = "New Complaint"
        evaluation_template = request.env.ref(
            'oehealth_extension.oeha_template_convid_triage').id
        evaluation_start_date = fields.Datetime.now()
        eval_id = request.env['oeh.medical.evaluation'].sudo().create({
            'cif_ref': cif.id,
            'patient': cif.patient_id.id, 'care_provider': care_provider, 'nurse': nurse, 'allergies_new': "no",
            'height': 0.00, 'evaluation_type': evaluation_type, 'template_id': evaluation_template,
            'evaluation_start_date': evaluation_start_date, 'is_convid': True, 'branch_id': cif.test_location_id})

        eval_id.action_toggle_system()
        # update cif evaluation id
        cif.update({'evaluation_id': eval_id.id, 'evaluation_generated': True})
        return eval_id.id

    def get_labtest_types(self, test_type_tag):
        '''test type tags include:
                PCR, PCR_ANTIBODY, ANTIGEN, ANTIGEN_ANTIBODY
            The new test types:
                Name: Coretech COVID-19 Anti-Body RDT
                Code: COVID-19 Anti-Body RDT
                Name: COVID-19 Ag
                Code: COVID-19 Ag
        '''
        test_type_list = []
        test_types = request.env['oeh.medical.labtest.types'].sudo().search(
            [('code', 'in', ['COVID-19', 'COVID-19 Anti-Body RDT', 'COVID-19 Ag'])])
        if test_type_tag == 'PCR':
            pcr_type = test_types.filtered(lambda t: t.code == 'COVID-19')
            if not pcr_type:
                raise ValidationError(
                    _('Labtest type with code COVID-19 not yet created. Please contact sys. admin'))
            test_type_list += pcr_type

        if test_type_tag == 'PCR_ANTIBODY':
            pcr_antibody = test_types.filtered(
                lambda t: t.code in ['COVID-19', 'COVID-19 Anti-Body RDT'])
            if not pcr_antibody:
                raise ValidationError(
                    _('Labtest type with code COVID-19 OR COVID-19 Anti-Body RDT not yet created. Please contact sys. admin'))
            test_type_list += pcr_antibody

        if test_type_tag == 'ANTIGEN':
            antigen = test_types.filtered(lambda t: t.code == 'COVID-19 Ag')
            if not antigen:
                raise ValidationError(
                    _('Labtest type with code COVID-19 Ag not yet created. Please contact sys. admin'))
            test_type_list += antigen

        if test_type_tag == 'ANTIGEN_ANTIBODY':
            antigen_antibody = test_types.filtered(
                lambda t: t.code in ['COVID-19 Ag', 'COVID-19 Anti-Body RDT'])
            if not antigen_antibody:
                raise ValidationError(
                    _('Labtest type with code COVID-19 Ag OR COVID-19 Anti-Body RDT not yet created. Please contact sys. admin'))
            test_type_list += antigen_antibody
        return test_type_list

    def create_lab_test(self, eval_id, cif):
        """ Method: Used to create lab test. 
            Argument required is Patient ID and Evaluation ID
        """
        _logger.info("cif: Creating CIF Labtest ...")
        department_obj = request.env['oeh.medical.labtest.department'].sudo()
        cr_provider = request.env.ref(
            'oehealth_extension.user_external_lab').id
        department_ref = department_obj.search(
            [('name', '=ilike', 'VIROLOGY')], limit=1)
        lab_department = department_ref.id
        location = "Internal"
        labtest_ids = []
        for test_type in self.get_labtest_types(cif.test_type_tag):
            date_requested = cif.appointment_date if cif.appointment_date else fields.Datetime.now()
            # patientobj = request.env['oeh.medical.patient'].sudo().browse([patient])
            vals = {
                'cif_ref': cif.id,
                'patient': cif.patient_id.id,
                'care_provider_who_ordered_test': cr_provider,
                'lab_department': lab_department,
                'evaluation_id': eval_id,
                'location': location,
                'date_requested': date_requested,
                'branch_id': cif.test_location_id,
                'test_type': test_type.id,
                'thirdparty_partner_id': cif.thirdparty_partner_id,
                'lab_test_criteria': [(0, 0, {
                    'name': crt.name,
                    'sequence': crt.sequence,
                    'normal_range': crt.normal_range,
                    'units': crt.units
                }) for crt in request.env['oeh.medical.labtest.criteria'].sudo().search([('medical_type_id', '=', test_type.id)])]
            }
            _logger.info('LAB VALS %s ' % vals)
            labtest_id = request.env['oeh.medical.lab.test'].sudo().create(
                vals)
            labtest_ids += [labtest_id.id]

        # update CIF with the new labtest
        cif.labtest_ids = [(6, 0, labtest_ids)]
