"""Part of odoo. See LICENSE file for full copyright and licensing details."""

import logging
import requests
from odoo import http 
from odoo.http import request#, Response, JsonRequest
import json
from odoo.exceptions import ValidationError
from datetime import datetime
from datetime import date
_logger = logging.getLogger(__name__)


class ShapShapDeliveryAPI(http.Controller):
    """."""
    @http.route(['/api/v1/delivery-status/update'], type="json", auth="public", methods=["POST", "GET"], csrf=False)
    def stock_picking_shap_update(self, **kw):
        """data = {
                "tracking_reference": 'WQEWRTREERRERRER',
                "order_status": 'draft', # Accepted type includes : [ Pending, Assigned, DriverArrived, InTransit, Delivered, DropOnCollectionPoint, CancelledByCustomer, CancelledByDriver, NoDriverFound, CancelledByAdmin ]
            }
        """

        accepted_status = [
        'Delivered', 'Pending','Assigned','DriverArrived','InTransit','CancelledByCustomer','CancelledByDriver',
        'NoDriverFound','CancelledByAdmin'
        ]
        # this is to remove the default json typed endpoints response format to normal response object 
        # request._json_response = self.alternative_json_response.__get__(request, JsonRequest)
        data = json.loads(request.httprequest.data.decode("utf8"))
        _logger.info("DELIVERY DATA %s" % json.dumps(data, indent=4))
        error_item = ["Error Found: "]
        tracking_reference = data.get('tracking_reference')
        order_status = data.get('order_status')
        
        stock_picking = request.env['stock.picking'].sudo()
        if not all([tracking_reference, order_status]):
            error_item.append('Ensure that you provide Tracking reference and order status')
        
        if order_status not in accepted_status:
            error_item.append('Ensure that the order status is in {}'.format(accepted_status))
        
        if len(error_item) > 1:
            _logger.info("VALIDATION ERROR %s" % error_item)
            return {"status": "400", "message": ',\n'.join(error_item)}
        ##### 
        try:
            status = 'delivered' if order_status == "Delivered" else order_status
            delivery_shap_shap_id = request.env.ref("delivery_shap_shap.delivery_carrier_ng_shap_shap")
            stock_picking_ref = stock_picking.search([
                ('carrier_id.id', '=', delivery_shap_shap_id.id),
                ('carrier_tracking_ref', '=', tracking_reference)
                ])
            if stock_picking_ref:
                for stockref in stock_picking_ref:
                    stockref.write({
                        'order_status': status,
                    })
                return {
                    "message": "Record successfully updated",
                    "status": "200",
                }
            else:
                return {
                    "message": "Delivery Record not found !",
                    "status": "400",
                }
        except Exception as e:
            _logger.exception(e)
            return {"message": str(e), "status": "400"}

