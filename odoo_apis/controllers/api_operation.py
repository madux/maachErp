from odoo import http
from odoo.http import request
import json
import logging
# from odoo_apis.controllers.main import validate_token
# from odoo.addons.eha_auth.controllers.helpers import validate_token, validate_secret_key, invalid_response, valid_response
import werkzeug.wrappers
from odoo import fields
from odoo.exceptions import ValidationError
import functools
from datetime import datetime

def invalid_response(typ, message=None, status=401):
    """Invalid Response
    This will be the return value whenever the server runs into an error
    either from the client or the server."""
    # return json.dumps({})
    return werkzeug.wrappers.Response(
    status=status,
    content_type="application/json; charset=utf-8",
    response=json.dumps(
        {
            "type": typ,
            "message": str(message)
            if str(message)
            else "wrong arguments (missing validation)",
        },
        default=datetime.isoformat,
    ),
)

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

class OperationController(http.Controller):
    
    def validate_token(func):
        """."""

        @functools.wraps(func)
        def wrap(self, *args, **kwargs):
            """."""
            token = request.httprequest.headers.get("token")
            if not token:
                return invalid_response(
                    "token_not_found", "please provide token in the request header", 401
                )
            access_token_data = (
                request.env["user.api.token"]
                .sudo()
                .search([("token", "=", token)], order="id DESC", limit=1)
            )
            _logger.info(f"ASCCES DATA {access_token_data} AND {token}")
            if (access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id) != token):
                return invalid_response(
                    "token", "Invalid Token", 401
                )

            request.session.uid = access_token_data.user_id.id
            request.update_env(user=access_token_data.user_id.id, context=None, su=None)
            return func(self, *args, **kwargs)
        return wrap 
    
    @validate_token
    @http.route(['/api/user/deliveries'], type="http", methods=["GET"], website=True, csrf=False, auth="none")
    def get_user_deliveries(self, **kwargs):
        '''
        data = {
            'delivery_man_id': 1, # userid
        }
        if so_number, returns the specific delivery orders of logged in user,
        '''
        try: 
            data = request.params
            user = request.env.user
            if data.get('delivery_man_id'):
                _logger.info(f"Delivery orders {request} DATA {data} VDELIVERY MAN {data.get('delivery_man_id')}")
                delivery_man_id = int(data.get('delivery_man_id')) if data.get('delivery_man_id') else 0 
                domain = [
                        ('assigned_delivery_man', '=', delivery_man_id)
                ]
            else:
                domain = [('id', '=', 0)] 
            so_order = request.env['sale.order'].sudo().search(domain)
            if so_order:
                data = []
                for prd in so_order:
                    data.append({
                        'id': prd.id, 'name': prd.name, 'assigned_delivery_man_id': prd.assigned_delivery_man.id,
                        'delivery_man_name': prd.assigned_delivery_man.name, 'amount_total': prd.amount_total,
                        'contact_id': prd.partner_id.id,'contact_name': prd.partner_id.name, 'contact_address': prd.partner_id.street,
                        'orderlines': [{
                            'id': ord.id,
                            'name': ord.name,
                            'product_id': ord.product_id.id,
                            'product_name': ord.product_id.name,
                            'product_uom_qty': ord.product_uom_qty,
                            'price_unit': ord.price_unit,
                            'sub_total': ord.price_subtotal,
                        } for ord in prd.order_line],
                        'deliveries': [{
                            'id': dv.id,
                            'name': dv.name,
                            'number': dv.origin,
                            'scheduled_date': dv.scheduled_date.strftime("%d/%m/%Y") if dv.scheduled_date else "",
                            'status': dv.state,
                            'contact_id': dv.partner_id.id,
                            'contact_name': dv.partner_id.name,
                            'contact_address': dv.partner_id.street,
                            'delivery_man_name': dv.assigned_delivery_man.name,
                            'location_destination_name': dv.location_dest_id.name,
                            'location_destination_id': dv.location_dest_id.id,
                            'source_location_name': dv.location_id.name,
                            'source_location_id': dv.location_id.id,
                            'back_order_id': True if dv.backorder_id else False,
                            'transfer_lines': [
                                {
                                    'product_id': tl.product_id.id, 
                                    'product_name': tl.product_id.name,
                                    'product_uom_qty': tl.product_uom_qty,
                                    'quantity_done': tl.quantity,
                                    'unit': tl.product_uom.name,
                                    } for tl in dv.move_ids_without_package]
                        } for dv in prd.picking_ids]
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No delivery record found for this user'})  
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
            
       
    @validate_token
    @http.route(['/api/user/sales'], type="http", methods=["GET"], website=True, csrf=False, auth="none")
    def get_user_sales(self, **kwargs):
        '''
       {
        'delivery_man_id': 1, # userid or null
        'so_number': "SO00001" or null,
        }
        if so_number, returns the specific delivery orders of logged in user,
        '''
        try: 
            # data = json.loads(request.httprequest.data) # kwargs 
            data = request.params
            user = request.env.user
            _logger.info(f"Delivery orders {request} DATA {data} VDELIVERY MAN {data.get('delivery_man_id')}")
            user_admin = request.env.user.has_group('base.group_system')
            sale_manager = request.env.user.has_group('sales_team.group_sale_manager')
            domain = ['|',
                        ('create_uid', '=', user.id), 
                        ('write_uid', '=', user.id)
                    ]
            
            if data.get('delivery_man_id'):
                delivery_man_id = int(data.get('delivery_man_id')) if data.get('delivery_man_id') else 0 
                domain = [
                    '|', '|',
                        ('create_uid', '=', user.id), 
                        ('write_uid', '=', user.id),
                        ('assigned_delivery_man', '=', delivery_man_id)
                    ]
            if data.get('so_number'):
                domain = [('name', '=', data.get('so_number'))] + domain
                
            so_order = request.env['sale.order'].sudo().search(domain)
            if not so_order:
                if user_admin or sale_manager:
                    domain = []
            so_order = request.env['sale.order'].sudo().search(domain)
            if so_order:
                data = []
                for prd in so_order:
                    data.append({
                        'id': prd.id, 'name': prd.name, 'assigned_delivery_man_id': prd.assigned_delivery_man.id,
                        'delivery_man_name': prd.assigned_delivery_man.name, 'amount_total': prd.amount_total,
                        'contact_id': prd.partner_id.id,'contact_name': prd.partner_id.name, 'contact_address': prd.partner_id.street,  
                        'invoice_number': prd.invoice_ids[0].name if prd.invoice_ids else '',
                        'invoice_id': prd.invoice_ids[0].id if prd.invoice_ids else '',
                        'orderlines': [{
                            'id': ord.id,
                            'name': ord.name,
                            'product_id': ord.product_id.id,
                            'product_name': ord.product_id.name,
                            'product_uom_qty': ord.product_uom_qty,
                            'price_unit': ord.price_unit,
                            
                            
                            'sub_total': ord.price_subtotal,
                        } for ord in prd.order_line],
                        'deliveries': [{
                            'id': dv.id,
                            'name': dv.name,
                            'number': dv.origin,
                            'scheduled_date': dv.scheduled_date.strftime("%d/%m/%Y") if dv.scheduled_date else "",
                            'status': dv.state,
                            'delivery_man_name': dv.assigned_delivery_man.name,
                            'location_destination_name': dv.location_dest_id.name,
                            'location_destination_id': dv.location_dest_id.id,
                            'source_location_name': dv.location_id.name,
                            'source_location_id': dv.location_id.id,
                            'contact_id': prd.partner_id.id, 'contact_name': prd.partner_id.name, 'contact_address': prd.partner_id.street or '',
                            'back_order_id': True if dv.backorder_id else False,
                            'transfer_lines': [
                                {
                                    'product_id': tl.product_id.id, 
                                    'product_name': tl.product_id.name,
                                    'product_uom_qty': tl.product_uom_qty,
                                    'quantity_done': tl.quantity,
                                    'unit': tl.product_uom.name,
                                    } for tl in dv.move_ids_without_package]
                        } for dv in prd.picking_ids]
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No delivery record found for this user'})  
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
            
     