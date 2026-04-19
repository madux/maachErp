import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode
from odoo import http, SUPERUSER_ID
import json
from odoo.http import request
import requests
# from odoo.addons.payment.controllers.portal import PaymentProcessing
_logger = logging.getLogger(__name__)


class TelehealthPayment(http.Controller):

    @http.route(['/telehealth/fees'], type='json', csrf=False, auth="public", website=True)
    def telehealth_fees(self, so_id=None, **kwargs):
        amount = 0.0
        patient = None
        partner_id = kwargs.get("telehealthPartner")
        patient_id = kwargs.get("telehealthPatient")
        amount_dict = {
            'amount': 0.0
        }
        if patient_id :
            patient = request.env['oeh.medical.patient'].sudo().search(
            [('id', '=', patient_id and int(patient_id) or False)])
        if patient and patient.plan_id:
            return amount_dict
        if not so_id:
            so_id = request.website.sale_telehealth_get_order(
                force_create=True, patient_id=patient_id, partner_id=partner_id)
            amount = so_id.amount_total if so_id else 0.0
            amount_dict.update({'amount':  amount})
        else:
            amount = so_id.amount_total if so_id else 0.0
            amount_dict.update({'amount':  amount})
        return amount_dict

    @http.route(['/telehealth/payment/transaction'], type='json', csrf=False, auth="public", website=True)
    def telehealth_payment_transaction(self, acquirer_id, save_token=False, so_id=None, access_token=None, token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        # Ensure a payment acquirer is selected
        if not acquirer_id:
            return False
        try:
            acquirer_id = int(acquirer_id)
        except:
            return False
        #
        # determines if is_service booking is true, system uses the save sale order in the session
        is_service_booking = request.session.get('is_service_booking')
        if is_service_booking:
            saved_order = request.session.get('service_sale_order_id')
            order = request.env['sale.order'].sudo().browse([saved_order])
            is_telehealth = False
        else:
            order = request.website.sale_telehealth_get_order()
            is_telehealth = True 

        # Ensure there is something to proceed
        if not order or (order and not order.order_line):
            return False
        _logger.info(f"ORDER LINE S FOUND ==> ", order)
        # Create transaction
        vals = {
            'acquirer_id': acquirer_id,
            'return_url': '/telehealth/payment/validate'
        }
        transaction = order._create_payment_transaction(vals)
        last_tx_id = request.session.get('__website_sale_last_tx_id')
        last_tx = request.env['payment.transaction'].browse(
            last_tx_id).sudo().exists()
        # if last_tx:
        #     PaymentProcessing.remove_payment_transaction(last_tx)
        # PaymentProcessing.add_payment_transaction(transaction)
        request.session['__website_sale_last_tx_id'] = transaction.id
        return transaction.render_sale_button(order, telehealth=is_telehealth)

    @http.route(route='/telehealth/payment/process', website=True, auth="public", csrf=False)
    def payment_confirmation(self, *kw):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        sale_order_id = request.session.get('sale_last_order_id')
        _logger.info(f"SALE ORDER PROCESS PAYMENT {sale_order_id}")
        if request.session.get('is_service_booking'):
            sale_order_id = request.session.get('service_sale_order_id')
            _logger.info(f"SERVICE SALE ORDER PROCESS PAYMENT {sale_order_id}")
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            if request.session.get('is_service_booking'):
                self.create_simplybook_service_appointment()
                return request.redirect("/service-final")
            else:
                return request.render("eha_telehealth.telehealth_final", {'order': order})
        else:
            return request.redirect('/telehalth-1')

    @http.route('/telehealth/payment/validate', type='http', auth="public", website=True, sitemap=False)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        if sale_order_id is None:
            is_service_booking = request.session.get('is_service_booking')
            if is_service_booking:
                saved_order = request.session.get('service_sale_order_id')
                order = request.env['sale.order'].sudo().browse([saved_order])
            else:
                order = request.website.sale_telehealth_get_order()
        else:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            # assert order.id == request.session.get('sale_telehealth_order_id')

        if transaction_id:
            tx = request.env['payment.transaction'].sudo().browse(
                transaction_id)
            assert tx in order.transaction_ids()
        elif order:
            tx = order.get_portal_last_transaction()
        else:
            tx = None
            
        # PaymentProcessing.remove_payment_transaction(tx)
        return request.redirect(f'/telehealth/confirmation')
    
    @http.route('/telehealth/confirmation', type="http", auth='public', website="True")
    def telehealth_confirmation(self):
        """Create a booking, create patient and redirect to this page after successful payment, else return an error page
        """
        sale_order_id = request.session.get('service_sale_order_id')
        _logger.info(f" {sale_order_id} SALES CONFIRMED")
        is_service_booking = request.session.get('is_service_booking')
        if is_service_booking:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
        else:
            order = request.website.sale_telehealth_get_order()
        transaction = order.get_portal_last_transaction()
        if transaction and transaction.state == 'done':
            # create a patient if partner does not have a linked patient record
            partner_id = order.partner_id.id or request.session['partner_id']
            if partner_id and partner_id != "null":
                try:
                    partner = request.env['res.partner'].browse(int(partner_id))
                except Exception as e:
                    _logger.error("{}".format(e))
                else:
                    if partner:
                        linked_patient = request.env['oeh.medical.patient'].sudo().search([('partner_id', '=', partner.id)])
                        if not linked_patient:
                            try:
                                partner.with_user(SUPERUSER_ID).convert_to_patient()
                            except:
                                _logger.error(f"Error converting telehealth partner, {partner.firstname} {partner.lastname}, to patient")
            if is_service_booking:
                self.create_simplybook_service_appointment()
                return request.redirect("/service-final")
            else:
                booking = self.register_booking()
                context = {
                    "booking_id": booking.id
                }
                query_params = urlencode(context)
                # return request.redirect(f'/telehealth-final/?{query_params}')
                return request.redirect(f'/telehealth-final/{booking.id}')
        else:
            return "Payment cannot be confirmed" # Redirect to failure page
        

    @http.route(["/telehealth/register_booking"], type="json", auth="public", website=True)
    def member_booking(self, **kwargs):
        self.check_if_insurance_selected(kwargs)
        booking = self.register_booking()
        context = {
            "booking_id": booking.id,
        }
        query_params = urlencode(context)
        # return request.redirect(f'/telehealth-final/?{query_params}')
        return request.redirect(f'/telehealth-final/{booking.id}')

    @http.route(['/telehealth/register'], auth="public", type="json")
    def create_booking_method(self, *args, **kwargs):
        self.check_if_insurance_selected(kwargs)
        booking = self.register_booking()
        context = {
            "booking_id": booking.id,
        }
        # query_params = urlencode(context)
        return booking.id # query_params

    @http.route(['/service/register/booking'], auth="public", type="json")
    def service_register(self, *args, **kwargs):
        self.check_if_insurance_selected(kwargs)
        _logger.info(kwargs)
        self.create_simplybook_service_appointment()
         
    def check_if_insurance_selected(self, kwargs):
         
        _logger.info(f"kwargs is === {kwargs}")

        params = kwargs.get('params')
        _logger.info(f"Params === {params}")
        is_service_booking = params.get('is_service_booking')
        if is_service_booking:
            so_order_id = request.session.get("service_sale_order_id")
        else:
            so_order_id = request.session.get("sale_telehealth_order_id")
        is_insurance = params.get('insurance_checkbox')
        insurance_code = params.get('insurance_code')
        insurance_name = params.get('insurance_name')
        _logger.info(f"Insurance select: {is_insurance} , Insurance name and code is {insurance_name} - {insurance_code} with SO ID {so_order_id}")
        if params.get('insurance_name') and params.get('insurance_code') and so_order_id:
            _logger.info(f"Insurance is selected and ready to update")
            so_id = request.env['sale.order'].sudo().browse([int(so_order_id)])
            so_id.send_mail_to_command_center()
            so_id.write({
                'is_insurance': True,
                'insurance_code': insurance_code,
                'insurance_name': int(insurance_name),
            })

    def register_booking(self):
        partner_id = request.session.get("partner_id") #
        note_for_doctor = request.session.get("note_for_doctor")
        alarm_ids = request.env['calendar.alarm'].sudo().search(
            [('alarm_type', '=', 'email')])
        odoo_telehealth_service_id = request.env['ir.config_parameter'].sudo(
        ).get_param("eha_telehealth.telehealth_service_id")
        odoo_telehealth_location_id = request.env['ir.config_parameter'].sudo(
        ).get_param("eha_telehealth.telehealth_location_id")
        odoo_service_id = request.env['eha.booking.services'].sudo().search(
            [('id', '=', int(odoo_telehealth_service_id))])
        odoo_service_provider_id = odoo_service_id.service_providers[
            0] if odoo_service_id and odoo_service_id.service_providers else False
        booking_date_str = request.session.get(
            "telehealth_simplybook_date")  # 07/30/2022
        telehealth_simplybook_time = request.session.get(
            "telehealth_simplybook_time")  # 07:10
        
        time_str = f"{telehealth_simplybook_time}:00"
        date_list = booking_date_str.split("/")
        month = date_list[0]
        day = date_list[1]
        year = date_list[2]
        date_str = f"{month}/{day}/{year}"
        date_time_str = f"{date_str} {time_str}"
        start_datetime = datetime.strptime(date_time_str, '%m/%d/%Y %H:%M:%S')
        wk = start_datetime.weekday()
        slot_weekday = odoo_service_id.mapped(
            'slot_ids').filtered(lambda s: s.weekday == str(wk))
         
        slot_id = None
        duration = 0
        # hr_stop_time = None
        # min_stop_time = None
        stop_time = None
        if slot_weekday:
            appointment_slot_id = slot_weekday[0]
            duration = appointment_slot_id and appointment_slot_id.appointment_duration
            slot_id = appointment_slot_id.mapped('time_slot_ids').filtered(
                lambda s: s.name == time_str)  # eg . 07:30:00

            # Need to find out from Chris why this was written this way
            # if time_slot_id:
            #     slot_id = time_slot_id[0]
            #     duration = 60 if appointment_slot_id.time_stamp_type == 'min' else appointment_slot_id.appointment_duration
            # hr_stop_time = start_datetime + timedelta(hours=duration)
            # min_stop_time = start_datetime + timedelta(minutes=duration)
            # stop_time = min_stop_time if appointment_slot_id.time_stamp_type == 'min' else hr_stop_time
            time_diff = timedelta(minutes=duration) if appointment_slot_id.time_stamp_type == 'min' else timedelta(hours=duration)
            stop_time = start_datetime + time_diff
        _logger.info(f"""Here is the whole attifacts ==> config_telehealth : {odoo_telehealth_location_id}, Provider: {odoo_service_provider_id}, fetched services == {odoo_service_id.id},
        START DATE {start_datetime} ,SLOT {slot_id.name} TIMES {time_str} , WEEKDAY {wk}, WEEKDAY SLOTSSS => {[re.weekday for re in slot_weekday]}""")
        booking = request.env['calendar.event'].sudo().create({
            'eha_service_location_id': int(odoo_telehealth_location_id),
            'service_id': odoo_telehealth_service_id,
            'service_provider_id': odoo_service_provider_id.id,
            'strt_slot_time': slot_id.id if slot_id else False,
            'strt_slot_time_text': slot_id.name if slot_id else False,
            'booking_start_date': start_datetime.date(),
            'partner_ids': [(4, partner_id), (4, odoo_service_provider_id.partner_id.id)],
            'start': start_datetime.date(),
            'duration': duration,
            'start_datetime': start_datetime,
            'is_online_booking': True,
            'stop': stop_time,
            'stop_datetime': stop_time,
            'alarm_ids': [(6, 0, alarm_ids.ids)],
            'user_id': int(request.env.ref('base.user_admin')),
            'description': note_for_doctor,
        })
        _logger.info(f'''Odoo Booking ID {booking}''')
        # creating slot to simplybook
        self.schedule_simplybook_appointment()
        GoogleCal = request.env['google.calendar'].sudo()
        admin = request.env.ref('base.user_admin')
        try:
            meeting_link = ''
            _, response, _ = GoogleCal.with_user(
                admin).create_an_event(booking)
            event_id = response.get('id', None)
            content = GoogleCal.with_user(
                admin).get_one_event_synchro(event_id)
            meeting_link = content.get("hangoutLink")
            if meeting_link:
                booking.sudo().write({
                    'telehealth_google_meet_link': meeting_link
                })
                # trigger sending of email to attendees
                booking.sudo().action_mail_telehealth_attendees()
                _logger.error("Google meet link generated")

        except Exception as e:
            _logger.error("Google meet link not generated %s" % (e))

        request.session["telehealth_location_id"] = ""
        request.session["telehealth_service_id"] = ""
        request.session["telehealth_time_slot_id"] = ""
        request.session["telehealth_booking_date"] = ""
        request.session["note_for_doctor"] = ""
        return booking

    def simplybookmeToken(self, params, simplybookme_url):
        # api = "https://user-api-v2.simplybook.me/admin/auth"
        api = "%s/admin/auth" %simplybookme_url
        _logger.info(f"FIRST URL == {api}")
        parameter = {
            'company': params.get('company'),
            'login': params.get('login'),
            'password': params.get('password'), 
        }
        headers = {
            "Content-Type": "application/json"
        }
        data = json.dumps(parameter)
        data = str(data).encode('utf-8')
        req = requests.post(api, data=data, headers=headers)
        res = json.loads(req.text)
        TOKEN = res.get('token')
        print(req.text)
        return TOKEN

    def create_simplybookme_client(self, headers, clientdata, simplybookme_url):
        # token = '618c66950bc37d607e31ca850af38bc235301e6cc97f885d9958a7e541114e29'
        clientData = {
            'name': clientdata.get('name'),
            'email': clientdata.get('email'),
            'phone': clientdata.get('phone'),
            'patient_id': clientdata.get('patient_id'),
        }
        email = clientData.get('email')
        # check if there is an existing simplybook client for the cif patient
        search = email
        # url = 'https://user-api-v2.simplybook.me/admin/clients?page=1&on_page=10&filter[search]=%s' % search
        url = '%s/admin/clients?page=1&on_page=10&filter[search]=%s' % (simplybookme_url, search)
        _logger.info(f"SECOND URL =={url}")

        req = requests.get(url, headers=headers)
        _logger.info(req)
        clients = json.loads(req.text)
        client_id = None
        for client in clients.get('data', []):
            if client.get('address2') == clientData.get('patient_id'):
                client_id = client.get('id')
                break
        # if no simplybook client exists for cif patient, create a new one
        if client_id is None:
            data = json.dumps({
                "name": clientdata.get('name'),
                'email': clientdata.get('email'),
                'phone': clientdata.get('phone'),
                "address2": clientdata.get('patient_id'),
            })
            # url = 'https://user-api-v2.simplybook.me/admin/clients'
            url = '%s/admin/clients' % simplybookme_url
            _logger.info(f"SECOND URL =={url}")
            req = requests.post(url, data=data, headers=headers)
            client = json.loads(req.text)
            client_id = client.get('id')
        _logger.info('CLIENT ID CREATED %s' % (client))
        return client_id

    def schedule_simplybook_appointment(self):
        param_obj = request.env['ir.config_parameter'].sudo()
        simplybookme_url = request.env['ir.config_parameter'].sudo().get_param('simplybookme_rest_url', False)
        companyLogin = param_obj.sudo().get_param('simplybookme_companylogin', '')
        admin_login = param_obj.sudo().get_param('simplybookme_admin_login', '')
        admin_password = param_obj.sudo().get_param('simplybookme_admin_password', '')
        location_id = request.session.get("telehealth_simplybook_location_id")
        provider_id = request.session.get("telehealth_simplybook_performer_id")
        service_id = request.session.get("telehealth_simplybook_service_id")
        token_params = {
            'company': companyLogin,
            'login': admin_login,
            'password': admin_password,
        }
        _logger.info(f"SIMPLY BOOK URL == {simplybookme_url}")
        token = self.simplybookmeToken(token_params, simplybookme_url)
        _logger.info('TOKEN IS HERE =====> %s' % (token))
        headers = {
            "Content-Type": "application/json",
            "X-Company-Login": companyLogin,
            "X-Token": token
        }
        clientData = request.session.get("telehealth_simplybook_clientData")
        Clientname = clientData.get('name')
        Clientemail = clientData.get('email')
        Clientphone = clientData.get('phone')
        ClientpatientId = clientData.get('patientId')
        date_appt = request.session.get("telehealth_simplybook_date")
        starttime = request.session.get("telehealth_simplybook_time")
        date_list = date_appt.split("/")
        month = date_list[0]
        day = date_list[1]
        year = date_list[2]
        date_str = f"{year}-{month}-{day}"
        book_date = f"{date_str} {starttime}:00"
        clientData = {
            'name': Clientname,
            'email': Clientemail,
            'phone': Clientphone,
            'patient_id': ClientpatientId,
        }
        client_id = self.create_simplybookme_client(headers, clientData, simplybookme_url)
        if token is not None:
            # url = "https://user-api-v2.simplybook.me/admin/bookings"
            url = "%s/admin/bookings" %simplybookme_url
            _logger.info(f"SECOND URL =={url}")
            _logger.info('CLIENT ID %s' % client_id)
            data = {
                "count": 1,
                "start_datetime": book_date,
                "location_id": location_id,
                "provider_id": provider_id,
                "service_id": service_id,
                "client_id": client_id,
            }
            _logger.info('booking data ID %s' % data)
            try:
                dt = json.dumps(data)
                req = requests.post(url, data=dt, headers=headers)
                booking = req.json()
                _logger.info('BOOKING RESP %s' % booking)
                return booking
            except Exception as ex:
                _logger.info(
                    'Could not schedule simplybook.pro appointment: {}'.format(ex.args[0]))

    def create_simplybook_service_appointment(self):
        param_obj = request.env['ir.config_parameter'].sudo()
        simplybookme_url = request.env['ir.config_parameter'].sudo().get_param('simplybookme_rest_url', False)
        companyLogin = param_obj.sudo().get_param('simplybookme_companylogin', '')
        admin_login = param_obj.sudo().get_param('simplybookme_admin_login', '')
        admin_password = param_obj.sudo().get_param('simplybookme_admin_password', '')
        location_id = request.session.get("serviceLocationID")
        provider_id = request.session.get("serviceProviderID")
        service_id = request.session.get("serviceID")
        token_params = {
            'company': companyLogin,
            'login': admin_login,
            'password': admin_password,
        }
        _logger.info(f"ALL SENT DATA =====> {location_id} {provider_id} {service_id}")
        serviceDate = request.session.get("serviceDate")
        serviceTime = request.session.get("serviceTime")
        token = self.simplybookmeToken(token_params, simplybookme_url)
        _logger.info('Service TOKEN IS HERE =====> %s' % (token))
        _logger.info('Service Date IS HERE =====> %s' % (serviceDate))
        _logger.info('Service time IS HERE =====> %s' % (serviceTime))
        headers = {
            "Content-Type": "application/json",
            "X-Company-Login": companyLogin,
            "X-Token": token
        }
        clientData = request.session.get("serviceClientData")
        Clientname = clientData.get('name')
        Clientemail = clientData.get('email')
        Clientphone = clientData.get('phone')
        ClientpatientId = clientData.get('patientId')
        serviceDate = request.session.get("serviceDate")
        serviceTime = request.session.get("serviceTime")
        date_list = serviceDate.split("/") # the date time must be in these format Y-m-d H:m:s
        day = date_list[0]
        month = date_list[1]
        year = date_list[2]
        date_str = f"{year}-{month}-{day}"
        book_date = f"{date_str} {serviceTime}:00"
        clientData = {
            'name': Clientname,
            'email': Clientemail,
            'phone': Clientphone,
            'patient_id': ClientpatientId,
        }
        client_id = self.create_simplybookme_client(headers, clientData, simplybookme_url)
        if token is not None:
            # url = "https://user-api-v2.simplybook.me/admin/bookings"
            url = "%s/admin/bookings" %simplybookme_url
            _logger.info(f"SECOND URL =={url}")
            _logger.info('CLIENT ID %s' % client_id)
            data = {
                "count": 1,
                "start_datetime": book_date, # the date time must be in these format Y-m-d H:m:s
                "location_id": location_id,
                "provider_id": provider_id,
                "service_id": service_id,
                "client_id": client_id,
            }
            _logger.info('booking data ID %s' % data)
            try:
                dt = json.dumps(data)
                req = requests.post(url, data=dt, headers=headers)
                booking = req.json()
                _logger.info('Service BOOKING RESP %s' % booking)
                request.session["book_date"] = book_date
                request.session["Clientname"] = Clientname
                context = {
                        'book_date': book_date,
                        'Clientname': Clientname,
                        'return_url': '/service-final'
                    }
            
                # return context

            except Exception as ex:
                _logger.info(
                    'Could not schedule simplybook.pro appointment: {}'.format(ex.args[0]))

 