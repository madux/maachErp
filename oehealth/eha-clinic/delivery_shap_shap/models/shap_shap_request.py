# -*- coding: utf-8 -*-
import binascii
import time
from math import ceil
from datetime import datetime
import json

import requests
from requests.auth import HTTPBasicAuth

from urllib.parse import urlencode

from odoo import _, fields, http
from odoo.exceptions import UserError
from odoo.tools import float_repr, DEFAULT_SERVER_DATETIME_FORMAT, date_utils
import pytz

import logging

_logger = logging.getLogger(__name__)


class ShapShapProvider():

    def __init__(self, prod_environment, debug_logger):
        self.debug_logger = debug_logger
        if not prod_environment:
            self.url = 'https://portal.shapshap.com/api/v1/vendor'
        else:
            self.url = 'https://portal.shapshap.com/api/v1/vendor'

    def _get_rate_param(self, order, carrier):
        res = {}
        total_weight = 0
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
            'total_value': str(float_repr(sum([(line.price_unit * line.product_uom_qty) for line in
                                               order.order_line.filtered(lambda line: not line.is_delivery)]), 2)),
            'package_ids': False,
        }
        return res

    def get_token(self, carrier):
        try:
            headers = {"Content-Type": "application/json"}
            url = "{}/user/login".format(self.url)
            payload = json.dumps(
                {'email': carrier.email, 'password': carrier.password})
            req = requests.post(url, headers=headers, data=payload, timeout=60)
            res_json = req.json()
            _logger.info('Shap Shap Token response %s' % res_json)
        except IOError as ex:
            _logger.exception(ex)
            raise UserError("Invalid Request")
        if 'error' in res_json:
            raise UserError("Invalid request or api key")
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

        if not res.get('success', False):
            dict_response['error_found'] = res.get('error')
            return dict_response
        else:
            if res.get('success'):
                currency, price = self._get_rate_price(
                    res.get('data').get('estimated_fare'))
                dict_response['price'] = price
                dict_response['currency'] = currency
            return dict_response

    def _send_rate_request(self, param):
        try:
            carrier = param["carrier"].sudo()
            if 'customerAddress' in param and 'clinicAddress' in param:
                payload = {'customerAddress': param.get('customerAddress'),
                           'clinicAddress': param.get('clinicAddress'),
                           'journeyType': carrier.journeyType or 'Single'}
            else:
                payload = self._create_rate_dict(param)
            _logger.info('df Shap Shap Query %s' % payload)
            if payload and 'error' in payload:
                raise UserError(payload.get('error', 'Request Failed'))
            if not payload:
                raise UserError('Request Failed')
            """regenerate a new token anytime user tries to shop"""
            carrier.auth_get_token_shap_shap()
            headers = {"Content-Type": "application/json",
                       "authorization": "Bearer " + carrier.shap_shap_token}
            url = "{}/journey/quotation".format(self.url)
            req = requests.post(url, headers=headers, data=json.dumps(payload))
            if req.status_code == 200:
                res_json = req.json()
                _logger.info('Shap Shap response %s' % res_json)
            else:
                if req.status_code == 401:
                    msg = 'Authentication Failed'
                else:
                    res_json = req.json()
                    msg = res_json.get('error', 'Request Failed') or res_json.get(
                        'message', 'Request Failed')
                raise UserError(msg)
        except IOError as ex:
            _logger.exception(ex)
            raise UserError(
                "Shap Shap Server not found. Check your connectivity.")
        return res_json

    def get_location_lat_lon(self, param):
        sender = param.get('shipper_branch') or param.get('shipper_partner')
        receiver = param.get('recipient_partner')
        if not sender:
            return {'error': 'Sender address missing'}
        if not receiver:
            return {'error': 'Receiver address missing'}
        sender_result = http.request.env['res.partner']._geo_localize(
            sender.street, sender.zip, sender.city,
            sender.state_id.name, sender.country_id.name
        )
        receiver_result = http.request.env['res.partner']._geo_localize(
            receiver.street, receiver.zip, receiver.city,
            receiver.state_id.name, receiver.country_id.name
        )
        if not receiver_result:
            return {'error': 'We are not providing service to this area'}
        return {
            'customerAddress': {
                "lat": receiver_result[0],
                "lon": receiver_result[1],
            },
            'clinicAddress': {
                "lat": sender_result[0],
                "lon": sender_result[1],
            }
        }

    def _create_rate_dict(self, param):
        coords = self.get_location_lat_lon(param)
        carrier = param.get('carrier')
        coords.update({'journeyType': carrier.journeyType or 'Single'})
        query_dict = coords
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
            _logger.exception('Shap Shap DATE CONVERSION ERROR %s ' % ex)

    def _get_send_param(self, picking, carrier):
        tommorrow = date_utils.add(fields.Datetime.now(), days=1)
        shipping_date = str(self._tolocale_time(tommorrow).strftime(
            "%Y-%m-%dT%H:%M:%SZ")).replace('Z', ' GMT+01:00')
        shipping_params = self.get_location_lat_lon({
            'shipper_partner': picking.picking_type_id.warehouse_id.partner_id,
            'recipient_partner': picking.partner_id
        })

        if shipping_params:
            shipping_params.get('customerAddress', {}).update({
                "address": picking.partner_id._display_address(),
                "landmark": picking.partner_id.street,
                "contact_no": picking.partner_id.phone or picking.partner_id.mobile,
                "name": picking.partner_id.name
            })
            shipping_params.get('clinicAddress', {}).update({
                "address": picking.picking_type_id.warehouse_id.partner_id._display_address(),
                "landmark": picking.picking_type_id.warehouse_id.partner_id.street,
                "contact_no": picking.picking_type_id.warehouse_id.partner_id.phone or picking.picking_type_id.warehouse_id.partner_id.mobile,
                "name": picking.picking_type_id.warehouse_id.partner_id.name
            })
            shipping_params.update({
                'journeyType': carrier.journeyType or 'Single',
                "instructions": "Drive slow medicine in the parcel"
            })

        return shipping_params

    def get_latest_tracking(self, order, carrier):
        try:
            """regenerate a new token anytime user tries to shop"""
            carrier.auth_get_token_shap_shap()
            headers = {"Content-Type": "application/json",
                       "Authorization": "Bearer " + carrier.shap_shap_token
                       }
            url = "{}/clicknship/Operations/TrackShipment?waybillno={}".format(
                self.url, order.carrier_tracking_ref)
            req = requests.get(url, headers=headers, timeout=60)
            res = req.json()
            _logger.info('ShapShap SHIPMENT Response %s' % res)
        except Exception as ex:
            _logger.exception('ShapShap SHIPMENT TRACK EXCEPTION => %s' % ex)
            raise UserError(
                "ShapShap Server not found. Check your connectivity.")
        return res

    def _send_shipment_request(self, payload, carrier):
        try:
            _logger.info('Shap Shap SHIPMENT PAYLOAD %s' % payload)
            """regenerate a new token anytime user tries to shop"""
            carrier.auth_get_token_shap_shap()
            headers = {"Content-Type": "application/json",
                       "authorization": "Bearer " + carrier.shap_shap_token
                       }
            url = "{}/journey/request-journey".format(self.url)
            req = requests.post(url, data=payload,
                                headers=headers, timeout=60)
            res = req.json()
            _logger.info('Shap Shap SHIPMENT Response %s' % res)
        except Exception as ex:
            _logger.exception('Shap Shap SHIPMENT EXCEPTION => %s' % ex)
            raise UserError(
                "Shap Shap Server not found. Check your connectivity.")

        if not res.get('success', False):
            error = res.get("error", "") or res.get("message", "Failed")
            raise UserError(error)
        return res

    def send_shipping(self, picking, carrier):
        '''
            Send Shipment Request to shap shap.
        '''
        dict_response = {'tracking_number': 0.0,
                         'price': 0.0,
                         'currency': False}

        param = self._get_send_param(picking, carrier)
        param.update(
            {'carrier': carrier, 'shipping_stock': picking.move_ids_without_package})
        data = self._create_shipping_vals(param)
        param.pop('carrier')
        param.pop('shipping_stock')
        payload = json.dumps(data, indent=4)
        res = self._send_shipment_request(payload, carrier)
        param.update({'carrier': carrier})
        price_param = param.copy()
        price_param.get('customerAddress').pop('address')
        price_param.get('customerAddress').pop('landmark')
        price_param.get('customerAddress').pop('name')
        price_param.get('customerAddress').pop('contact_no')
        price_param.get('clinicAddress').pop('address')
        price_param.get('clinicAddress').pop('landmark')
        price_param.get('clinicAddress').pop('name')
        price_param.get('clinicAddress').pop('contact_no')

        price_param.pop('instructions')
        price_req = self._send_rate_request(price_param)
        if res.get('error'):
            detail = res.get('error', "")
            raise UserError(_(detail))
        else:
            dict_response['tracking_number'] = res.get(
                'data', {}).get('reference_number')
            currency, price = self._get_rate_price(
                price_req.get('data', {}).get('estimated_fare'))
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

        param.update({
            'instructions': desc
        })

        return param

    def _get_rate_price(self, price_list):
        price = price_list
        currency = 'NGN'
        return currency, price

    # check all the necessary details before requesting rate or sending shipments

    def check_required_value(self, carrier, recipient, shipper, order=False, picking=False):
        carrier = carrier.sudo()
        recipient_required_field = ['city', 'zip', 'country_id']
        if not carrier.shap_shap_token:
            return _("Shap Shap Token is missing, please modify your delivery method settings.")
        if not carrier.shap_shap_api_key:
            return _("Shap Shap API Key is missing, please modify your delivery method settings.")

        if not recipient.street and not recipient.street2:
            recipient_required_field.append('street')
        res = [field for field in recipient_required_field if not recipient[field]]
        if res:
            return _("The address of the customer is missing or wrong (Missing field(s) :\n %s)") % ", ".join(
                res).replace("_id", "")

        shipper_required_field = ['city', 'zip', 'phone', 'country_id']
        if not shipper.street and not shipper.street2:
            shipper_required_field.append('street')

        res = [field for field in shipper_required_field if not shipper[field]]
        if res:
            return _("The address of your company warehouse is missing or wrong (Missing field(s) :\n %s)") % ", ".join(
                res).replace("_id", "")
        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            # for line in order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type not in ['service', 'digital']):
            #     return _('The estimated price cannot be computed because the weight of your product is missing.')
        return False
