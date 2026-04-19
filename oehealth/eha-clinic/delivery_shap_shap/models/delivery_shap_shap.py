# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from .shap_shap_request import ShapShapProvider

from odoo import models, fields, _
import logging
_logger = logging.getLogger(__name__)


class DeliveryShapShapProvider(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('ng_shap_shap', "Shap Shao Nigeria")],ondelete={'ng_shap_shap': lambda recs: recs.write({
            'delivery_type': 'fixed', 'fixed_price': 0})})
    shap_shap_token = fields.Char(
        string="Shap Shap Token", groups="base.group_system")
    shap_shap_api_key = fields.Char(
        string="Shap Shap API Key", groups="base.group_system")
    shap_shap_package_dimension_unit = fields.Selection([('IN', 'Inches'),
                                                         ('CM', 'Centimeters')],
                                                        default='CM',
                                                        string='Package Dimension Unit')
    shap_shap_package_weight_unit = fields.Selection([('LB', 'Pounds'),
                                                      ('KG', 'Kilograms')],
                                                     default='KG',
                                                     string="Package Weight Unit")

    shap_shap_default_packaging_id = fields.Many2one(
        'stock.package.type', string='Shap Shap Default Packaging Type')

    shap_shap_region_code = fields.Selection([('AP', 'Asia Pacific'),
                                              ('AM', 'America'),
                                              ('EU', 'Europe')],
                                             default='AM',
                                             string='Region')
    journeyType = fields.Selection([('Single', 'Single'),
                                    ('Round', 'Round')],
                                   default='Single',
                                   string='Journey Type')
    email = fields.Char(string='Email')
    password = fields.Char(string='Password')

    def auth_get_token_shap_shap(self):
        srm = ShapShapProvider(self.prod_environment, self.log_xml)
        res = srm.get_token(self)
        _logger.info(
            f"HERE IS SHAP SHAP TOKEN === {res.get('data').get('token')}")
        if res and res.get('success', '') and res.get('data'):
            # self.shap_shap_token = res.get('data').get('token')
            res_token_list = res.get('data').get('token').split(" ")
            self.shap_shap_token = res_token_list[-1]
        else:
            raise UserError("Invalid Request")

    def ng_shap_shap_track_shipment(self, order):
        srm = ShapShapProvider(self.prod_environment, self.log_xml)
        res = srm.get_latest_tracking(order, self)
        if res:
            return res
        else:
            return {}

    def ng_shap_shap_rate_shipment(self, order):
        srm = ShapShapProvider(self.prod_environment, self.log_xml)
        check_value = srm.check_required_value(self, order.partner_shipping_id, order.warehouse_id.partner_id,
                                               order=order)
        if check_value:
            return {'success': False,
                    'price': 0.0,
                    'error_message': check_value,
                    'warning_message': False}

        result = srm.rate_request(order, self)
        if result['error_found']:
            return {'success': False,
                    'price': 0.0,
                    'error_message': result['error_found'],
                    'warning_message': False}

        if order.currency_id.name == result['currency']:
            price = float(result['price'])
        else:
            quote_currency = self.env['res.currency'].search(
                [('name', '=', result['currency'])], limit=1)
            price = quote_currency._convert(float(result['price']), order.currency_id, order.company_id,
                                            order.date_order or fields.Date.today())

        return {'success': True,
                'price': price,
                'error_message': False,
                'warning_message': False}

    def ng_shap_shap_send_shipping(self, pickings):
        res = []

        srm = ShapShapProvider(self.prod_environment, self.log_xml)
        for picking in pickings:
            shipping = srm.send_shipping(picking, self)
            order = picking.sale_id
            company = order.company_id or picking.company_id or self.env.user.company_id
            order_currency = picking.sale_id.currency_id or picking.company_id.currency_id
            if order_currency.name == shipping['currency']:
                carrier_price = float(shipping.get('price', 0))
            else:
                quote_currency = self.env['res.currency'].search(
                    [('name', '=', shipping['currency'])], limit=1)
                carrier_price = quote_currency._convert(float(shipping['price'].replace(',', '')), order_currency,
                                                        company, order.date_order or fields.Date.today())
            carrier_tracking_ref = shipping['tracking_number']
            logmessage = (
                _("Shipment created into ShapShap <br/> <b>Tracking Number : </b>%s") % (carrier_tracking_ref))
            picking.message_post(body=logmessage)
            shipping_data = {
                'exact_price': carrier_price,
                'tracking_number': carrier_tracking_ref
            }
            res = res + [shipping_data]

        return res

    def ng_shap_shap_get_tracking_link(self, picking):
        '''
        Return Shap Shap tracking URL
        'https://api.clicknship.com.ng/clicknship/Operations/TrackShipment?waybillno=%s' % picking.carrier_tracking_ref
        '''
        return "https://api.clicknship.com.ng/clicknship/Operations/TrackShipment?waybillno=%s" % picking.carrier_tracking_ref

    def ng_shap_shap_cancel_shipment(self, picking):
        # Obviously you need a pick up date to delete SHIPMENT by Shap Shap. So you can't do it if you didn't schedule a pick-up.
        picking.message_post(
            body=_(u"You can't cancel Shap Shap shipping without pickup date."))
        picking.write({'carrier_tracking_ref': '',
                       'carrier_price': 0.0})

    def _ng_shap_shap_convert_weight(self, weight, unit):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter(
        )
        if unit == 'LB':
            return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_lb'), round=False)
        else:
            return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'), round=False)
