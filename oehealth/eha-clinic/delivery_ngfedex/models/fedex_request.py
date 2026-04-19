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


class FedexProvider():

    def __init__(self, prod_environment, debug_logger):
        self.debug_logger = debug_logger
        if not prod_environment:
            self.url = 'https://api.clicknship.com.ng'
        else:
            self.url = 'https://api.clicknship.com.ng'

    def _get_rate_param(self, order, carrier):
        res = {}
        total_weight = carrier._dhl_convert_weight(sum(
            [(line.product_id.weight * line.product_qty) for line in order.order_line]), carrier.dhl_package_weight_unit)
        max_weight = carrier._dhl_convert_weight(
            carrier.fedex_default_packaging_id.max_weight, carrier.dhl_package_weight_unit)

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
            'package_ids': False,
        }
        return res

    def get_token(self,carrier):
        try:
            headers = {"Content-Type": "application/json"}
            url = "{}/Token".format(self.url)
            payload = "username={}&password={}&grant_type={}".format(carrier.fedex_username, carrier.fedex_password,"password")
            req = requests.get(url, headers=headers,data=payload,timeout=60)
            res_json = req.json()
            _logger.info('Fedex Token response %s' % res_json)
        except IOError as ex:
            _logger.exception(ex)
            raise UserError("Invalid Request")
        if 'error' in res_json:
            raise UserError("Invalid request or username and password")    
        return res_json

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
            found = False
            if res.get('DeliveryFee'):
                currency, price = self._get_rate_price(res.get('TotalAmount'))
                dict_response['price'] = price
                dict_response['currency'] = currency
                found = True
                if not found:
                    dict_response['error_found'] = _(
                        "No shipping available for the selected Fedex product")
            return dict_response

    def _send_rate_request(self, param):
        try:
            carrier = param["carrier"].sudo()
            payload = json.dumps(self._create_rate_dict(param))
            _logger.info('Fedex Query %s' % payload)
            headers = {"Content-Type": "application/json", "Authorization": "Bearer " + carrier.fedex_token}
            url = "{}/clicknship/Operations/DeliveryFee".format(self.url)
            req = requests.post(url, headers=headers, data=payload)
            res_json = req.json()
            _logger.info('Fedex response %s' % res_json)
        except IOError as ex:
            _logger.exception(ex)
            raise UserError("Fedex Server not found. Check your connectivity.")
        return res_json[0]

    def _create_rate_dict(self, param):
        ''' Create query string for rate request.
            &origin=NG
            &destination=NG
            &weight=5
            &length=15
            &width=10
            &height=5
         '''
        carrier = param["carrier"].sudo()
        query_dict = dict(
            Origin=param['shipper_branch'].city or param["shipper_partner"].city,
            Destination=param["recipient_partner"].city,
            PickupType='1',
        )
        if param["package_ids"] and not param.get('total_packages'):
            for index, package in enumerate(param["package_ids"], start=1):
                packaging = package or carrier.fedex_default_packaging_id
                query_dict['weight'] = float_repr(package.shipping_weight, 3)
                query_dict['length'] = packaging.length
                query_dict['height'] = packaging.height
                query_dict['width'] = packaging.height
        elif param['package_ids'] and param.get('total_packages'):
            package = param['package_ids']
            for seq in range(1, param['total_packages'] + 1):
                packaging = package or carrier.fedex_default_packaging_id
                query_dict['length'] = packaging.length
                query_dict['height'] = packaging.height
                query_dict['width'] = packaging.height
                if seq == param['total_packages'] and param['last_package_weight']:
                    query_dict['weight'] = float_repr(
                        param['last_package_weight'], 3)
                else:
                    query_dict['weight'] = float_repr(package.max_weight, 3)
        else:
            packaging = carrier.fedex_default_packaging_id
            query_dict['weight'] = float_repr(param["total_weight"], 3)
            query_dict['length'] = packaging.length
            query_dict['height'] = packaging.height
            query_dict['width'] = packaging.height
        return query_dict

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
            converted_date = datetime.strftime(pytz.utc.localize(datetime.strptime(
                ftime, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
            return fields.Datetime.from_string(converted_date)
        except Exception as ex:
            _logger.exception('DHL DATE CONVERSION ERROR %s ' % ex)

    def _get_send_param(self, picking, carrier):
        tommorrow = date_utils.add(fields.Datetime.now(), days=1)
        shipping_date = str(self._tolocale_time(tommorrow).strftime(
            "%Y-%m-%dT%H:%M:%SZ")).replace('Z', ' GMT+01:00')

        fedex_payment_type = 'Pay On Delivery'
        fedex_delivery_type = 'Normal Delivery'

        #payment type in string
        if carrier.fedex_payment_type == '0':
            fedex_payment_type = 'Pay On Delivery'
        else:
            fedex_payment_type = 'Prepaid'
        
        #delivery type in string
        if carrier.fedex_delivery_type == '0':
            fedex_delivery_type = 'Normal Delivery'
        else:
            fedex_delivery_type = 'Same Day Delivery'

        return {
            'carrier': carrier,
            'descr': picking.name,
            'weight': picking.weight,
            'NumberOfPieces': len(picking.package_ids) or 1,
            'package_ids': picking.package_ids,
            'order_no': picking.origin,
            'shipping_stock': picking.move_ids_without_package,  # relates to picking stock move
            'shipping_date': shipping_date,
            'shipper_partner': picking.picking_type_id.warehouse_id.partner_id,
            'shipper_company': picking.company_id,
            'shipper_branch': picking.picking_type_id.warehouse_id.branch_id,
            'shipper_streetLines': ('%s %s') % (picking.picking_type_id.warehouse_id.partner_id.street or '',
                                                picking.picking_type_id.warehouse_id.partner_id.street2 or ''),
            'recipient_partner': picking.partner_id,
            "PaymentType": fedex_payment_type,
            "DeliveryType": fedex_delivery_type,
            "PickupType": "1",
            "ShipmentItems": [{ "ItemName": item.product_id.name,
                                "ItemUnitCost": 0,
                                "ItemQuantity": item.qty_done,
                                "ItemColour": "",
                                "ItemSize": ""
            } for item in picking.move_line_ids_without_package],
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
            'package_ids': picking.package_ids,
        }
    
    def get_latest_tracking(self,order,carrier):
        try:
            headers = {"Content-Type": "application/json",
                       "Authorization": "Bearer " + carrier.fedex_token
                       }
            url = "{}/clicknship/Operations/TrackShipment?waybillno={}".format(self.url,order.carrier_tracking_ref)
            req = requests.get(url, headers=headers,  timeout=60)
            res = req.json()
            _logger.info('Fedex SHIPMENT Response %s' % res)
        except Exception as ex:
            _logger.exception('Fedex SHIPMENT TRACK EXCEPTION => %s' % ex)
            raise UserError("Fedex Server not found. Check your connectivity.")
        return res

    def _send_shipment_request(self, payload, carrier):
        try:
            _logger.info('Fedex SHIPMENT PAYLOAD %s' % payload)
            headers = {"Content-Type": "application/json",
                       "Authorization": "Bearer " + carrier.fedex_token
                       }
            url = "{}/clicknship/Operations/PickupRequest".format(self.url)
            req = requests.post(url, data=payload, headers=headers,  timeout=60)
            res = req.json()
            _logger.info('Fedex SHIPMENT Response %s' % res)
        except Exception as ex:
            _logger.exception('Fedex SHIPMENT EXCEPTION => %s' % ex)
            raise UserError("Fedex Server not found. Check your connectivity.")

        if res.get('TransStatus',"") == 'Failed':
            raise UserError(res.get("TransStatusDetails",""))
        return res

    def send_shipping(self, picking, carrier):
        '''
            Send Shipment Request to Fedex.
        '''
        dict_response = {'tracking_number': 0.0,
                         'price': 0.0,
                         'currency': False}

        param = self._get_send_param(picking, carrier)
        data = self._create_shipping_vals(param)
        payload = json.dumps(data, indent=4)
        # if not data.get('content').get('packages'):
        #     raise UserError(_('Please put the delivery package in a PACK'))

        res = self._send_shipment_request(payload, carrier)
        if res.get('detail'):
            detail = '{} \n\n'.format(res.get('detail'))
            additional_detail = ''
            if res.get('additionalDetails') and type(res.get('additionalDetails')) is list:
                additional_detail = '\n'.join(res.get('additionalDetails'))
            raise UserError(_(detail + additional_detail))
        else:
            dict_response['tracking_number'] = res.get('WaybillNumber')
            currency, price = self._get_rate_price(res.get('TotalAmount'))
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
            desc += 'Name: {} Quantity {}, '.format(
                stock.product_id.name, stock.product_uom_qty)
        
        # Packages to be shipped
        packages = []

        # Multi-package
        for package in param["package_ids"]:
            packaging = package.packaging_id or carrier.fedex_default_packaging_id
            packages.append(
                {
                    # "typeCode": "2BP",
                    "weight": package.shipping_weight,  # 22.5,
                    "dimensions": {
                        "length": packaging.length,  # 15,
                        "width": packaging.width,
                        "height": packaging.height  # 40
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
            "OrderNo": param['order_no'],
            "SenderName": param['shipper_branch'].name or param["shipper_partner"].name,
            "SenderCity": param['shipper_branch'].city or param["shipper_partner"].city,
            "SenderAddress": (param['shipper_branch'].street or param["shipper_partner"].street or ',')[:45],
            "SenderPhone": param["shipper_partner"].phone,
            "SenderEmail": param["shipper_partner"].email,
            "RecipientName": param['recipient_partner'].name or 'NA',
            "RecipientCity": param['recipient_partner'].city or 'NA',
            "RecipientAddress": param['recipient_partner'].street or 'NA',
            "RecipientPhone": param['recipient_partner'].phone or 'NA',
            "RecipientEmail": param['recipient_partner'].email or 'NA',
            "weight": str(param["weight"] or 0),
            "PaymentType": param["PaymentType"],
            "DeliveryType": param["DeliveryType"],
            "PickupType": param["PickupType"],
            "ShipmentItems": param["ShipmentItems"],     
        }

    def _get_rate_price(self, price_list):
        price = price_list
        currency = 'NGN'
        return currency, price

    # check all the necessary details before requesting rate or sending shipments
    def check_data(self,carrier,check_state,check_city):
        try:
            headers = {"Content-Type": "application/json",
                       "Authorization": "Bearer " + carrier.fedex_token
                       }
            if check_state:
                url = "{}/clicknship/Operations/States".format(self.url)
            elif check_city:
                url = "{}/clicknship/Operations/cities".format(self.url)
            req = requests.get(url, headers=headers,  timeout=60)
            res = req.json()
            _logger.info('Fedex SHIPMENT Response %s' % res)
        except Exception as ex:
            _logger.exception('Fedex SHIPMENT TRACK EXCEPTION => %s' % ex)
            raise UserError("Fedex Server not found. Check your connectivity.")
        return res


    def check_required_value(self, carrier, recipient, shipper, order=False, picking=False):
        carrier = carrier.sudo()
        recipient_required_field = ['city', 'zip', 'country_id']
        if not carrier.fedex_token:
            return _("Fedex Token is missing, please modify your delivery method settings.")
        if not carrier.fedex_username:
            return _("Fedex Username is missing, please modify your delivery method settings.")
        if not carrier.fedex_password:
            return _("Fedex password is missing, please modify your delivery method settings.")
        if not carrier.fedex_account_number:
            return _("Fedex account number is missing, please modify your delivery method settings.")

        if not recipient.street and not recipient.street2:
            recipient_required_field.append('street')
        res = [field for field in recipient_required_field if not recipient[field]]
        if res:
            return _("The address of the customer is missing or wrong (Missing field(s) :\n %s)") % ", ".join(res).replace("_id", "")

        shipper_required_field = ['city', 'zip', 'phone', 'country_id']
        if not shipper.street and not shipper.street2:
            shipper_required_field.append('street')

        res = [field for field in shipper_required_field if not shipper[field]]

        #check if shipper and recipient state are valid for delivery
        avail_states = self.check_data(carrier,True,False)
        shipper_state = shipper.state_id and shipper.state_id.name and shipper.state_id.name.upper()
        valid_shipper_state = False
        if 'Message' in avail_states:
            return _(avail_states.get('Message','INvalid response'))
        if avail_states:
            valid_shipper_state = dict(filter(lambda avail_states: avail_states and avail_states['StateName'] == shipper_state, avail_states))
        if not valid_shipper_state:
            return _("The Provided state for shipper is invalid or unavailable")

        avail_states = self.check_data(carrier,True,False)
        recipient_state = False
        recipient_state = recipient.state_id and recipient.state_id.name and recipient.state_id.name.upper()
        if avail_states:
            valid_shipper_state = dict(filter(lambda avail_states: avail_states and avail_states['StateName'] == recipient_state, avail_states))
        if not valid_shipper_state:
            return _("The Provided state for recipient is invalid or unavailable")

        #check if shipper and recipient city are valid for delivery
        avail_city = self.check_data(carrier,False,True)
        valid_shipper_city = False
        if avail_city:
            valid_shipper_city = dict(filter(lambda avail_states: avail_states and avail_states['CityName'] == shipper.city.upper(), avail_city))
        if not valid_shipper_city:
            return _("The Provided city for shipper is invalid or unavailable")

        avail_city = self.check_data(carrier,False,True)
        if avail_city:
            valid_shipper_city = dict(filter(lambda avail_states: avail_states and avail_states['CityName'] == recipient.city.upper(), avail_city))
        if not valid_shipper_city:
            return _("The Provided city for recipient is invalid or unavailable")

        if res:
            return _("The address of your company warehouse is missing or wrong (Missing field(s) :\n %s)") % ", ".join(res).replace("_id", "")

        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            for line in order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type not in ['service', 'digital']):
                return _('The estimated price cannot be computed because the weight of your product is missing.')
        return False
