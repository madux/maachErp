# -*- coding: utf-8 -*-
import binascii
import time
from math import ceil
from datetime import datetime
import json

import requests
from requests.auth import HTTPBasicAuth

from urllib.parse import urlencode

from odoo import _, fields
from odoo.exceptions import UserError
from odoo.tools import float_repr, DEFAULT_SERVER_DATETIME_FORMAT, date_utils
import pytz

import logging

_logger = logging.getLogger(__name__)


class MyDHLProvider():

    def __init__(self, prod_environment, debug_logger):
        self.debug_logger = debug_logger
        if not prod_environment:
            self.url = 'https://express.api.dhl.com/mydhlapi/test'
        else:
            self.url = 'https://express.api.dhl.com/mydhlapi'

    def _get_rate_param(self, order, carrier):
        res = {}
        total_weight = carrier._dhl_convert_weight(sum(
            [(line.product_id.weight * line.product_qty) for line in order.order_line]), carrier.dhl_package_weight_unit)
        max_weight = carrier._dhl_convert_weight(
            carrier.dhl_default_packaging_id.max_weight, carrier.dhl_package_weight_unit)

        if total_weight and total_weight != '' and total_weight != False:
            total_weight = float(total_weight)

        if max_weight and max_weight != '' and max_weight != False:
            max_weight = float(max_weight)
        res = {
            'MessageTime': datetime.now().isoformat(),
            'MessageReference': 'ref:' + datetime.now().isoformat(),
            'carrier': carrier,
            'shipper_partner': order.warehouse_id.partner_id,
            'shipper_branch': order.warehouse_id.branch_id,
            'Date': time.strftime('%Y-%m-%d'),
            'recipient_partner': order.partner_shipping_id,
            'total_weight': total_weight,
            'currency_name': order.currency_id.name,
            'total_value': str(float_repr(sum([(line.price_unit * line.product_uom_qty) for line in order.order_line.filtered(lambda line: not line.is_delivery)]), 2)),
            'is_dutiable': carrier.dhl_dutiable,
            'package_ids': False,
        }
        if max_weight and total_weight > max_weight:
            total_package = int(ceil(total_weight / max_weight))
            last_package_weight = total_weight % max_weight
            res['total_packages'] = total_package
            res['last_package_weight'] = last_package_weight
            res['package_ids'] = carrier.dhl_default_packaging_id
        return res

    def rate_request(self, order, carrier):
        dict_response = {'price': 0.0,
                         'currency': False,
                         'error_found': False}

        param = self._get_rate_param(order, carrier)
        try:
            res = self._send_rate_request(param)
        except UserError as e:
            dict_response['error_found'] = e.args[0]
            return dict_response

        if res.get('detail'):
            dict_response['error_found'] = res.get('detail')
            return dict_response
        else:
            products = res.get('products')
            found = False
            if products:
                for product in products:
                    if product.get('productCode') == carrier.dhl_product_code\
                            and product.get('totalPrice'):
                        currency, price  = self._get_rate_price(product.get('totalPrice'))
                        dict_response['price'] = price
                        dict_response['currency'] = currency
                        found = True
                if not found:
                    dict_response['error_found'] = _(
                        "No shipping available for the selected DHL product")
            return dict_response

    def _send_rate_request(self, param):
        try:
            carrier = param["carrier"].sudo()
            request_query = self._create_rate_querystring(param)
            _logger.info('DHL Query %s' % request_query)
            headers = {"Content-Type": "application/json"}
            url = "{}/rates?{}".format(self.url, request_query)
            req = requests.get(url, headers=headers, auth=HTTPBasicAuth(
                carrier.dhl_username, carrier.dhl_password), timeout=60)
            # req.raise_for_status()
            res_json = req.json()
            _logger.info('DHL response %s' % res_json)
        except IOError as ex:
            _logger.exception(ex)
            raise UserError("DHL Server not found. Check your connectivity.")
        return res_json

    def _create_rate_querystring(self, param):
        ''' Create query string for rate request.
            Eg. 
            ?accountNumber=365344919
            &originCountryCode=NG
            &originPostalCode=0
            &originCityName=Abuja
            &destinationCountryCode=NG
            &destinationPostalCode=0
            &destinationCityName=umuahia
            &weight=5
            &length=15
            &width=10
            &height=5
            &plannedShippingDate=2020-12-17
            &isCustomsDeclarable=false
            &unitOfMeasurement=metric
         '''
        carrier = param["carrier"].sudo()
        query_dict = dict(
            accountNumber=carrier.dhl_account_number,
            originCountryCode=param['shipper_branch'].country_id.code or param["shipper_partner"].country_id.code,
            originPostalCode=param['shipper_branch'].zip or param["shipper_partner"].zip,
            originCityName=param['shipper_branch'].city or param["shipper_partner"].city,
            destinationCountryCode=param["recipient_partner"].country_id.code,
            destinationPostalCode=param["recipient_partner"].zip,
            destinationCityName=param["recipient_partner"].city,
            plannedShippingDate=param["Date"],
            isCustomsDeclarable=False,
            unitOfMeasurement='metric'
        )
        if param["package_ids"] and not param.get('total_packages'):
            for index, package in enumerate(param["package_ids"], start=1):
                packaging = package or carrier.dhl_default_packaging_id
                query_dict['weight'] = float_repr(package.shipping_weight, 3)
                query_dict['length'] = packaging.length
                query_dict['height'] = packaging.height
                query_dict['width'] = packaging.height
        elif param['package_ids'] and param.get('total_packages'):
            package = param['package_ids']
            for seq in range(1, param['total_packages'] + 1):
                packaging = package or carrier.dhl_default_packaging_id
                query_dict['length'] = packaging.length
                query_dict['height'] = packaging.height
                query_dict['width'] = packaging.height
                if seq == param['total_packages'] and param['last_package_weight']:
                    query_dict['weight'] = float_repr(
                        param['last_package_weight'], 3)
                else:
                    query_dict['weight'] = float_repr(package.max_weight, 3)
        else:
            packaging = carrier.dhl_default_packaging_id
            query_dict['weight'] = float_repr(param["total_weight"], 3)
            query_dict['length'] = packaging.length
            query_dict['height'] = packaging.height
            query_dict['width'] = packaging.height
        return urlencode(query_dict)

    # shipping

    def _tolocale_time(self, input_time):
        ''' This method converts UTC to current user timezone
            By default, odoo records date in UTC. 
            This is bcos odoo users can login from any place in the world 
            and thus will not be idle to save in different timezone
            odoo converts the UTC date to users timezone on the view
        '''
        try:
            ftime = input_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            local = pytz.timezone('Africa/Lagos')
            converted_date = datetime.strftime(pytz.utc.localize(datetime.strptime(ftime, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
            return fields.Datetime.from_string(converted_date)
        except Exception as ex:
            _logger.exception('DHL DATE CONVERSION ERROR %s ' % ex)

    def _get_send_param(self, picking, carrier):
        tommorrow = date_utils.add(fields.Datetime.now(), days=1)
        shipping_date = str(self._tolocale_time(tommorrow).strftime("%Y-%m-%dT%H:%M:%SZ")).replace('Z', ' GMT+01:00')
        
        return {
            # it's if you want to track the message numbers
            'MessageTime': datetime.now().isoformat(),
            'MessageReference': 'ref:' + datetime.now().isoformat(),
            'carrier': carrier,
            'RegionCode': carrier.dhl_region_code,
            'lang': 'en',
            'recipient_partner': picking.partner_id,
            'PiecesEnabled': 'Y',
            # Hard coded, S for Shipper, R for Recipient and T for Third Party
            'ShippingPaymentType': 'S',
            'recipient_streetLines': ('%s %s') % (picking.partner_id.street or '',
                                                  picking.partner_id.street2 or ''),
            'NumberOfPieces': len(picking.package_ids) or 1,
            'weight_bulk': carrier._dhl_convert_weight(picking.weight_bulk, carrier.dhl_package_weight_unit),
            'package_ids': picking.package_ids,
            'order_no': picking.origin,
            'shipping_stock': picking.move_ids_without_package, #relates to picking stock move
            'total_weight': carrier._dhl_convert_weight(picking.shipping_weight, carrier.dhl_package_weight_unit),
            'weight_unit': carrier.dhl_package_weight_unit[:1],
            'dimension_unit': carrier.dhl_package_dimension_unit[0],
            # For the rating API waits for CM and IN here for C and I...
            'dhl_product_code': carrier.dhl_product_code,
            'dhl_account': carrier.dhl_account_number,
            'Date': time.strftime('%Y-%m-%d'),
            #'yyyy-MM-dd\'T\'HH:mm:ss.SSS\'Z\''
            'shipping_date': shipping_date,  #datetime.now().isoformat(), #2021-03-17T09:54:20.269990 Expected format '2010-02-11T17:10:09 GMT+01:00')
            'shipper_partner': picking.picking_type_id.warehouse_id.partner_id,
            'shipper_company': picking.company_id,
            'shipper_branch': picking.picking_type_id.warehouse_id.branch_id,
            'shipper_streetLines': ('%s %s') % (picking.picking_type_id.warehouse_id.partner_id.street or '',
                                                picking.picking_type_id.warehouse_id.partner_id.street2 or ''),
            'LabelImageFormat': carrier.dhl_label_image_format,
            'LabelTemplate': carrier.dhl_label_template,
            'is_dutiable': carrier.dhl_dutiable,
            'currency_name': picking.sale_id.currency_id.name or picking.company_id.currency_id.name,
            'total_value': str(float_repr(sum([line.product_id.lst_price * int(line.product_uom_qty) for line in picking.move_lines]), 2))
        }

    def _get_send_param_final_rating(self, picking, carrier):
        return {
            'MessageTime': datetime.now().isoformat(),
            'MessageReference': 'ref:' + datetime.now().isoformat(),
            'carrier': carrier,
            'shipper_partner': picking.picking_type_id.warehouse_id.partner_id,
            'Date': time.strftime('%Y-%m-%d'),
            'ReadyTime': time.strftime('PT%HH%MM'),
            'recipient_partner': picking.partner_id,
            'currency_name': picking.sale_id.currency_id.name or picking.company_id.currency_id.name,
            'total_value': str(float_repr(sum([line.product_id.lst_price * int(line.product_uom_qty) for line in picking.move_lines]), 2)),
            'is_dutiable': carrier.dhl_dutiable,
            'package_ids': picking.package_ids,
            'total_weight': carrier._dhl_convert_weight(picking.weight_bulk, carrier.dhl_package_weight_unit),
        }

    def _send_shipment_request(self, payload, carrier):
        try:
            # self.debug_logger(request_dict, 'dhl_request')
            _logger.info('DHL SHIPMENT PAYLOAD %s' % payload)
            headers = {"Content-Type": "application/json"}
            url = "{}/shipments".format(self.url)
            req = requests.post(url, data=payload, headers=headers, auth=HTTPBasicAuth(carrier.dhl_username, carrier.dhl_password), timeout=60)
            # req.raise_for_status()
            res = req.json()
            # self.debug_logger(res, 'dhl_response')
            _logger.info('DHL SHIPMENT Response %s' %res)
        except Exception as ex:
            _logger.exception('DHL SHIPMENT EXCEPTION => %s' % ex)
            raise UserError("DHL Server not found. Check your connectivity.")
        return res


    def send_shipping(self, picking, carrier):
        '''
            Send Shipment Request to DHL.

            #Success Response Format:
                {
                    "shipmentTrackingNumber": "1192520512",
                    "trackingUrl": "https://express.api.dhl.com/mydhlapi/test/shipments/1192520512/tracking",
                    "packages": [
                        {
                            "referenceNumber": 1,
                            "trackingNumber": "JD011100003645597355",
                            "trackingUrl": "https://express.api.dhl.com/mydhlapi/test/shipments/1192520512/tracking?pieceTrackingNumber=JD011100003645597355"
                        }
                    ],
                    "documents": [
                        {
                            "imageFormat": "PDF",
                            "content": "base64 string",
                            "typeCode": "label"
                        }
                    ],
                    "shipmentCharges": [
                        {
                            "currencyType": "BILLC",
                            "priceCurrency": "NGN",
                            "price": 53296.35,
                            "serviceBreakdown": [
                                {
                                    "name": "EXPRESS DOMESTIC",
                                    "price": 53296.35
                                }
                            ]
                        },
                        {
                            "currencyType": "PULCL",
                            "priceCurrency": "NGN",
                            "price": 53296.35,
                            "serviceBreakdown": [
                                {
                                    "name": "EXPRESS DOMESTIC",
                                    "price": 53296.35
                                }
                            ]
                        },
                        {
                            "currencyType": "BASEC",
                            "priceCurrency": "EUR",
                            "price": 106.8,
                            "serviceBreakdown": [
                                {
                                    "name": "EXPRESS DOMESTIC",
                                    "price": 106.8
                                }
                            ]
                        }
                    ]
                }
            #Error  Response Format:
                {
                    "instance": "/expressapi/shipments",
                    "detail": "410138: Requested product(s) not available at payer, D/D ",
                    "title": "Bad request",
                    "message": "Bad request",
                    "status": "400"
                }
        '''

        dict_response = {'tracking_number': 0.0,
                         'price': 0.0,
                         'currency': False}

        param = self._get_send_param(picking, carrier)
        data = self._create_shipping_vals(param)
        payload = json.dumps(data, indent=4)
        if not data.get('content').get('packages'):
            raise UserError(_('Please put the delivery package in a PACK'))

        res = self._send_shipment_request(payload, carrier)
        
        if res.get('detail'):
            detail = '{} \n\n'.format( res.get('detail'))
            additional_detail = ''
            if res.get('additionalDetails') and type(res.get('additionalDetails')) is list:
                additional_detail = '\n'.join(res.get('additionalDetails'))
            raise UserError(_(detail + additional_detail))
        else:
            docs = res.get('documents')
            for doc in docs:
                if doc.get('typeCode') == 'label':
                    self.label = doc.get('content')
            dict_response['tracking_number'] = res.get('shipmentTrackingNumber')
            currency, price = self._get_rate_price(res.get('shipmentCharges'))
            dict_response['price'] = price
            dict_response['currency'] = currency
        return dict_response

    def save_label(self):
        label_binary_data = binascii.a2b_base64(self.label)
        return label_binary_data

    def send_cancelling(self, picking, carrier):
        dict_response = {'tracking_number': 0.0,
                         'price': 0.0, 'currency': False}
        return dict_response

    def _create_shipping_vals(self, param):
        '''
            Create shipping dict data
        '''
        carrier = param["carrier"].sudo()
        stocks_for_shipping = param['shipping_stock']
        desc = ''
        for stock in stocks_for_shipping:
            desc += 'Name: {} Quantity {}, '.format(stock.product_id.name, stock.product_uom_qty)
        # packages to be shipped
        packages = []
        # Multi-package
        for package in param["package_ids"]:
            packaging = package.packaging_id or carrier.dhl_default_packaging_id
            packages.append(
                {
                    # "typeCode": "2BP",
                    "weight": package.shipping_weight, #22.5,
                    "dimensions": {
                                "length": packaging.length, #15,
                                "width": packaging.width,
                                "height": packaging.height #40
                    },
                    "customerReferences": [
                        {
                            "value": "Customer reference",
                            "typeCode": "CU"
                        }
                    ],
                    "description": package.name
                }
            )

        return {
            # "2021-03-17T17:00:00 GMT+01:00",
            "plannedShippingDateAndTime": param['shipping_date'],
            "pickup": {
                "isRequested": False,
                "closeTime": "18:00",
                "location": "reception"
            },
            "productCode": param['dhl_product_code'],
            "localProductCode":  param['dhl_product_code'],
            "getRateEstimates": True,
            "accounts": [
                {
                    "typeCode": "shipper",
                    "number": param['dhl_account']
                }
            ],
            "customerReferences": [
                {
                    "value": "Customer reference",
                    "typeCode": "CU"
                }
            ],
            "customerDetails": {
                "shipperDetails": {
                    "postalAddress": {
                        "postalCode": param['shipper_branch'].zip or param["shipper_partner"].zip,
                        "cityName": param['shipper_branch'].city or param["shipper_partner"].city,
                        "countryCode": param['shipper_branch'].country_id.code or param["shipper_partner"].country_id.code,
                        "provinceCode": param['shipper_branch'].state_id.code or param["shipper_partner"].state_id.code,
                        "addressLine1": (param['shipper_branch'].street or param["shipper_partner"].street or ',')[:45],
                        "addressLine2": (param['shipper_branch'].street2 or param["shipper_partner"].street2 or ',')[:45],
                        "addressLine3": '.',
                        "countyName": param['shipper_branch'].state_id.name or param["shipper_partner"].state_id.name,
                    },
                    "contactInformation": {
                        "email": param['shipper_company'].email or 'support@eha.ng',
                        "phone": param['shipper_company'].phone or 'NA',
                        "mobilePhone": param['shipper_company'].phone or 'NA',
                        "companyName": (param["shipper_company"].name or '')[:35],
                        "fullName": (param["shipper_company"].name or '')[:35]
                    }
                },
                "receiverDetails": {
                    "postalAddress": {
                        "postalCode": param["recipient_partner"].zip,
                        "cityName": param["recipient_partner"].city,
                        "countryCode": param["recipient_partner"].country_id.code,
                        "provinceCode": param['recipient_partner'].state_id.code or 'na',
                        "addressLine1": (param['recipient_partner'].street or ',')[:45],
                        "addressLine2": (param['recipient_partner'].street2 or ',')[:45],
                        "addressLine3": ".",
                        "countyName": param['recipient_partner'].state_id.name
                    },
                    "contactInformation": {
                        "email": param['recipient_partner'].email or 'NA',
                        "phone": param['recipient_partner'].phone or 'NA',
                        "mobilePhone": param['recipient_partner'].phone or 'NA',
                        "companyName": param['recipient_partner'].name,
                        "fullName": param['recipient_partner'].name
                    }
                }
            },
            "content": {
                "packages": packages,
                "isCustomsDeclarable": False,
                "description": desc if desc else "My shipment description",
                "incoterm": "DAP",
                "unitOfMeasurement": "metric"
            },
            "requestOndemandDeliveryURL": False,
            "shipmentNotification": [
                {
                    "typeCode": "email",
                    "receiverId": param['recipient_partner'].email or 'support@eha.ng',
                    "languageCode": "eng",
                    "languageCountryCode": "en",
                    "bespokeMessage": "Your order {} from EHA Clinics LTD has been shipped via DHL Nigeria".format(param['order_no'])
                }
            ],
            "getOptionalInformation": False
        }

    def _get_rate_price(self, price_list):
        price = 0.00
        currency = 'NGN'
        filtered = list(filter(lambda x: x.get('currencyType')
                               == 'BILLC', price_list))
        if filtered:
            _logger.info('PRICELIST %s' % filtered)
            price = filtered[0].get('price')
            currency = filtered[0].get('priceCurrency')
        return currency, price


    def check_required_value(self, carrier, recipient, shipper, order=False, picking=False):
        carrier = carrier.sudo()
        recipient_required_field = ['city', 'zip', 'country_id']
        if not carrier.dhl_username:
            return _("DHL Username is missing, please modify your delivery method settings.")
        if not carrier.dhl_password:
            return _("DHL password is missing, please modify your delivery method settings.")
        if not carrier.dhl_account_number:
            return _("DHL account number is missing, please modify your delivery method settings.")

        if not recipient.street and not recipient.street2:
            recipient_required_field.append('street')
        res = [field for field in recipient_required_field if not recipient[field]]
        if res:
            return _("The address of the customer is missing or wrong (Missing field(s) :\n %s)") % ", ".join(res).replace("_id", "")

        shipper_required_field = ['city', 'zip', 'phone', 'country_id']
        if not shipper.street and not shipper.street2:
            shipper_required_field.append('street')

        res = [field for field in shipper_required_field if not shipper[field]]
        if res:
            return _("The address of your company warehouse is missing or wrong (Missing field(s) :\n %s)") % ", ".join(res).replace("_id", "")

        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            for line in order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type not in ['service', 'digital']):
                return _('The estimated price cannot be computed because the weight of your product is missing.')
        return False
