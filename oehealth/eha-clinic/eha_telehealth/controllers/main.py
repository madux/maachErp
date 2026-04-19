# -*- coding: utf-8 -*-
from multiprocessing.connection import Client
from odoo import http
from odoo.http import request
from odoo.osv import expression
from datetime import datetime
import logging
import json
_logger = logging.getLogger(__name__)

def get_telehealth_data():
    # domain = expression.AND([
    #     [('state', 'in', ['enabled', 'test'])],
    #     ['|', ('website_id', '=', False),
    #      ('website_id', '=', request.website.id)],
    #     [('country_ids', '=', False)]
    # ])
    payment_acquirers = request.env['payment.provider'].search([])
    telehealth_booking_service_id = request.env['ir.config_parameter'].sudo(
    ).get_param("eha_telehealth.telehealth_service_id")
    booking_service_id = request.env['eha.booking.services'].sudo().browse(
        int(telehealth_booking_service_id))
    state_ids = request.env['res.country.state'].sudo().search(
        [('country_id.name', '=', 'Nigeria')]
    )
    insurance_company_ids = request.env['eha.insurance.organisation'].sudo().search([])
    telehealth_location_id = request.env['ir.config_parameter'].sudo(
    ).get_param("eha_telehealth.telehealth_location_id")
    location_id = request.env['eha.branch'].sudo().browse(
        int(telehealth_location_id))
    return payment_acquirers, booking_service_id, location_id, state_ids, insurance_company_ids


