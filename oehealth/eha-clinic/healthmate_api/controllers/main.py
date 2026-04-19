"""Part of odoo. See LICENSE file for full copyright and licensing details."""

import functools
import logging
from odoo import api, fields, models, _
import requests
from odoo import http
from odoo.http import request, Response# , JsonRequest
from odoo.tools import date_utils
from odoo.addons.eha_auth.controllers.helpers import validate_token, invalid_response, valid_response
import json
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import ValidationError
from datetime import datetime
from datetime import date
_logger = logging.getLogger(__name__)

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}


class APIController(http.Controller):
    """."""
    #GET: '/api/v1/members'
    # @validate_token
    # @http.route(['/api/v1/patients', '/api/v1/patients/<id>'], type="http", auth="none", methods=["GET"], csrf=False)
    # def get(self, id=None, **payload):
    #     '''
    #     Return patients that have active subscription
    #     Args:
    #         **id: refers to the patient_id (the odoo system generated Id).
    #     Sample Request:
    #         url = "http://localhost:8069/api/v1/patients"
    #         headers =  {"token":"token_962d374c024c0cc56c21eeba9ae2fa03b6d191c0"}
    #         req = requests.get(url, headers=headers)
    #         req.json()
    #     '''

    #     data = (
    #         request.env['oeh.medical.patient']
    #         .sudo()
    #         .search([])
    #     )
    #     patient_data = [
    #         {
    #             "patient_id": p.id,
    #             "identification_code": p.identification_code,
    #             'partner_id': p.partner_id.id,
    #             "dob": p.dob,
    #             "firstname": p.firstname,
    #             "lastname": p.lastname,
    #         } for p in data]
    #     if id:
    #         domain = [("id", "=", int(id))]
    #         data = (
    #             request.env['oeh.medical.patient']
    #             .sudo()
    #             .search(domain)
    #         )
    #         if not data:
    #             return invalid_response(
    #                 "patient_not_found",
    #                 "patient with %s was not found." % id,
    #                 404,
    #             )
    #         patient_data = {
    #             "patient_id": data.id,
    #             "identification_code": data.identification_code,
    #             'partner_id': data.partner_id.id,
    #             "dob": data.dob,
    #             "firstname": data.firstname,
    #             "lastname": data.lastname,
    #         }

    #     return valid_response(patient_data)

    def alternative_json_response(self, result=None, error=None):
        if error is not None:
            response = error
        if result is not None:
            response = result

        mime = 'application/json'
        body = json.dumps(response, default=date_utils.json_default)

        return Response(
            body, status=error and error.pop('http_status', 200) or 200,
            headers=[('Content-Type', mime), ('Content-Length', len(body))]
        )

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
        if data:
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
                if not (reasons_for_test):
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

    def validate_fields(self, data, isEcommerce=False):
        error_item = []
        productObj = request.env['product.product'].sudo()
        branch_model = request.env['eha.branch'].sudo()

        testlocation = data.get('order').get('test_location')
        productlist = data.get('order').get('products')
        source = data.get('source')
        partner = data.get('order').get('partner')
        user_id = data.get('order').get('user_id')
        coupon_code = data.get('coupon_code')

        if not (user_id or partner):
            error_item.append(
                "Customer user id or partner details must be provided\n ")
        if partner:
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

                    if pd.get('unit_price'):
                        if type(pd.get('unit_price')) in [float, int]:
                            if int(pd.get('unit_price')) < 0:
                                error_item.append(
                                    "Product Price must not be lesser than 0\n ")
                        else:
                            error_item.append(
                                "Please Ensure that the product unit price is of type integer or float \n ")
                else:
                    error_item.append(
                        "No Product value found - Ensure you provide the Value \n ")
        else:
            error_item.append("You must provide at least one product")

        if source == "healthmate":
            if testlocation:
                testlocationid = int(testlocation)
                branch = self.get_branch_by_simplybook_id(testlocationid)
                branch_id = branch.id if branch else False
                if not branch_id:
                    error_item.append(
                        f"Healthmate Test location ID ({testlocationid}) not found!")
            else:
                error_item.append("Please provide Test location!")
        if not isEcommerce:
            patient_error_validation = self.patient_field_validation(
                data.get('cif_data'))
            error_item += patient_error_validation
        return error_item

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

    def get_country_id(self, dialing_code):

        if dialing_code:
            code = dialing_code.replace('+', '')
            dialing_code = int(code)
            country_id = request.env['res.country'].sudo().search(
                [('phone_code', '=', dialing_code)], limit=1)
            return country_id.id if country_id else False
        else:
            return False

    @http.route("/api/v1/blood-pressure-diary", type="json", auth="public", methods=["POST", "GET"], csrf=False)
    def healthmate_medical_diary(self, **kw):
        """data = {
                "reference": 'WQEWRTREERRERRER',
                "patient_id": 'HP0008',
                "blood_diary": [
                    {
                        "diastolic": 4,
                        "systolic": 5,
                        "date_of_reading": "11/13/2020 01:00:01"
                    }, 
                    {
                        "diastolic": 60,
                        "systolic": 190,
                        "date_of_reading": "12/06/2020 01:00:01"
                    }
                ],
            }
        """
        # this is to remove the default json typed endpoints response format to normal response object
        # request._json_response = self.alternative_json_response.__get__(
        #     request, JsonRequest)
        data = json.loads(request.httprequest.data.decode("utf8"))
        _logger.info("PATIENT DATA %s" % json.dumps(data, indent=4))
        error_item = ["Error Found: "]

        patient_id = data.get('patient_id', 0)
        diary_items = data.get('blood_diary')
        reference = data.get('reference', '')
        Patient = request.env['oeh.medical.patient'].sudo()
        Diary = request.env['oeh.medical.blood.pressure.diary'].sudo()
        if diary_items:
            for rec in diary_items:
                if not all([rec.get('diastolic'), rec.get('systolic'), rec.get('date_of_reading')]):
                    error_item.append(
                        'Ensure that you provide systolic, diastolic and datetime values')

        if not patient_id:
            error_item.append('No patient records !!!')

        if len(error_item) > 1:
            _logger.info("VALIDATION ERROR %s" % error_item)
            return {"status": "failure", "message": ',\n'.join(error_item)}

        #####
        try:
            patient = Patient.search(
                [('identification_code', '=', patient_id)], limit=1)
            for diary in diary_items:
                systolic_pressure = diary.get('systolic')
                diastolic_pressure = diary.get('diastolic')
                reference = diary.get('reference')
                date_of_reading = diary.get('date_of_reading')
                vals = {
                    'systolic_pressure': systolic_pressure,
                    'diastolic_pressure': diastolic_pressure,
                    'reference': reference,
                    'date_of_reading': date_of_reading,
                    'patient_id': patient.id
                }
                Diary.create(vals)
            # return records in response
            # http.Response.status = "201"
            return {
                "message": "Record successfully created!",
            }
        except Exception as e:
            _logger.exception(e)
            return {"message": str(e)}

    def patient_validation(self, rec):
        # where rec is the data items provided
        error_list = []
        gender = rec.get('gender')
        email = rec.get('email')
        dob = rec.get('dob')
        name = rec.get('name')
        phone = rec.get('phone_contact').get('phone_number')
        patient_first_name = rec.get('patient_full_name').get('firstname')
        patient_last_name = rec.get('patient_full_name').get('lastname')
        secondary_phone_number = rec.get(
            'phone_contact').get('secondary_phone_number')
        dialing_code = rec.get('phone_contact').get('dialing_code')
        if not dialing_code:
            error_list.append(
                "Please ensure that you provide valid dialing code")
        if not (gender):
            error_list.append("Please ensure that you provide patients Gender")
        else:
            if gender.title() not in ["Male", "Female"]:
                error_list.append(
                    "Please ensure Gender value is set to Female or Male")

        if not (phone or secondary_phone_number):
            error_list.append(
                "Please ensure that you provide Phone or secondary phone number")

        if not self.get_country_id(dialing_code):
            error_list.append(
                "No Country found. Please provide a valid country dialing code")
        if not (email):
            error_list.append("Please ensure that you provide patients email")

        if not (dob):
            error_list.append("Please ensure that you provide patients DOB")

        if not any([patient_last_name, patient_first_name]):
            if not (name):
                error_list.append(
                    "Please ensure that you provide patients Name")
        return error_list

    @http.route(['/api/v1/update/refill'], type="json", auth="none", method=['POST', 'GET'], csrf=False)
    def api_update_prescription_refill(self, **kw):
        """
         # where ids (arrayof integers) is the record instance of each refill line of a prescription
         # state: a text value 'done' or 'open': default is open 
        data = {'orders': [
            {
            'id':7,
            'state': 'done',
            'date_of_refill': '09/12/2022',
                }, 
            {'id': 4,
            'state': 'done',
            'date_of_refill': '10/12/2022',
            }
            ]}
        """
        try:
            # request._json_response = self.alternative_json_response.__get__(
            #     request, JsonRequest)
            data = json.loads(request.httprequest.data.decode("utf8"))

            def validate_refill_values():
                error_item = []
                if not any([
                    data.get('orders'),
                ]):
                    error_item.append(
                        """You must provide refill orders
                        """
                    )
                return error_item
            errors = validate_refill_values()
            refill_obj = request.env['oeh.medical.prescription.refill']
            if errors:
                return {
                    "status": "failure",
                    "message": ',\n'.join(errors),
                    "data": ""
                }
            else:
                refill_orders = data.get('orders')
                err_msg = []
                for rf_dict in refill_orders:
                    rf = refill_obj.sudo().search([
                        ('id', '=', rf_dict.get('id', False))
                    ], limit=1)
                    dt_refill = rf_dict.get('date_of_refill')
                    if rf:
                        rf.sudo().write({
                            'state': rf_dict.get('state'),
                            'date_refill_actual': datetime.strptime(dt_refill, '%d/%m/%Y') if dt_refill else False
                        })
                    else:
                        err_msg.append(f"{rf_dict.get('id', False)}")
                msg = "Record successfully updated!" if not err_msg else \
                    "Successful but record(s) with ID(s) not found to update " + \
                    ",".join(err_msg)
                return {
                    "status": "success",
                    "message": msg,
                    "data": ""

                }
        except Exception as e:
            _logger.exception(e)
            return {
                "status": "failure",
                "message": str(e),
                "data": False
            }

    # @validate_token

    @http.route([
        "/api/v1/get-insurance"
    ], type="json", auth="none", methods=["POST", "GET"], csrf=False)
    def api_get_insurance(
            self,
            **kw):
        """  
            data = {
                'partner_id': '',
                'ins_no': '',
                'patient_no': 'HP0001',

            }
        """
        # request._json_response = self.alternative_json_response.__get__(
        #     request, JsonRequest)
        data = json.loads(request.httprequest.data.decode("utf8"))
        _logger.info("PATIENT DATA LOADING .... %s" %
                     json.dumps(data, indent=4))
        try:
            if data:
                def validate_data():
                    error_item = []
                    if not any([
                        data.get('partner_id'),
                        data.get('ins_no'),
                        data.get('patient_no')
                    ]):
                        error_item.append(
                            """
                            You must provide either partner id 
                            or insurance id or patient HP number
                            """
                        )
                    if data.get('partner_id'):
                        partner = request.env['res.partner'].sudo().search([
                            ('id', '=', data.get('partner_id'))], limit=1)
                        if not partner:
                            error_item.append(
                                """
                                Please provider a valid system partner id
                                """
                            )
                        else:
                            insurance = request.env['eha.medical.insurance'].sudo().search([
                                ('partner_id', '=', data.get('partner_id')), ('state', '=', 'Active')], limit=1)
                            if not insurance:
                                error_item.append(
                                    """
                                    Insurance with Partner ID not found !!!
                                    Please provide a valid partner ID
                                    """
                                )
                    elif data.get('ins_no'):
                        insurance = request.env['eha.medical.insurance'].sudo().search([
                            ('ins_no', '=', data.get('ins_no')), ('state', '=', 'Active')], limit=1)
                        if not insurance:
                            error_item.append(
                                """
                                Insurance Number not found !!! Please provide a valid insurance Number
                                """
                            )
                    elif data.get('patient_no'):
                        insurance = request.env['eha.medical.insurance'].sudo().search([
                            ('patientid', '=', data.get('patient_no')), ('state', '=', 'Active')], limit=1)
                        if not insurance:
                            error_item.append(
                                """
                                Patient HP Number not found !!! Please provide a valid Patient HP Number
                                """
                            )
                    return error_item
                errors = validate_data()
                if errors:
                    return {
                        "status": "failure",
                        "message": ',\n'.join(errors),
                        "data": ""
                    }
                else:
                    data_vals = {}
                    insurance = request.env['eha.medical.insurance'].sudo()

                    def _prepare_insurance_vals(insurance_ids):
                        vals = None
                        for ins in insurance_ids:
                            insurance_dicts = {
                                'partner_id': ins.partner_id.id or "",
                                'partner_name': ins.partner_id.name or "",
                                'patientid': ins.patientid or "",
                                'start_date': ins.start_date or "",
                                'exp_date': ins.exp_date or "",
                                'info': ins.info or "",
                                'state': ins.state or "",
                                'insurance_info': {
                                    'insurance_company': ins.insurance_company.name if ins.insurance_company else False,
                                    'insurance_email': ins.insurance_company.email or "",
                                    'insurance_phone': ins.insurance_company.phone or ins.insurance_company.mobile,
                                    'insurance_address': ins.insurance_company.street or ins.insurance_company.street2,
                                    'insurance_country_name': ins.insurance_company.country_id.name or "",
                                    'insurance_country_id': ins.insurance_company.country_id.id or "",
                                    'ins_type': ins.ins_type.name if ins.ins_type else False,
                                }
                            }
                            vals = insurance_dicts
                        return vals
                    if data.get('partner_id'):
                        insurance_ids = insurance.search([
                            ('partner_id', '=', data.get('partner_id')
                             ), ('state', '=', 'Active')
                        ], limit=1)
                        data_vals = _prepare_insurance_vals(insurance_ids)

                    elif data.get('ins_no'):
                        insurance_ids = insurance.search([
                            ('ins_no', '=', data.get('ins_no')
                             ), ('state', '=', 'Active')
                        ], limit=1)
                        data_vals = _prepare_insurance_vals(insurance_ids)

                    elif data.get('patient_no'):
                        insurance_ids = insurance.search([
                            ('patientid', '=', data.get('patient_no')
                             ), ('state', '=', 'Active')
                        ], limit=1)
                        data_vals = _prepare_insurance_vals(insurance_ids)
                    return {
                        "status": "success",
                        "message": "Record successfully processed!",
                        "data": data_vals
                    }
        except Exception as e:
            _logger.exception(e)
            return {
                "status": "failure",
                "message": str(e),
                "data": False
            }

    # @validate_token
    @http.route(["/api/v1/get-patient-invoice"], type="json", auth="none", methods=["POST", "GET"], csrf=False)
    def api_get_patient_invoice(
            self, **kw):
        """  
            data = {
                'patient_no': 'HP0001',
            }
        """
        # request._json_response = self.alternative_json_response.__get__(
        #     request, JsonRequest)
        data = json.loads(request.httprequest.data.decode("utf8"))
        _logger.info("PATIENT INVOICE LOADING .... %s" %
                     json.dumps(data, indent=4))
        try:
            if data:
                def validate_data():
                    error_item = []
                    if not any([data.get('patient_no')]):
                        error_item.append(
                            """You must provide patient HP number""")
                    return error_item
                errors = validate_data()
                if errors:
                    return {
                        "status": "failure",
                        "message": ',\n'.join(errors),
                        "data": ""
                    }
                else:
                    partner = request.env['res.partner'].sudo()
                    partner_ref = partner.search(
                        [('hp_number', '=', data.get('patient_no'))], limit=1)
                    invoice_items = []
                    if partner_ref:
                        invoices = request.env['account.move'].sudo().search(
                            [('partner_id', '=', partner_ref.id)])
                        invoices_vals = [{
                            'id': invoice.id,
                            'invoice_nummber': invoice.name,
                            'partner_name': invoice.partner_id.name,
                            'partner_hp_number': invoice.partner_id.hp_number,
                            'invoice_date': datetime.strftime(invoice.invoice_date, '%Y-%m-%d') if invoice.invoice_date else "",
                            'amount_total': invoice.amount_total,
                            'amount_paid': invoice.amount_total - invoice.amount_residual,
                            'amount_outstanding': invoice.amount_residual,
                            'invoice_currency_id': invoice.currency_id.name,
                        } for invoice in invoices]
                        return {
                            "status": "success",
                            "message": "Record successfully processed!",
                            "data": invoices_vals
                        }
                    else:
                        return {
                            "status": "failure",
                            "message": f"Partner with HP Number {data.get('patient_no')} does not exists",
                            "data": ""
                        }
            else:
                return {
                    "status": "failure",
                    "message": f"Please Provide a valid payload",
                    "data": ""
                }

        except Exception as e:
            _logger.exception(e)
            return {
                "status": "failure",
                "message": str(e),
                "data": False
            }

    def link_patient_to_user(self, patientid):
        if patientid:
            user = request.env["res.users"].sudo().browse([request.uid])
            user.write({'linked_patient_ids': [(4, patientid)]})
            _logger.info('Log user linked !!!')
        else:
            _logger.info('Logged in user not detected')

    # @validate_token
    @http.route("/api/v1/create-patient", type="json", auth="public", methods=["POST", "GET"], csrf=False)
    def api_create_patient(self, **kw):
        """ 
            data = {
                'patient_id': 'HP0001',
                'name': '', # Pass full name e.g Firstname  Midlname Lastname
                'patient_full_name': {
                    'firstname': 'Oeylopa',
                    'middlename': 'Sasa',
                    'lastname': 'Dmanel'
                    }
                },
                'phone_contact': {
                    'dialing_code': '+234',
                    'phone_number': '7060001111',
                    'secondary_phone_number': '8065559990'
                    }
                },

                'state_id': 2,
                'country_id': 163
                'dob': '12/12/2002',
                'email': 'chisk@gmail.com',
                'gender': 'male',
                'city': 'Awka',
                'address': '45 Nsukka Street',
                'passport_number': '991188KKSKA',
            }
        """
        # this is to remove the default json typed endpoints response format to normal response object
        # request._json_response = self.alternative_json_response.__get__(
        #     request, JsonRequest)
        data = json.loads(request.httprequest.data.decode("utf8"))
        _logger.info("PATIENT DATA LOADING .... %s" %
                     json.dumps(data, indent=4))
        error_item = []
        #####
        try:
            if data:
                # for rec in data:
                error_item = self.patient_validation(data)
                if error_item:
                    _logger.info("VALIDATION ERROR %s" % error_item)
                    return {"status": "failure", "message": ',\n'.join(error_item),
                            "patient_id": False}
                else:
                    patient_id = self.create_patient(data)
                    # return records in response
                    # http.Response.status = "201"
                    patient = request.env['oeh.medical.patient'].sudo().browse([
                        patient_id])
                    self.link_patient_to_user(patient_id)
                    patientvals = {
                        'id': patient.id or "",
                        'patient_id': patient.identification_code or "",
                        'partner_id': patient.partner_id.id or "",
                        'firstname': patient.firstname or "",
                        'middlename': patient.lastname2 or "",
                        'lastname': patient.lastname or "",
                        'marital_status': patient.marital_status or "",
                        'sex': patient.sex or "",
                        'dob': patient.dob or "",
                        'email': patient.email or "",
                        'phone': patient.phone or "",
                        'mobile': patient.mobile or "",
                        'street': patient.street or "",
                        'city': patient.city or "",
                        'state_id': patient.state_id.name or "",
                        'country_id': patient.country_id.name or "",
                        'passport_no': patient.passport_no or "",
                    }
                    return {
                        "status": "success",
                        "message": "Record successfully processed!",
                        "data": patientvals
                    }
            else:
                return {"status": "failure", "message": 'No Data found to process', 'patient_id': False}
        except Exception as e:
            _logger.exception(e)
            return {"status": "failure", "message": str(e), "patient_id": False}

    # @validate_token
    @http.route(['/api/v1/eha-ecommerce'], type="json", auth="public", methods=["POST", "GET"], csrf=False)
    def healthmate_ecommerce(self, **kw):
        """parameter = {
                "order": {
                    "user_id": 2,
                    "order_ref": "healthmate order ref to ",
                    "payment_ref": "89jjfjjf",
                    "payment_gateway": "rave",
                    "branch_id": 4, #1,
                    "warehouse_id": 1,
                    "shipping_method": 1, # odoo => property_delivery_id
                    "partner_shipping_id": {
                      "id": 3,
                      "is_updated" : False,
                      "address" : "the newly inputed address",
                      "state_id" : 1,
                      "country_id" : 17,
                      "city" : "Abuja",
                      "lga" : "Awaka",
                      "firstname" : "Awaka",
                      "lastname" : "Awaka",
                    },
                    "partner_invoice_id": {
                      "id": None,
                      "is_updated" : False,
                      "address" : "the newly inputed address",
                      "state_id" : 1,
                      "country_id" : 17,
                      "city" : "Abuja",
                      "lga" : "Awaka",
                      "firstname" : "Awaka",
                      "lastname" : "Awaka",
                    }
                    "products": [{
                        "product_id": 9, #7933,#4,
                        "product_uom_qty": 5, # purchased Quantity goes
                        "unit_price": 653, # product_price,
                        "discount_percentage": 0 # Not required
                    }],
                }
            }
        """
        data = json.loads(request.httprequest.data.decode("utf8"))
        _logger.info("API DATA %s" % json.dumps(data, indent=4))
        check_validation_errors = self.validate_fields(data, True)
        error_item = ["Error Found: "]

        if len(error_item) > 1:
            _logger.info("VALIDATION ERROR %s" % error_item)
            return {"status": "failure", "message": ',\n'.join(error_item)}

        try:
            invoice_obj = request.env['account.move'].sudo()
            account_journal = request.env['account.journal'].sudo()
            account_payment_obj = request.env['account.payment'].sudo()
            productObj = request.env['product.product'].sudo()
            Partner = request.env['res.partner'].sudo()
            user_id = data.get('order').get('user_id')
            partner_invoice = data.get('order').get('partner_invoice_id')
            partner_shipping = data.get('order').get('partner_shipping_id')
            warehouse_id = data.get('order').get('warehouse_id')
            shipping_method = data.get('order').get('shipping_method')
            branch = data.get('order').get('branch_id')
            partner = None
            billing_address_id, delivery_address_id = None, None

            if branch:
                branches = request.env['eha.branch'].sudo().search(
                    [('id', '=', int(branch))])
                if not branches:
                    return {
                        "error": "Branch not found",
                        "message": f"Branch with id {branch} not found.",
                        "status_code": 400
                    }

            if user_id:
                user = request.env['res.users'].sudo().search(
                    [('id', '=', int(user_id))])
                if not user:
                    return {
                        "error": "user_not_found",
                        "message": f"User with id {user_id} not found.",
                        "status_code": 400
                    }
                partner = user.partner_id
                # ensure the partner ID exists
                if not partner:
                    return {
                        "error": "partner_not_found",
                        "message": f"User with ID {user_id} don't have a related partner",
                        "status_code": 400
                    }
            else:
                return {
                    "error": "user_not_found",
                    "message": f"User ID is required for this transaction",
                    "status_code": 400
                }

            if partner_invoice:
                partner_invoice_id = partner_invoice.get('id') or 0
                invoice_vals = {
                    'street': partner_invoice.get('address'),
                    'state_id': partner_invoice.get('state_id'),
                    'country_id': partner_invoice.get('country_id'),
                    'city': partner_invoice.get('city'),
                    'lga': partner_invoice.get('lga'),
                    'type': "invoice",
                }
                if not partner_invoice.get('is_updated') and not partner_invoice.get('id'):
                    invoice_vals.setdefault(
                        'firstname', partner_invoice.get('firstname'))
                    invoice_vals.setdefault(
                        'lastname', partner_invoice.get('lastname'))
                    invoice_vals.setdefault('parent_id', partner.id)
                    billing_address_id = Partner.create(invoice_vals).id

                elif partner_invoice.get('is_updated') and partner_invoice.get('id'):
                    billing_address_id = Partner.search(
                        [('id', '=', int(partner_invoice_id))], limit=1)
                    if not billing_address_id:
                        return {
                            "error": "billing_address_not_found",
                            "message": f"Partner billing Adresses {billing_address_id} not found.",
                            "status_code": 400
                        }
                    else:
                        billing_address_id.sudo().update(invoice_vals)
                        billing_address_id = billing_address_id.id
                else:
                    _logger.info("CHECKING BILLING ID ==> ",
                                 partner_invoice_id)
                    billing_address_id = Partner.search(
                        [('id', '=', int(partner_invoice_id))], limit=1)
                    if not billing_address_id:
                        return {
                            "error": "billing_address_not_found",
                            "message": f"Partner billing Adresses {billing_address_id} not found.",
                            "status_code": 400
                        }
                    billing_address_id = billing_address_id.id

            if partner_shipping:
                partner_shipping_id = partner_shipping.get('id') or 0
                shipping_vals = {
                    'street': partner_shipping.get('address'),
                    'state_id': partner_shipping.get('state_id'),
                    'country_id': partner_shipping.get('country_id'),
                    'city': partner_shipping.get('city'),
                    'lga': partner_shipping.get('lga'),
                    'type': "delivery",

                    # 'parent_id': partner.id,
                }
                if not partner_shipping.get('is_updated') and not partner_shipping.get('id'):
                    shipping_vals.setdefault(
                        'firstname', partner_shipping.get('firstname'))
                    shipping_vals.setdefault(
                        'lastname', partner_shipping.get('lastname'))
                    shipping_vals.setdefault('parent_id', partner.id)
                    delivery_address_id = Partner.create(shipping_vals).id

                elif partner_shipping.get('is_updated') and partner_shipping.get('id'):
                    _logger.info(
                        "CHECKING SHIPPING ID ON UPDATE ==> ", partner_shipping_id)

                    delivery_address_id = Partner.search(
                        [('id', '=', int(partner_shipping_id))], limit=1)
                    if not delivery_address_id:
                        return {
                            "error": "partner_Shipping_not_found",
                            "message": f"Partner Shipping Adresses {partner_shipping_id} not found.",
                            "status_code": 400
                        }
                    else:
                        delivery_address_id.sudo().update(shipping_vals)
                        delivery_address_id = delivery_address_id.id

                else:
                    delivery_address_id = Partner.search(
                        [('id', '=', int(partner_shipping_id))], limit=1)
                    _logger.info(
                        "CHECKING SHIPPING ID ON EXISTING ==> ", partner_shipping_id)
                    if not delivery_address_id:
                        return {
                            "error": "partner_Shipping_not_found",
                            "message": f"Partner Shipping Adresses {partner_shipping_id} not found.",
                            "status_code": 400
                        }
                    delivery_address_id = delivery_address_id.id

            if warehouse_id:
                warehouse = request.env['stock.warehouse'].sudo().search(
                    [('id', '=', int(warehouse_id))])
                if not warehouse:
                    return {
                        "error": "warehouse_not_found",
                        "message": f"Warehouse ID {warehouse_id} not found.",
                        "status_code": 400
                    }
            if shipping_method:
                shipping = request.env['delivery.carrier'].sudo().search(
                    [('id', '=', shipping_method)])
                if not shipping:
                    return {
                        "error": "shipping_method_not_found",
                        "message": f"shipping method ID {shipping_method} not found.",
                        "status_code": 400
                    }
            branch_id = int(data.get('order').get('branch_id')) if data.get(
                'order').get('branch_id') else False
            contact_dicts = {
                "warehouse_id": warehouse_id,
                "partner_invoice_id": billing_address_id,
                "partner_shipping_id": delivery_address_id,
            }
            sale_order = self.create_or_get_sale_order(
                partner, branch_id, contact_dicts, warehouse_id=int(warehouse_id))
            for datas in data.get('order')['products']:
                product_id = int(datas['product_id'])
                product_uom_qty = int(datas['product_uom_qty'])
                price = int(datas['unit_price']) if datas['unit_price'] else productObj.browse(
                    [product_id]).list_price
                discount = float(datas['discount_percentage']
                                 ) if datas['discount_percentage'] else 0.00
                description = False
                if sale_order.client_order_ref:
                    names = sale_order.name
                    today = date.today()
                    description = "{} - {}".format(names,
                                                   today.strftime("%d/%m/%y"))

                so_line_val = {
                    'product_id': product_id,
                    'order_id': sale_order.id,
                    'name': description if description else "",
                    'product_uom_qty': product_uom_qty,
                    'price_unit': price,
                    'discount': discount,
                    'display_type': False
                }
                request.env['sale.order.line'].sudo().create(so_line_val)
            sale_order.action_confirm()
            inv = sale_order.sudo()._create_invoices()[0]
            inv.post()
            sale_payment_method = request.env['account.payment.method'].sudo().search(
                [('code', '=', 'manual'), ('payment_type', '=', 'inbound')], limit=1)

            journal_id = self.journal_id(False)
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
                'partner_id': sale_order.partner_id.id,  # or partner_id,
            }
            payment = account_payment_obj.create(acc_values)
            payment.post()
            http.Response.status = "201"
            return {
                "status": "successful",
                "invoice": {
                    'id': inv.id,
                    # INV-2021-14001
                    'invoice_code': "-".join((inv.name).split("/")),
                    'reference_number': inv.name,
                    'invoice_date': datetime.strftime(inv.invoice_date, '%Y-%m-%d') if inv.invoice_date else None,
                    'due_date': datetime.strftime(inv.invoice_date_due, '%Y-%m-%d') if inv.invoice_date_due else None,
                    'total': inv.amount_total,
                    'amount_due': inv.amount_residual,
                    'bank': inv.partner_bank_id.bank_id.name or None,
                    'account_number': inv.partner_bank_id.acc_number or None,
                    'lines': [{
                        'product': line.product_id.name,
                        'requires_appointment': line.product_id.requires_appointment or "",
                        'is_returnable': line.product_id.is_returnable or "",
                        'quantity': line.quantity,
                        'unit_price': line.price_unit,
                        'amount': line.price_subtotal,
                        'discount': line.discount
                    } for line in inv.invoice_line_ids]
                }
            }
        except Exception as e:
            _logger.exception(e)
            return {"status": "failure", "message": str(e)}

    # @validate_token
    @http.route("/api/v1/eha-payment", type="json", auth="public", methods=["POST", "GET"], csrf=False)
    def healthmate_payment(self, **kw):
        """parameter = {
                "order": {
                    "order_ref": "healthmate order ref to ",
                    "payment_ref": "89jjfjjf",
                    "payment_gateway": "rave"
                    "test_location": 4, #4, #1,
                    "products": [{
                        "product_id": 4, #7933,#4,
                        "product_uom_qty": 5,
                        "unit_price": 653,
                        "discount_percentage": 10
                    }],
                    "user_id": 214,
                    "partner":{
                        "patient_id": "", # "HP0001", 
                        "name": "Hicent Okonkwo",
                        "phone_contact": {
                                "dialing_code": "+234",
                                "phone_number": "07081120401",
                                "secondary_phone_number": ""
                                },
                        "email":"davidemas@gmail.com" 
                    }
                },
                "source": "healthmate",
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
        if not data:
            return {
                "error": "invalid_data",
                "message": "Data Not found",
                "status_code": 400
            }
        payment_gateway = data.get('order').get('payment_gateway')
        if payment_gateway not in ['rave', 'paystackAcquirer']:
            return {
                "error": "invalid_payment_gateway",
                "message": "payment getway must be rave or paystackAcquirer",
                "status_code": 400
            }
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
            if not self.verify_charge(verification_code, payment_gateway):
                return {"status": "failure", "message": 'Payment verification failed!'}
        try:
            coupon_code = data.get('coupon_code', 0)
            invoice_obj = request.env['account.move'].sudo()
            account_journal = request.env['account.journal'].sudo()
            account_payment_obj = request.env['account.payment'].sudo()
            productObj = request.env['product.product'].sudo()
            Patient = request.env['oeh.medical.patient'].sudo()
            Partner = request.env['res.partner'].sudo()
            user_id = data.get('order').get('user_id')
            if user_id:
                user = request.env['res.users'].sudo().search(
                    [('id', '=', int(user_id))])
                if not user:
                    return {
                        "error": "user_not_found",
                        "message": f"User with id {user_id} not found.",
                        "status_code": 400
                    }
                partner = user.partner_id
                # ensure the partner ID exists
                if not partner:
                    return {
                        "error": "partner_not_found",
                        "message": f"User with ID {user_id} don't have a related partner",
                        "status_code": 400
                    }
            else:
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

            # if request is coming from the website, the test_location_id is mapped to
            # locationId in simplybookme. We will retrieve the appropraite branch id
            # by mapping the location to a branch in odoo
            if data.get('source') == 'website':
                test_location_name = data.get(
                    'booking').get('test_location_name')
                branch = self.get_branch_by_name(test_location_name)
                branch_id = branch.id if branch else False
            elif data.get('source') == 'healthmate':
                testlocationid = int(data.get('order').get('test_location'))
                branch = self.get_branch_by_simplybook_id(testlocationid)
                branch_id = branch.id if branch else False
            else:
                branch_id = int(data.get('order').get('test_location')) if data.get(
                    'order').get('test_location') else False

            # Create a sale order
            sale_order = self.create_or_get_sale_order(
                partner, branch_id, warehouse_id=int(data.get("order")['warehouse_id']))
            for datas in data.get('order')['products']:
                product_id = int(datas['product_id'])
                product_uom_qty = int(datas['product_uom_qty'])
                price = int(datas['unit_price']) if datas['unit_price'] else productObj.browse(
                    [product_id]).list_price
                discount = float(datas['discount_percentage']
                                 ) if datas['discount_percentage'] else 0.00
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
                    'discount': discount,
                    'display_type': False
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
                # Auto Validated the invoice
                # inv.action_invoice_open()

                # Default company payment journal for sales
                sale_payment_method = request.env['account.payment.method'].sudo().search(
                    [('code', '=', 'manual'), ('payment_type', '=', 'inbound')], limit=1)

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
                journal_id = self.journal_id(acquirer)
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
                    'partner_id': sale_order.partner_id.id,
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

            next_available_slot = False
            booking = data.get("booking")
            if booking and booking.get("isSimplybook"):
                if data.get('source') == 'website':
                    # book appointment
                    next_available_slot = self.schedule_appointment(cifs, hsc)
            else:
                # send appointment support request to support@eha.ng
                if booking and booking.get("appointment_date"):
                    date_time = booking.get("appointment_date").split(" ")
                    appointment_date = date_time[0]
                    if len(date_time) > 1:
                        appointment_time = date_time[1]
                    else:
                        appointment_time = booking.get("selected_time")

                    if appointment_time and len(appointment_time.split(":")) > 1:
                        hour = int(appointment_time.split(":")[0])
                        minutes = appointment_time.split(":")[1]
                        time_label = "PM" if hour >= 12 else "AM"
                        if hour > 12:
                            time = "{}:{} {}".format(
                                int(hour) - 12, minutes, time_label)
                        else:
                            time = "{} {}".format(appointment_time, time_label)

                    # create booking and send mail to support for each CIF
                    location = booking.get("test_location_name")
                    # service = booking.get("service_id")
                    # selected_time_id = booking.get("selected_time_id")
                    # location_id = booking.get("location_id")
                    booking_date = booking.get("selected_date")
                    for cif in cifs:
                        # cif.generate_booking_appointment(location_id, service, booking_date, selected_time_id)
                        cif.send_appointment_support_email(
                            location, appointment_date, time)

            # return cif and invoice records in response
            http.Response.status = "201"
            return {
                "status": "successful",
                "next_available_slot": next_available_slot,
                "cif_data": [{'cif_id': c.id, 'name': c.name, 'url_token': c.url_token} for c in cifs],
                "invoice": {
                    'id': inv.id,
                    # INV-2021-14001
                    'invoice_code': "-".join((inv.name).split("/")),
                    'reference_number': inv.name,
                    'invoice_date': datetime.strftime(inv.invoice_date, '%Y-%m-%d') if inv.invoice_date else None,
                    'due_date': datetime.strftime(inv.invoice_date_due, '%Y-%m-%d') if inv.invoice_date_due else None,
                    'source': 'Healthmate',
                    'total': inv.amount_total,
                    'amount_due': inv.amount_residual,
                    'bank': inv.partner_bank_id.bank_id.name or None,
                    'account_number': inv.partner_bank_id.acc_number or None,
                    'lines': [{
                        'product': line.product_id.name,
                        'quantity': line.quantity,
                        'unit_price': line.price_unit,
                        'amount': line.price_subtotal,
                        'discount': line.discount
                    } for line in inv.invoice_line_ids]
                }
            }
        except Exception as e:
            _logger.exception(e)
            return {"status": "failure", "message": str(e)}

    def verify_charge(self, verification_code, payment_gateway):
        ''' verify payment charge '''
        _logger.info('CIF: Verifying Charge ...')

        payment_provider = request.env['payment.provider'].sudo().search(
            [('code', '=', payment_gateway)])

        if payment_provider.code == 'rave':
            url = 'https://api.flutterwave.com/v3/transactions/{}/verify'.format(
                verification_code)
            secret_key = payment_provider.rave_secret_key
        else:
            url = 'https://api.paystack.co/transaction/verify/{}'.format(
                verification_code)
            secret_key = payment_provider.paystack_secret_key

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
        Returns branch object by retrieving branch code from the service object store in ir_config_param.

        Args:
            **test_location_name: name of the test location provided 
            from simplybook on website appointment booking page.
        """
        _logger.info("CIF: Getting branch name from config service param ...")
        service_dict = json.loads(request.env['ir.config_parameter'].sudo(
        ).get_param('simplybookme_service_params'))
        service_list = service_dict.get("data")
        # Simplybook locations are mapped to odoo branch in the service JSON saved in ir_config_param
        # we will retrieve the branch from the json and use the code to search for the odoo branch
        branches = list(
            filter(lambda x: x['location_name'] == test_location_name, service_list))
        # the filter above could return multiple results since a branch can map to multiple simplybook servic
        # we will just take any branch from the list
        branch_dict = branches[0] if branches else {}
        return request.env['eha.branch'].sudo().search([('code', '=', branch_dict.get("branch_code"))]) if branch_dict else False

    def get_branch_by_simplybook_id(self, simplybook_location_id):
        _logger.info("CIF: Getting branch info from config service param ...")
        service_dict = json.loads(request.env['ir.config_parameter'].sudo(
        ).get_param('simplybookme_service_params'))
        service_list = service_dict.get("data")
        # Simplybook locations are mapped to odoo branch in the service JSON saved in ir_config_param
        # we will retrieve the branch from the json and use the code to search for the odoo branch
        branches = list(
            filter(lambda x: x['location_id'] == simplybook_location_id, service_list))
        # the filter above could return multiple results since a branch can map to multiple simplybook servic
        # we will just take any branch from the list
        branch_dict = branches[0] if branches else {}
        return request.env['eha.branch'].sudo().search([('code', '=', branch_dict.get("branch_code"))]) if branch_dict else False

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
        if data.get('cif_data'):
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

    def schedule_appointment(self, cifs, hsc):
        ''' Schedule appointment for new convid-19 workflow '''
        _logger.info("CIF: Scheduling CIF appointment on simplybook ...")

        next_available_slot = False
        for cif in cifs:
            branch = request.env['eha.branch'].sudo().search(
                [('id', '=', cif.test_location_id)])
            r = cif.schedule_simplybook_appointment(
                False, branch, cif.simplybookme_appointment_date, hsc)
            # schedule appointment returns a tuple
            res = r[0]
            bookings = res.get('bookings', [])
            next_available_slot = r[1]
            if bookings:
                booking = bookings[0]
                date_appt = fields.Datetime.from_string(
                    booking.get('start_datetime'))
                cif.write({
                    'simplybookme_appointment_code': booking.get('code'),
                    'simplybookme_appointment_date': date_appt,
                    'has_booked': True,
                })
        return next_available_slot

    def create_patient(self, rec):
        _logger.info("CIF: Creating patient ...")

        Patient = request.env['oeh.medical.patient'].sudo()
        if rec.get('patient_id'):
            patient = Patient.search(
                [('identification_code', '=', rec.get('patient_id'))])
            if patient:
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
        fname, lastname2, lastname = self.format_return_name(rec.get('name'))\
            if rec.get('name') else rec.get('patient_full_name').get('firstname'),\
            rec.get('patient_full_name').get('middlename'), rec.get(
                'patient_full_name').get('lastname')
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

    def create_or_get_sale_order(self, partner, branch_id, contact_dicts=False, warehouse_id=None):
        _logger.info("CIF: Retrieving of Creating Sale Order ...")
        coupon_code = partner.coupon_code
        if not warehouse_id:
            warehouse = contact_dicts.get(
                'warehouse_id') if contact_dicts else False
            if not warehouse:
                warehouse = request.env['stock.warehouse'].sudo().search(
                    [('branch_id', '=', branch_id)], limit=1) or False
            warehouse_id = warehouse and warehouse.id
        partner_invoice_id = contact_dicts.get(
            'partner_invoice_id') if contact_dicts and contact_dicts.get('partner_invoice_id') else partner.id
        partner_shipping_id = contact_dicts.get(
            'partner_shipping_id') if contact_dicts and contact_dicts.get('partner_shipping_id') else partner.id
        sale_value = {
            'partner_id': partner.id,
            'payer_id': partner.id,
            'partner_invoice_id': partner_invoice_id,
            'partner_shipping_id': partner_shipping_id,
            'branch_id': branch_id,
            'warehouse_id': int(warehouse_id),
            'payment_term_id': request.env.ref('account.account_payment_term_immediate').id,
            # set default warehouse to 1 or branch warehose, this can be modify when warehouse feature
            'client_order_ref': coupon_code if coupon_code else '',
        }
        if coupon_code and not partner.is_invoicing_required:
            saleOrder = request.env['sale.order'].sudo().search(
                [('state', '=', 'draft'), ('client_order_ref', '=', coupon_code)])
            if not saleOrder:
                saleOrder = request.env['sale.order'].sudo().create(sale_value)
            return saleOrder

        return request.env['sale.order'].sudo().create(sale_value)

    def journal_id(self, acquirer=False):
        company_id = request.env.user.company_id.id
        domain = [('type', 'in', ['bank', 'cash']),
                  ('company_id', '=', company_id)]
        journal_id = None
        bnk_journal_id = request.env['account.journal'].sudo().search(
            domain, limit=1).id
        company_journal = (request.env['account.move'].sudo().with_context(
            company_id=company_id or request.env.user.company_id.id).default_get(['journal_id'])['journal_id'])

        if acquirer:
            journal_id = acquirer.journal_id.id
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