class EhaTelehealth(http.Controller):

    @http.route('/simplybookme/params', type='json',
                website=True, auth="public", csrf=False)
    def booking_param_data(self):
        param_obj = http.request.env['ir.config_parameter']
        data_item = []
        company_name = param_obj.sudo().get_param(
            'simplybookme_companyname', False)
        company_login = param_obj.sudo().get_param(
            'simplybookme_companylogin', False)
        admin_password = param_obj.sudo().get_param(
            'simplybookme_admin_password', False)
        api_key = param_obj.sudo().get_param(
            'simplybookme_apikey', False)
        simplybookme_url = param_obj.sudo().get_param(
            'simplybookme_url', False)
        admin_login = param_obj.sudo().get_param(
            'simplybookme_admin_login', False)
        # Telehealth
        telehealth_location_id = param_obj.sudo().get_param(
            'simplybookme_telehealth_location_id', False)
        telehealth_service_id = param_obj.sudo().get_param(
            'simplybookme_telehealth_service_id', False)
        telehealth_performer_id = param_obj.sudo().get_param(
            'simplybookme_telehealth_performer_id', False)
        return {
            'name': company_name,
            'company_login': company_login,
            'admin_login': admin_login,
            'admin_password': admin_password,
            'api_key': api_key,
            'url': simplybookme_url,
            'telehealth_location_id': telehealth_location_id,
            'telehealth_service_id': telehealth_service_id,
            'telehealth_performer_id': telehealth_performer_id,
        }
        
    @http.route('/telehealth', auth='public', website=True, type="http")
    def telehealth(self, **kw):
        payment_acquirers, booking_service_id, location_id, state_ids, insurance_ids = get_telehealth_data()
        _logger.info(','.join([rec.name for rec in state_ids]))
        context = {
            "payment_acquirers": payment_acquirers,
            "booking_service": booking_service_id,
            "location": location_id,
            "state_ids": state_ids,
            "insurance_ids": insurance_ids,
        }
        return request.render("eha_telehealth.telehealth", qcontext=context)

    @http.route('/telehealth-final/<booking_id>', auth='public', website=True, type="http")
    def telehealth_final(self, booking_id, **kw):
        booking_id = int(booking_id) if booking_id else None
        booking = request.env['calendar.event'].sudo().search(
            [("id", '=', booking_id)], limit=1)
         
        booking_date_str = request.session.get("telehealth_simplybook_date") # 07/30/2022
        telehealth_simplybook_time = request.session.get("telehealth_simplybook_time")
        return request.render("eha_telehealth.telehealth_final", {
            "booking": booking, 
            "date": booking_date_str, "time": telehealth_simplybook_time
            })
    
    def clearAllSessions(self):
        # here to clear all sessions
        request.session.clear()

    @http.route('/service-final', 
    auth='public', 
    website=True, 
    type="http",
    csrf=False)
    def service_final(self, **kw):
        book_date, Clientname =False, False 
        book_date = request.session.get("book_date")
        Clientname = request.session.get("Clientname")
        # request.session.clear()
        request.session['service_sale_order_id'] = False
        return request.render("eha_telehealth.service_final", {
            "book_date": book_date, 
            "Clientname": Clientname
            })

    @http.route('/telehealth/booking_details', auth='public', website=True, type="json")
    def booking_details(self, **kw):
        _logger.info(kw.get('params'))
        telehealth_location_id = kw.get('params').get('location_id')
        telehealth_service_id = kw.get("params").get('service_id')
        telehealth_time_slot_id = kw.get("params").get("slot_id")
        telehealth_booking_date = kw.get("params").get("booking_date")
        telehealth_simplybook_location_id = kw.get("params").get("simplybook_location_id")
        telehealth_simplybook_performer_id = kw.get("params").get("simplybook_performer_id")
        telehealth_simplybook_service_id = kw.get("params").get("simplybook_service_id")
        telehealth_simplybook_date = kw.get("params").get("simplybook_date")
        telehealth_simplybook_time = kw.get("params").get("simplybook_time")
        clientData = kw.get("params").get("clientData")

        request.session["telehealth_simplybook_location_id"] = telehealth_simplybook_location_id
        request.session["telehealth_simplybook_performer_id"] = telehealth_simplybook_performer_id
        request.session["telehealth_simplybook_service_id"] = telehealth_simplybook_service_id
        request.session["telehealth_simplybook_date"] = telehealth_simplybook_date
        request.session["telehealth_simplybook_time"] = telehealth_simplybook_time
        request.session["telehealth_simplybook_clientData"] = clientData

        telehealth_note_for_doctor = kw.get("params").get("note_for_doctor")
        request.session["telehealth_location_id"] = telehealth_location_id
        request.session["telehealth_service_id"] = telehealth_service_id
        request.session["telehealth_time_slot_id"] = telehealth_time_slot_id
        request.session["telehealth_booking_date"] = telehealth_booking_date
        request.session["note_for_doctor"] = telehealth_note_for_doctor
         
        return {
            "msg": "Success",
            "booking_date": telehealth_simplybook_date,
            "booking_time": telehealth_simplybook_time,
        }
    
    @http.route(['/telehealth/get-care-properties'], auth="public", type="json")
    def get_care_props(self, *args, **kwargs):
        state_ids = request.env['res.country.state'].sudo().search(
            [('country_id.name', '=', 'Nigeria')]
        )
        insurance_company_ids = request.env['eha.insurance.organisation'].sudo().search([])
        ins_data = []
        for ins in insurance_company_ids:
            ins_data.append({
                'id': ins.id,
                'name': ins.name,
            })
        
        state_data = []
        for state in state_ids:
            state_data.append({
                'id': state.id,
                'name': state.name,
            })

        context = {
            "state_data": state_data,
            "insurance_data": ins_data,
        }
        return context

    @http.route(['/telehealth/patients'], auth="public", type="json")
    def patient_create(self, *args, **kwargs):
        """Check if patient exists, create if not.
        """
        Patient = request.env['oeh.medical.patient'].sudo()
        if not kwargs or not kwargs.get("params"):
            return None
        patient_details = kwargs.get("params")
        firstname = patient_details.get("first_name")
        secondname = patient_details.get("middle_name")
        lastname = patient_details.get("last_name")
        email = patient_details.get("email")
        dob = patient_details.get("dob")
        dob_list = dob.split("/")
        dob_list.reverse()
        formatted_dob = "-".join(dob_list)
        sex = patient_details.get("gender")
        phone = patient_details.get("phone")
        state_id = patient_details.get("state_id")
        patient = None
        state = None
        partner_id = None
        if patient_details.get("patient_id"):
            patient = Patient.search(
                [('identification_code', '=', patient_details.get("patient_id"))])
        if not patient:
            patient = Patient.find_patient_by_phone_dob(phone, formatted_dob)
        if state_id:
            state = request.env['res.country.state'].sudo().search(
                [('id', '=', int(state_id or False))]
            )
        _logger.info(f'STATE IS====> {state} AND {patient_details.get("state_id")}')
        country_id = request.env['res.country'].sudo().search(
            ['|',('name', '=', 'Nigeria'), ('id', '=', 163)]
        )
        patient_vals = {
            'firstname': firstname,
            'lastname2': secondname,
            'lastname': lastname,
            'email': email,
            'sex': sex,
            'dob': formatted_dob,
            'phone': phone,
            'state_id': state.id if state else int(state_id) if state_id else False,
            'country_id': country_id.id
        }

        patient_id = patient and patient.id or None
        if patient_id:
            partner_id = patient.partner_id and patient.partner_id.id
        request.session['patient_id'] = patient_id
        request.session['partner_id'] = partner_id
        # if patient is not found, save the stringified values to session
        request.session['partner_vals'] = json.dumps(patient_vals)
        return {
            "partner_id": partner_id,
            "patient_id": patient_id
        }


    def get_service_pricelist(self, service_id):
        """Gets the service(product) respective pricelists for display""" 
        pricelists = service_id.mapped('product_pricelist_ids')
        price_items = []
        for item in pricelists:
            ppl = item.mapped('item_ids').filtered(
                lambda ppr: ppr.product_tmpl_id.id == service_id.product_id.id or ppr.product_tmpl_id.name == service_id.product_id.name
            )
            if ppl:
                # Configured Pricelist may look like this: 'Abuja- Public Pricelist'
                # so am getting the first index word
                # first_ppl_name = ppl[0].pricelist_id.name.split(' ')
                # ppl_name = first_ppl_name[0] if first_ppl_name else "*"
                ppl_name = ppl[0].pricelist_id.name
                """Because there might multiple product in the item line, use only one"""
                price_items.append({'name': ppl_name,'amount': ppl[0].fixed_price})
        return price_items

    @http.route('/book-service', auth='public', website=True, type="http")
    def book_service(self, **kw):
        """
        This route ensures services are displayed on the /book-service page
        To setup: Kindly go to sales ==> configuration ==> category and add
        the services.
        On each service, select a product to map to it, add related product
        prices list that matches the select product and then the system will
        pick the product price list item and prepares a dictionary to display
        the prices for user
        """
        eha_categories = request.env['eha_service.category'].sudo().search([])
        payment_acquirers, booking_service_id, location_id, state_ids, insurance_ids = get_telehealth_data()
        categories = []
        for rec in eha_categories:
            service_ids = rec.mapped('service_ids').filtered(
                lambda s: s.display_on_website
            ) 
            if service_ids:
                category_dict = {
                    'category_id': rec.id,
                    'category_obj': rec,
                    'name': rec.name,
                    # 'image': rec.image,
                    'first_service_index':{
                        'id': service_ids[0].id, 
                        'name': service_ids[0].name, 
                        'image': service_ids[0].image or "", 
                        'prices': self.get_service_pricelist(service_ids[0]),
                        'description': service_ids[0].description,
                        'is_member_free': service_ids[0].is_member_free,
                        'service_id': str(service_ids[0].id),
                    },
                    'other_services': [
                        {
                            'id': serv.id, 
                            'name': serv.name, 
                            'image': serv.image or "", 
                            'prices': self.get_service_pricelist(serv),
                            'description': serv.description,
                            'is_member_free': serv.is_member_free,
                            'service_id': str(serv.id),
                        } for serv in service_ids[1:] # starting from the next index after 0
                    ]
                }
                categories.append(category_dict)
        context = {
            "service_categories": categories,
            "payment_acquirers": payment_acquirers,
            "insurance_ids": insurance_ids,
        }
        _logger.info(f"{categories}, == > {context.get('service_categories')}")
        return request.render("eha_telehealth.book_a_service", qcontext=context)

    @http.route(['/get/service-location'], auth="public", type="json")
    def get_service_location(self, service_id):
        service = request.env['eha_service.service'].sudo().search(
            [('id', '=', service_id)], limit=1)
        registration_product = request.env['product.product'].sudo().search(
            [('default_code', '=', 'Website-Registration')], limit=1)
        data_props = self.get_care_props()
        registration_price = registration_product.list_price or 0.0
        location_ids = []
        provider_ids = []
        service_prices = self.get_service_pricelist(service)
        appointment_service_id = service.appointment_service_id
        price = service.product_id.list_price # to get the public price set for this service
        selected_br = []
        for pricelist in service.mapped('product_pricelist_ids'):
            branches = pricelist.mapped('branch_ids').filtered(lambda s: s.simplybook_location_id != False)
            for br in branches:
                if br.id not in selected_br:
                    location_ids.append({
                        'id': br.id,
                        'simplybook_location_id': br.simplybook_location_id,
                        'name': br.name or "",
                        'code': br.code or "",
                        'street': br.street or br.street2 or "",
                    })
                    selected_br.append(br.id)
        for provider in service.sudo().mapped('appointment_provider_ids'):
            provider_ids.append({
                'phone': provider.phone or "",
                'name': provider.name or "",
                'image': provider.image_1920 or "",
                'id': str(provider.id),
                'simplybook_performer_id': provider.simplybook_performer_id,
            })
        if location_ids and provider_ids:
            res = {
                'status': True,
                'location_ids': location_ids,
                'provider_ids': provider_ids,
                'price': price,
                'registration_price': registration_price,
                'appointment_service_id': appointment_service_id,
                'service_prices': service_prices,
                'service_name': service.name,
                'insurance_ids': data_props.get('insurance_data'), # this will pull the insurances and state
                'message': "Success",
            }
        else:
            res = {
                'status': False,
                'location_ids': False,
                'message': "No location Exist: Ensure that the service has pricelist location setup",
            }
        return res

    @http.route(['/get/location-price'], auth="public", type="json")
    def get_service_location_price(self, service_id, location_code):
        """Returns the selected location price"""
        _logger.info(f"Omila {service_id} and {location_code}")
        price = self.get_service_public_price(service_id, location_code, False)
        _logger.info(f"Price for location returned {price}")
        return {
            'location_price': price 
        }

    def get_service_public_price(self, serviceid, location_code, property_product_pricelist=False):
        service_id = request.env['eha_service.service'].sudo().search(
            [('appointment_service_id', '=', serviceid)], limit=1)
        price_items = service_id.product_id.list_price
        patient_price = False 
        if service_id:
            if property_product_pricelist:
                patient_price = property_product_pricelist.mapped('item_ids').filtered(
                        lambda ppr: ppr.product_tmpl_id.id == service_id.product_id.id or ppr.product_tmpl_id.name == service_id.product_id.name
                    )
            if patient_price:
                """Because there might multiple product in the item line, use only one"""
                price_items = patient_price[0].fixed_price
            else:
                '''checks the service pricelists and get where select branch code is
                equal to the selected branch and assign the pricelist o that branch'''
                public_price_lists = service_id.mapped('product_pricelist_ids').filtered(
                    lambda pub: location_code in [branch.code for branch in pub.branch_ids]
                )
                _logger.info(f'OMO NOOOO {location_code} cododo {public_price_lists}')
                if public_price_lists:
                    _logger.info(f'WE OMO NOOOO {location_code} cododo {public_price_lists}')

                    for item in public_price_lists:
                        """Loops because of multiple files"""
                        ppl = item.mapped('item_ids').filtered(
                            lambda ppr: ppr.product_tmpl_id.id == service_id.product_id.id or ppr.product_tmpl_id.name == service_id.product_id.name
                        )
                        if ppl:
                            _logger.info(f'GOT TA {ppl[0].fixed_price}')
                            """Because there might multiple product in the item line, use only one"""
                            price_items = ppl[0].fixed_price
        return price_items
    
    @http.route(['/get/existing-patient'], auth="public", type="json")
    def get_related_patient(self, **kwargs):
        Patient = request.env['oeh.medical.patient'].sudo()
        if not kwargs or not kwargs.get("params"):
            return None
        patient_details = kwargs.get("params")
        serviceid = patient_details.get("serviceid")
        location_code = patient_details.get("location_code")
        hp_number = patient_details.get("hp_number")
        dob = patient_details.get("existing_dob")
        dob_list = dob.split("/")
        dob_list.reverse()
        formatted_dob = "-".join(dob_list)
        phone = patient_details.get("existing_phone")
        patient = None
        patient_price_list = False
        price = 0
        if patient_details.get("hp_number"):
            patient = Patient.search(
                [('identification_code', '=', patient_details.get("hp_number"))])
        if not patient:
            if phone and formatted_dob:
                patient = Patient.find_patient_by_phone_dob(phone, formatted_dob)
                _logger.info(f"************** patient ************** {patient}")
        if patient:
            patient_price_list = patient.property_product_pricelist
            price = self.get_service_public_price(serviceid, location_code, patient_price_list)
            res = {
                'status': True,
                'firstname': patient.firstname,
                'middlename': patient.lastname2,
                'lastname': patient.lastname,
                'email': patient.email,
                'gender': patient.sex,
                'dob': patient.dob,
                'phone': patient.phone or patient.mobile,
                'price': price,
                'message': "Success",
            }
        else:
            res = {
                'status': False,
                'message': "Not found: No existing patient found",
            }
        _logger.info(f"Existing patient found {res}")
        return res

    @http.route(['/generate/service-saleorder'], auth="public", type="json")
    def generate_service_sale_order(self, *args, **kwargs):
        """sends dict obj of info to create SO and patient if not exists
        Assigns the partnerid, Saleorder to session storage to be used
        by /payment/process 
        service_storage = {
                        'serviceid': res.appointment_service_id,
                        'service_name': res.service_name,
                        'price': res.price,
                        'location_prices': res.price,
                        'is_registration': true,
                        'registration_price': res.registration_price,
                        'serviceDate': 07/10/2010
                        'serviceTime': 01:00:00
                    }
                
            patient_data = {
                'first_name': $('#existing_firstname').val(),
                'lastname': $('#existing_lastname').val(),
                'middle_name': $('#existing_middlename').val(),
                'gender': $('#gender').val(),
                'patientid': $('#existing_patientID').val(),
                'phone': $('#existing_phone').val(),
                'dob': $('#existing_dob').val(),
                'email': $('#new_email').val(),
            } or

            patient_data = {
                'first_name': $('#firstname').val(),
                'lastname': $('#firstname').val(),
                'middle_name': $('#middlename').val(),
                'email': $('#new_email').val(),
                'gender': $('#gender').val(),
                'patientid': $('#patientID').val(),
                'phone': $('#new_phone').val(),
                'dob': $('#dob').val(),
            }
        """
        Patient = request.env['oeh.medical.patient'].sudo()
        if not kwargs or not kwargs.get("params"):
            return None
        
        _logger.info(f"WHAT IS KWARGS {kwargs.get('params')}")    
        patient_details = kwargs.get('params').get("patient_data")
        service_vals = kwargs.get('params').get("service_storage")
        if not service_vals and not patient_details:
            return None
        firstname = patient_details.get("first_name")
        secondname = patient_details.get("middle_name")
        lastname = patient_details.get("lastname")
        email = patient_details.get("email")
        patient_id = patient_details.get("patient_id")
        dob = patient_details.get("dob")
        dob_list = dob.split("/")
        dob_list.reverse()
        formatted_dob = "-".join(dob_list)
        sex = patient_details.get("gender")
        phone = patient_details.get("phone")
        state_id = patient_details.get("state_id")
        patient = None
        state = None
        partner_id = None
        if patient_id:
            patient = Patient.search(
                [('identification_code', '=', patient_details.get("patient_id"))])
        if not patient:
            _logger.info(f"************** phone ************** {phone}, ************** formatted dob ************** {formatted_dob}")
            patient = Patient.find_patient_by_phone_dob(phone, formatted_dob)
            _logger.info(f"************** patient ************** {patient}")

        if state_id:
            state = request.env['res.country.state'].sudo().search(
                [('id', '=', int(state_id or False))]
            )
        country_id = request.env['res.country'].sudo().search(
            ['|',('name', '=', 'Nigeria'), ('id', '=', 163)]
        )
        patient_vals = {
            'firstname': firstname,
            'lastname2': secondname,
            'lastname': lastname,
            'email': email,
            'sex': sex,
            'dob': formatted_dob,
            'phone': phone,
            # 'state_id': state.id if state else int(state_id) or False,
            'country_id': country_id.id
        }
        if not patient:
            patient = self.create_patient(patient_vals)
        patient_id = patient and patient.id or None
        if patient_id:
            partner_id = patient.partner_id and patient.partner_id.id
        request.session['patient_id'] = patient_id
        request.session['partner_id'] = partner_id
        request.session['serviceDate'] = service_vals.get("serviceDate")
        request.session['serviceTime'] = service_vals.get("serviceTime")
        request.session['serviceLocationID'] = service_vals.get("locationid")
        request.session['serviceProviderID'] = service_vals.get("providerid")
        request.session['serviceID'] = service_vals.get("serviceid")

        _logger.info(f"STORED SESSIONS service_vals{service_vals}")
        service_client_Data = {
            'name': f"{firstname or patient.firstname} {lastname or patient.lastname}" or patient.name,
            'email': email or patient.email,
            'phone': phone or patient.phone or patient.mobile,
            'patientId': patient.identification_code,
        }
        request.session['serviceClientData'] = service_client_Data
        # if patient is not found, save the stringified values to session
        # request.session['partner_vals'] = json.dumps(patient_vals)
        self.create_service_sale_order(patient.partner_id, service_vals)
        _logger.info(f"SERVICE PATIENT ************** {patient}")
        return {
            "partner_id": partner_id,
            "patient_id": patient_id,
            "return_url": '/service-final'
        }

    def create_patient(self, vals):
        Patient = request.env['oeh.medical.patient'].sudo()
        patient = Patient.create(vals)
        return patient

    def create_service_sale_order(self, partner_id, service_vals):
        """expecting vals as 
            service_storage = {
                        'serviceid': res.appointment_service_id,
                        'service_name': res.service_name,
                        'price': res.price,
                        'location_prices': res.price,
                        'is_registration': true,
                        'registration_price': res.registration_price,
                    }
        """
        sale_order = False
        Saleorder = request.env['sale.order'].sudo()
        serviceid = service_vals.get('serviceid')
        service_price = service_vals.get('price')
        branch_code = service_vals.get('location_code')
        appointment_date = service_vals.get('appointment_date')
        appointment_time = service_vals.get('appointment_time')
        request.session['service_appointment_date'] = appointment_date
        request.session['service_appointment_time'] = appointment_time
        branch_code = service_vals.get('location_code')
        partner_id = partner_id
        # partner_id = partner_vals.get('partner_id') 
        service = request.env['eha_service.service'].sudo().search(
            [('appointment_service_id', '=', serviceid)], limit=1)
        product_id = service.product_id
        if service and product_id:
            warehouse = request.env["stock.warehouse"].sudo().search([
                        ("active", "=", True)], limit=1)
            branch_id = request.env["eha.branch"].sudo().search([
                        ("code", "=", branch_code)], limit=1)
            orders = [{
                        'product_id': product_id.id,
                        'name': product_id.name or service.name,
                        'price_unit': service_price,
                        'product_uom_qty': 1,
                        'product_uom': product_id.uom_id.id,
                    }]
            if service_vals.get('is_registration') and service_vals.get('registration_price') > 0:
                # checks if there is a new registration involved
                registration_product = request.env['product.product'].sudo().search(
                [('default_code', '=', 'Website-Registration')], limit=1)
                orders.append(
                    {
                        'product_id': registration_product.id,
                        'name': registration_product.name or "Website-Registration",
                        'price_unit': registration_product.list_price,
                        'product_uom_qty': 1,
                        'product_uom': registration_product.uom_id.id,
                    }
                )
            so_vals = {
                'date_order': datetime.now(),
                "partner_id": partner_id.id,
                "partner_invoice_id": partner_id.id,
                "partner_shipping_id": partner_id.id,
                "warehouse_id": warehouse.id,
                "branch_id": branch_id.id,
                # "company_id": int(request.website.company_id.id) if request.website.company_id.id else False,
                # "website_id": self.id,
                # "pricelist_id": int(pricelist_id),
                "order_line":
                            [(0, 0, order) for order in orders]
            }
            sale_order = Saleorder.create(so_vals)
            request.session['service_sale_order_id'] = sale_order.id
            request.session['is_service_booking'] = True
            _logger.info(f"SERVICE SALE ORDER ************** {sale_order} and again SESSION {request.session}")

        else:
            _logger.info(f"SERVICE SALE ORDER NO SERVICE FOUND **************")
        return sale_order
