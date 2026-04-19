from odoo import http
from odoo.http import request
import json
import logging
# from odoo.addons.eha_auth.controllers.helpers import validate_token, validate_secret_key, invalid_response, valid_response
import werkzeug.wrappers
from odoo import fields
from odoo.exceptions import ValidationError
import functools
from datetime import datetime,date,timedelta

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

class SalesManController(http.Controller):

    # logging.basicConfig(level=logging.INFO)
    # _logger = logging.getLogger(__name__)
    # class EmailAPI(http.Controller):
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
    
    @http.route('/api/send_email', type='json', auth='public', methods=['POST'], csrf=False)
    def send_email(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            recipient_email = data.get('recipient_email')
            subject = data.get('subject')
            body = data.get('body')
            if not all([recipient_email, subject, body]):
                return {'success': False, 'message': 'Missing required fields'}
            mail_values = {
                'email_to': recipient_email,
                'subject': subject,
                'body_html': body,
                'auto_delete': True,
            }
            mail = request.env['mail.mail'].sudo().create(mail_values)
            mail.send()
            return {'success': True, 'message': 'Email sent successfully'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
        
     
    ##### odoo artifacts ########
    @http.route('/api/inv', type='json', auth='none', methods=['POST', 'GET'], csrf=False, website=True)
    def validate_inv(self, **kwargs):
        data = json.loads(request.httprequest.data.decode("utf8"))
        inv = request.env['account.move'].sudo().search([
            '|', ('name', '=', data.get('invoice_number')), 
            ('id', '=', data.get('invoice_id'))], limit=1)
        _logger.info(f"INVOICES => {inv}")
        
    @http.route('/api/v1/inv', type='json', auth='none', methods=['POST', 'GET'], csrf=False, website=True)
    def validate_invoice_api(self, **kwargs):
        
        '''url = "http://localhost:8069/api/v1/invoice-validation"
        User must provide either invoice_number or invoice_id
        payload = {
            "invoice_number": "INV/2024/00001",
            "invoice_id": 2, # 
            "is_register_payment": True or False, # 
            "journal_id": Null or Not Null, Not null if is_register_payment is True# 
        }'''
        # data = json.loads(request.httprequest.data)
        # data = request.params
        data = json.loads(request.httprequest.data.decode("utf8"))
        _logger.info(f"Data is {data}")
        
        invoice_number = data.get('invoice_number')
        invoice_id = int(data.get('invoice_id')) if data.get('invoice_id') else False
        journal_id = int(data.get('journal_id')) if data.get('journal_id') else False
        is_register_payment = data.get('is_register_payment')
        if not invoice_number or not invoice_id: 
            json.dumps({
                    'success': False, 
                    'data': {},
                    'message': 'Please provide invoice id or invoice number'
                })
        journalid = None
        if is_register_payment:
            if not journal_id:
                json.dumps({
                    'success': False, 
                    'data': {},
                    'message': 'Please add a valid journal id'
                })
            journal = request.env['account.journal'].sudo().search([('id', '=', int(journal_id))], limit=1)
            if not journal:
                json.dumps({
                    'success': False, 
                    'data': {},
                    'message': 'No journal found'
                })
            journalid = journal.id
        inv = request.env['account.move'].sudo().search([
            '|', ('name', '=', invoice_number), 
            ('id', '=', invoice_id)], limit=1)
        _logger.info(f"Data INVOICE is {inv}")
        
        if inv:
            if inv.state == "draft":
                _logger.info(f"bolo {inv}")
                
                # inv.action_post()
                inv.action_post()
                # inv.message_post(body='Invoice Generated from api',
                #               message_type='comment',
                #               subtype_xmlid='mail.mt_note',
                #               author_id=request.env.user.partner_id.id)
        
            payment = None
            # journalid = request.env['account.journal'].sudo().browse([8])
            # _logger.info(f"Data JOURNAL INV TO VALIDATE is {journalid}")
            # if is_register_payment:
            
                # payment = self.validate_invoice_and_post_journal(journalid, inv)
                
            # else:
            return json.dumps({
            'success': True, 
            'message': 'Successfully generated',
            'data': {'invoice_id': inv.id, 'invoice_number': inv.name}
            })
        else:
            return json.dumps({
                    'success': False, 
                    'data': {},
                    'message': 'No invoice found'
                    }) 
            
    # @http.route('/api/get-product', type='json', auth='none', methods=['GET'], csrf=False)
    @validate_token
    @http.route(['/api/get-product'], type="http", methods=["GET"], website=True, csrf=False, auth="none")
    def get_products(self, **kwargs):
        '''
        {'params': {
                'product_id': 1 or null
            }
        }
        if product id, returns the specific product by id else returns all products
        '''
        try: 
            # req_data = json.loads(request.httprequest.data) # kwargs 
            data = request.params
            product_id = int(data.get('product_id')) if data.get('product_id') else False 
            _logger.info(f"KWARGS {kwargs} DATA {data} VALUE OF PRODUCT IS {data.get('product_id')} and type {type(data)} {data.keys()}")
            # if product_id and type(product_id) != int:
            #     return invalid_response(
            #         "Product id",
            #         "Product ID provided must be an integer"
            #         "[product_id]",
            #         400,
            #     )
            domain = [('id', '=', product_id)] if product_id else []
            products = request.env['product.product'].sudo().search(domain)
            if products:
                data = []
                for prd in products:
                    data.append({
                        'id': prd.id, 'name': prd.name, 'sale_price': prd.list_price,
                        'image': f'/web/image/product.product/{prd.id}/image_512',
                        'product_uom': request.env.ref('uom.product_uom_categ_unit').id,
                        'taxes': [{
                            'id': tx.id,
                            'name': tx.name,
                            'value': tx.amount,
                            'tax_type': tx.amount_type, # e.g percent, fixed
                        } for tx in prd.taxes_id]
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No product found'})  
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
    
    @validate_token  
    @http.route('/api/get-product-availability', type='http', auth='none', methods=['GET'], csrf=False,  website=True)
    def get_product_availability(self, **kwargs):
        '''
        {
            'product_id': 10,
            'requesting_qty': 2, # pass the requesting quantity
        }
        if product id, returns the specific product quantities based on the user company warehouse
        '''
        _logger.info(f"TESTTINGN {request.params}") 
        try:
            # req_data = json.loads(request.httprequest.data) # kwargs
            data = request.params # kwargs# req_data.get('params')
            
            _logger.info(f" PROFDUCEUS ==> {data} ==>>")
            
            product_id = int(data.get('product_id')) if data.get('product_id') else False
            qty = int(data.get('requesting_qty'))
            _logger.info(f" TRYINGGGGGGGGGGGGE ==> {data} ==>> QTY {qty} ===> PRODUCT TYPE {type(product_id)}")
            # if product_id and type(product_id) not in ['int', int]:
            #     _logger.info(f" PRODUCT TYPE IS type(f'{type(product_id)}")
            #     return json.dumps({
            #             "success": False,
            #             "data": {},
            #             "message": "Wrong Product id format sent", 
            #             })
            domain = [('active', '=', True),('id', '=', product_id)]
            product = request.env['product.product'].sudo().search(domain, limit=1)
            if product:
                warehouse_domain = [('company_id', '=', request.env.user.company_id.id)]
                warehouse_location_id = request.env['stock.warehouse'].sudo().search(warehouse_domain, limit=1)
                stock_location_id = warehouse_location_id.lot_stock_id
                # should_bypass_reservation : False
                if product.detailed_type in ['product']:
                    total_availability = request.env['stock.quant'].sudo()._get_available_quantity(product, stock_location_id, allow_negative=False) or 0.0
                    product_qty = float(qty) if qty else 0
                    if product_qty > total_availability:
                        return json.dumps({
                            "success": False,
                            "data": {'total_quantity': total_availability},
                            "message": f"Selected product quantity ({product_qty}) is higher than the Available Quantity. Available quantity is {total_availability}", 
                            })
                    else:
                        return json.dumps({
                            "status": True,
                            "message": "The requesting quantity of Product is available", 
                        })
                else:
                    return json.dumps({
                        "status": False,
                        "message": "Product selected for check must be a storable product and not service", 
                        })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No product found'})  
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)
                    })
            
    @validate_token
    @http.route(['/api/get-available-drivers'], type="http", methods=["GET"], website=True, csrf=False, auth="none")
    def get_available_products(self, **kwargs):
        """
        Returns list of all available drivers
        Payload: 
        
        DRIVER_DATA = {
        "id": None,
        }
        """
        try: 
            data = request.params
            _logger.info(f"Returning all drivers available")
            domain = [('is_delivery_person', '=', True),('is_available', '=', True)]
            driver_id = data.get('id')
            _logger.info(f"GETTING USERS drivers {driver_id} and {domain} // {type(driver_id)}") 
            if driver_id:
                # type(driver_id) not in [int,float]
                if not driver_id.isdigit() or driver_id in ['False', False, 'None']:
                    return json.dumps({
                    'success': False,
                    'message': 'id must be of type integer or none'
                    })
                domain.append(('id', '=',  int(data.get('id'))))
            delivery_men = request.env['res.users'].sudo().search(domain)
            if delivery_men:
                data = []
                for usr in delivery_men:
                    data.append({
                        'id': usr.id, 'name': usr.name, 'phone': usr.phone or usr.partner_id.phone,
                        'email': usr.email, 'email2': usr.partner_id.email, 'mobile': usr.partner_id.mobile,
                        'image': f'/web/image/res.users/{usr.id}/image_1920',
                    })
                return json.dumps({
                    'success': True, 
                    'data':data,
                    'message': 'All partner record retrieved'
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No user found as a delivery person'
                    })  
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
        
    @validate_token    
    @http.route('/api/get-branch', type='http', auth='none', methods=['GET'], csrf=False, website=True)
    def get_branch(self, **kwargs):
        '''
        {'params':{
            'branch_id': 1 or null
        }
        if product id, returns the specific product by id else returns all products
        '''
        try:
            # req_data = json.loads(request.httprequest.data) # kwargs
            # data = json.loads(request.httprequest.data) # kwargs 
            data = request.params # req_data.get('params')
            branch_id = int(data.get('branch_id')) if data.get('branch_id') else False
            # if branch_id and type(branch_id) != int:
                # return invalid_response(
                #     "branch id",
                #     "branch ID provided must be an integer"
                #     "[branch_id]",
                #     400,
                # )
            domain = [('id', '=', branch_id)] if branch_id else []
            branch = request.env['multi.branch'].sudo().search(domain)
            if branch:
                data = []
                for prd in branch:
                    data.append({
                        'id': prd.id, 'name': prd.name
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No branch found'})
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
            
    @validate_token
    @http.route('/api/delivery/acknowledge', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def get_contacts(self, **kwargs): 
        '''
        headers = {
            'Content-Type': 'application/json', # use if type of request is json
            'token': 'token_sasdd7e6ca6e3793e40bd6171429de6f8686ac6cd',
            #'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
             # use if type of request is http
            #'Cookie': 'session_id=3cc87cdab877e01940c841e98e337bf291c180c1',
                }
        # {'params': {
            {
            'stock_id': 1 or null,
            'stock_number': 1 or null,
            'note': "i have acknowledged it",
        }
        # }
        if stock id, use the stock id to send the data as acknowledged
        '''
        try:
            # req_data = json.loads(request.httprequest.data) # kwargs 
            # data = req_data.get('params')
            data = request.params # stock_id, stock_number, note
            stock_id = int(data.get('stock_id')) if data.get('stock_id') else False
            stock_number = data.get('stock_number')
            note = data.get('note')
            
            domain = ['|', ('id', '=', stock_id), ('name', '=', stock_number)] if stock_id or stock_number else [('id', '=', 0)]
            stock = request.env['stock.picking'].sudo().search(domain)
            if (not stock): 
                return json.dumps({
                'success': False, 
                'message': 'Please provide a valid stock id or stock number'
                })
            else:
                acknowledge_val = {
                    'acknowledge_note': note, 
                    'is_acknowledge': True,
                }
                stock_val = request.env['stock.picking'].sudo().write(acknowledge_val)
                return json.dumps({
                    'success': True, 
                    'data': stock.name
                    })
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)
            })
    
    @validate_token
    @http.route('/api/contact-operation', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def get_contacts(self, **kwargs): 
        '''
        headers = {
            'Content-Type': 'application/json', # use if type of request is json
            'token': 'token_sasdd7e6ca6e3793e40bd6171429de6f8686ac6cd',
            #'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
             # use if type of request is http
            #'Cookie': 'session_id=3cc87cdab877e01940c841e98e337bf291c180c1',
                }
        # {'params': {
            {
            'contact_id': 1 or null,
            'contact_name': Moses Abraham or null,
            'id': cnt.id, 
            'to_create_contact': True, # (creates a new contact if contact id or name is not found), 
            'contact_name': 'peter Maduka Sopulu' or None, 
            'address1': 'No. 45 Maduka Sopulu Street'
            'address2': 'No. 46 Maduka Sopulu Street'
            'phone': '09092998888',
            'email': 'maduka@gmail.com',
        }
        # }
        if contact id, returns the specific contact by id else returns all contacts
        '''
        try:
            # req_data = json.loads(request.httprequest.data) # kwargs
            
            # data = req_data.get('params')
            data = request.params
            contact_id = int(data.get('contact_id')) if data.get('contact_id') else False
            address1 = data.get('address1')
            address2 = data.get('address2')
            phone = data.get('phone')
            email = data.get('email')
            contact_name = data.get('contact_name')
            to_create_contact = data.get('to_create_contact')
            # if contact_id and type(contact_id) != int:
            #     return invalid_response(
            #         "contact id",
            #         "contact ID provided must be an integer"
            #         "[contact_id]",
            #         400,
            #     )
            domain = ['|', ('id', '=', contact_id), ('name', '=', contact_name)] if contact_id or contact_name else []
            contact = request.env['res.partner'].sudo().search(domain)
            address = address1 or address2
            if (not contact) and to_create_contact:
                if not contact_name or not address or not phone or not email:
                    return json.dumps({
                    'success': False, 
                    'message': 'Please provide the following fields; contact name, address, phone and email'
                    })
                contact_vals = {
                    'name': contact_name, 
                    'street': address1, 
                    'street2': address2,
                    'phone': phone,
                    'email': email,
                }
                contact = request.env['res.partner'].sudo().create(contact_vals)
            if contact:
                data = []
                for cnt in contact:
                    data.append({
                        'id': cnt.id, 
                        'contact_name': cnt.name or None, 
                        'address1': cnt.street or None, 
                        'address2': cnt.street2 or None,
                        'phone': cnt.phone or None,
                        'email': cnt.email or None,
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No contact found on the system'}) 
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)})
            
    @validate_token   
    @http.route('/api/get-users', type='http', auth='none', methods=['GET'], csrf=False)
    def get_users(self, **kwargs):
        '''
        {'params': {
            'user_id': 1 or null
            'user_name': Moses Abraham or null
        }}
        if user id or user name, returns the specific contact by id  or name else returns all contacts
        '''
        try:
            # req_data = json.loads(request.httprequest.data) # kwargs 
            # data = req_data.get('params')
            data = request.params
            user_id = int(data.get('user_id')) if data.get('user_id') else False
            user_name = data.get('user_name')
            if not user_id:
                return json.dumps({'success': False,  'message': 'No user found on the system'})
            domain = ['|', ('id', '=', user_id), ('name', '=', user_name)] if user_id or user_name else []
            users = request.env['res.users'].sudo().search(domain)
            if users:
                data = []
                for usr in users:
                    data.append({
                        'id': usr.id, 
                        'user_name': usr.name or None,
                    })
                return json.dumps({
                    'success': True, 
                    'data':data
                    })
            else:
                return json.dumps({
                    'success': False, 
                    'message': 'No user found on the system'})
        
        except Exception as e:
            return json.dumps({
                    'success': False, 
                    'message': str(e)}) 
            
    @validate_token   
    @http.route('/api/get/invoice', type='http', auth='none', methods=['GET'], csrf=False)
    def api_get_invoice(self, **kwargs):
        ''''''
        # data = json.loads(request.httprequest.data.decode("utf8"))
        data = request.params 
        _logger.info(f"TESTTINGN {data}") 
        
        '''
        headers = {
            'Content-Type': 'application/json',
            'token': 'token_sasdd7e6ca6e3793e40bd6171429de6f8686ac6cd',
            #'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    #'Cookie': 'session_id=3cc87cdab877e01940c841e98e337bf291c180c1',
                        }
        INV = {
                "invoice_id": '1', # USE IF YOU WANT TO GET THE INVOICE NUMBER USING ID REFERENCE FROM THE BACKEND
                "invoice_number": 'INV/A00/1233', # USE EITHER INVOICE NUMBER TO GET THE INVOICE NUMBER DIRECTLY
                "so_number": False, # TO BE USED IF YOU WANT TO CALL USING SO_NUMBER ONLY, IT RETURNS ALL INVOICES RELATED TO THE SALE ORDER,
                 "partner_id": "1" # 'RETURNS ALL THE INVOICES RELATED TO THIS PARTNER',
                }
            url3 = "http://127.0.0.1:8080/api/get/invoice"
            req = rq.get(url3, headers=headers, json=INV)
        '''
        invoice_id = int(data.get('invoice_id')) if data.get('invoice_id') else False
        partner_id = int(data.get('partner_id')) if data.get('partner_id') else False
        so_number = data.get('so_number')
        invoice_number = data.get('invoice_number')

        if invoice_number or invoice_id or so_number:
            inv = request.env['account.move'].sudo().search([
                '|', ('id', '=', invoice_id),
                ('name', '=', invoice_number)
            ], limit=1)
            if inv:
                order_data = {
                'id': inv.id,
                'name': inv.name,
                'partner_id': inv.partner_id.id,
                'partner_name': inv.partner_id.name,
                'date_order': inv.invoice_date.strftime('%Y-%m-%d %H:%M:%S') if inv.invoice_date else '',
                'invoice_line_ids': [{
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'account_id': line.account_id.id,
                    'account_name': line.account_id.name,
                    'product_uom_id': line.product_uom_id.id,
                    'product_uom_name': line.product_uom_id.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                    'taxes': [{
                            'id': tx.id,
                            'name': tx.name,
                            'value': tx.amount,
                            'tax_type': tx.amount_type, # e.g percent, fixed
                        } for tx in line.tax_ids]
                    } for line in inv.invoice_line_ids]
                }
                return json.dumps({'success': True, 'result': order_data})
        
        
            elif so_number or partner_id:
                so_order = request.env['sale.order'].sudo().search([
                '|', ('name', '=', so_number),
                ('partner_id', '=', partner_id),
                ], limit=1)

                if not so_order:
                    return json.dumps({'success': False, 'message': 'No invoice found for this sale order nummber or partner id provided'})
        
                order_data = [{
                    'id': inv.id,
                    'name': inv.name,
                    'partner_id': inv.partner_id.id,
                    'partner_name': inv.partner_id.name,
                    'date_order': inv.invoice_date.strftime('%Y-%m-%d %H:%M:%S') if inv.invoice_date else '',
                    'invoice_line_ids': [{
                        'product_id': line.product_id.id,
                        'product_name': line.product_id.name,
                        'account_id': line.account_id.id,
                        'account_name': line.account_id.name,
                        'product_uom_id': line.product_uom_id.id,
                        'product_uom_name': line.product_uom_id.name,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                        'price_subtotal': line.price_subtotal,
                        'taxes': [{
                                'id': tx.id,
                                'name': tx.name,
                                'value': tx.amount,
                                'tax_type': tx.amount_type, # e.g percent, fixed
                            } for tx in line.tax_ids]
                    } for line in inv.invoice_line_ids]
                } for inv in so_order.invoice_ids]
                return json.dumps({'success': True, 'result': order_data})
            else:
                return json.dumps({'success': False, 'message': 'No invoice found with this id or invoice or sale order nummber provided'})
        else:
            invoices = request.env['account.move'].sudo().search([])
            order_data = [{
            'id': inv.id,
            'name': inv.name,
            'partner_id': inv.partner_id.id,
            'partner_name': inv.partner_id.name,
            'date_order': inv.invoice_date.strftime('%Y-%m-%d %H:%M:%S') if inv.invoice_date else '',
            'invoice_line_ids': [{
                'product_id': line.product_id.id,
                'product_name': line.product_id.name,
                'account_id': line.account_id.id,
                'account_name': line.account_id.name,
                'product_uom_id': line.product_uom_id.id,
                'product_uom_name': line.product_uom_id.name,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'taxes': [{
                        'id': tx.id,
                        'name': tx.name,
                        'value': tx.amount,
                        'tax_type': tx.amount_type, # e.g percent, fixed
                    } for tx in line.tax_ids]
                } for line in inv.invoice_line_ids]
            } for inv in invoices]
            return json.dumps({'success': True, 'result': order_data})
            
    @validate_token   
    @http.route('/api/sales_order/operation', type='http', auth='none', methods=['POST', 'GET'], csrf=False)
    def handle_sales_operations(self, **kwargs):
        ''''''
        data = json.loads(request.httprequest.data.decode("utf8"))
         
        # req_data = json.loads(request.httprequest.data) # kwargs
        # req_data = json.loads(request.params) # kwargs
        # data = request.params
        '''
        headers = {
            'Content-Type': 'application/json',
            'token': 'token_sasdd7e6ca6e3793e40bd6171429de6f8686ac6cd',
            #'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    #'Cookie': 'session_id=3cc87cdab877e01940c841e98e337bf291c180c1',
                        }
        SALES = {
                "partner_id": "1",
                "operation": "create",
                "company_id": "1",
                "so_number": False,
                "order_id": False,
                "order_lines":
                    [{"product_id": 4, "price_unit": 8500, "product_uom_qty": 4}]
                }
            url3 = "http://127.0.0.1:8080/api/sales_order/operation"
            req = rq.get(url3, headers=headers, json=SALES)
        '''
        
        # try:
        if data.get('operation') == 'create':
            return self._create_sales_order(data)
              
             
        elif data.get('operation') == 'update':
            return self._update_sales_order(data)
        elif data.get('operation') == 'get':
            return self._get_sales_order(data)
        else:
            return json.dumps(
                {'success': False, 
                    'message': 'Ensure that the operation data contains create, update, or get'}
                )  
        
        # except Exception as e:
        #     return json.dumps({'error': str(e)})
        
        
        
    def _create_sales_order(self, data):
        '''where data is equal to the sent payload'''
        partner_id = int(data.get('partner_id')) if data.get('partner_id') else False
        order_lines = data.get('order_lines')
        company_id = int(data.get('company_id')) if data.get('company_id') else 1
        _logger.info(f"Data is {data}")
        _logger.info(f".....Partner_id: {partner_id}, Order Lines: {order_lines} and Company ID: {company_id}.....")
        
        if not partner_id or not order_lines:
            return json.dumps(
                    {'success': False, 
                     'message': 'missing parameter such as partnerid, or orderlines not provided'}
                    )
        order_vals = {
            'partner_id': partner_id,
            'company_id': company_id,
            'order_line': [(0, 0, line) for line in order_lines]
        }
        _logger.info(f"Data XXX is {data}")
        order = request.env['sale.order'].sudo().create(order_vals)
        order.action_confirm()
        inv = order.sudo()._create_invoices()[0]
        return json.dumps({
            'success': True, 
            'data': {
                'so_id': order.id, 'so_id': order.name,
            'invoice_id': inv.id,'invoice_number': inv.name,
            }
            })
    
    def generate_stock_transfer(self, user, **kwargs):
        '''params: kwargs = DELIVERY_TRANSFER = {
                "partner_id": 2,
                "so_id": 2,
                "picking_id": 4,
                "picking_number": "WHOOL/0001",
                "delivery_man_id": "3",
                "order_delivery_status": "progress",
                "so_number": "SO0004",
                "item_ids":
                    [{"name": "S0Q003", "product_id": 4, "location_id": 1, "location_dest_id": 5, "product_uom_qty": 4}]
                }'''
        stock_picking_type_out = request.env.ref('stock.picking_type_out')
        stock_picking = request.env['stock.picking']
        saleOrder = request.env['sale.order']
        picking_so_order = None
        data = kwargs.get('dict_data')
        so_id = data.get('so_id')
        so_number = data.get('so_number')
        picking_id = data.get('picking_id', None)
        delivery_man_id = data.get('delivery_man_id')
        picking_number = data.get('picking_number')
        order_delivery_status = data.get('order_delivery_status')
        partner_id = data.get('partner_id')
        item_ids = data.get('item_ids')
        so_order = saleOrder.search(['|', ('id', '=', so_id), ('name', '=', so_number)], limit=1)
        if so_order and so_order.picking_ids:
            picking_so_order = so_order.picking_ids[0]
        elif picking_number or picking_id:
            existing_picking = stock_picking.search(['|', ('id', '=', picking_id), ('name', '=', picking_number)], limit=1)
            if existing_picking:
                picking_so_order = existing_picking
        
        if not picking_so_order:
            # user = request.env.user
            warehouse_location_id = request.env['stock.warehouse'].search([
                ('company_id', '=', user.company_id.id) 
            ], limit=1)
            destination_location_id = request.env.ref('stock.stock_location_customers')
            vals = {
                'scheduled_date': fields.Date.today(),
                'picking_type_id': stock_picking_type_out.id,
                'origin': so_number,
                'assigned_delivery_man': delivery_man_id,
                'partner_id': partner_id,
                'order_delivery_status': order_delivery_status,
                'move_ids_without_package': [(0, 0, {
                                'name': so_number, 
                                'picking_type_id': stock_picking_type_out.id,
                                'location_id': stock_picking_type_out.default_location_src_id.id or warehouse_location_id.lot_stock_id.id,
                                'location_dest_id': stock_picking_type_out.default_location_dest_id.id or destination_location_id.id,
                                'product_id': mm.get('product_id'),
                                'product_uom_qty': mm.get('quantity'),
                                'quantity': mm.get('quantity'),
                                # 'date_deadline': mm.date_deadline,
                }) for mm in item_ids]
            }
            stock = stock_picking.sudo().create(vals)
            soid = saleOrder.search([('name', '=', stock.origin)], limit=1)
            del_man = request.env['res.users'].sudo().search([('id', '=', delivery_man_id)], limit=1)
            if soid:
                so_order.update({
                'assigned_delivery_man': delivery_man_id
                })
            if del_man:
                del_man.update({
                'is_available': True
                })
        else:
            stock = picking_so_order
            if delivery_man_id:
                stock.update({
                    'assigned_delivery_man': delivery_man_id
                    })
                soid = saleOrder.search([('name', '=', stock.origin)], limit=1)
                del_man = request.env['res.users'].sudo().search([('id', '=', delivery_man_id)], limit=1)
                if soid:
                    so_order.update({
                    'assigned_delivery_man': delivery_man_id
                    })
                if del_man:
                    del_man.update({
                    'is_available': True
                    })
                    
                
            stock.button_validate()
        return stock
    
    @validate_token   
    @http.route('/api/create/delivery', type='http', auth='none', methods=['POST', 'GET'], csrf=False)
    def delivery_operation(self, **kwargs):
         
        # req_data = json.loads(request.httprequest.data) # kwargs
        # req_data = json.loads(request.params) # kwargs
        # data = request.params
        '''
        headers = {
            'Content-Type': 'application/json',
            #'token': 'token_sasdd7e6ca6e3793e40bd6171429de6f8686ac6cd',
            #'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    #'Cookie': 'session_id=3cc87cdab877e01940c841e98e337bf291c180c1',
                        }
        DELIVERY_TRANSFER = {
                "partner_id": 2,
                "so_id": 2,
                "picking_id": 4,
                "picking_number": "WHOOL/0001",
                "so_number": "SO0004",
                "item_ids":
                    [{"name": "S0Q003", "product_id": 4, "location_id": 1, "location_dest_id": 5, "product_uom_qty": 4}]
                }
            url3 = "http://127.0.0.1:8080/api/delivery"
            req = rq.get(url3, headers=headers, json=SALES)
        '''
        data = json.loads(request.httprequest.data.decode("utf8"))
        if data: 
            dictdata = dict(
                so_id = data.get('so_id'),
                so_number = data.get('so_number'),
                picking_id = data.get('picking_id'),
                picking_number = data.get('picking_number'),
                partner_id = data.get('partner_id'),
                delivery_man_id = data.get('delivery_man_id'),
                order_delivery_status = data.get('order_delivery_status'),
                item_ids = data.get('item_ids'),
            )
            user = request.env.user
            stock = self.generate_stock_transfer(user, dict_data=dictdata)
            return json.dumps({
                'success': True, 
                'data': {
                    'delivery_id': stock.id, 'delivery_number': stock.name,
                    'delivery_man_id': stock.assigned_delivery_man.id,
                    'delivery_man': stock.assigned_delivery_man.name,
                    'status': stock.state.capitalize(),
                }
            })
        else:
            return json.dumps(
                {'success': False, 
                    'message': 'Ensure that the operation data contains create, update, or get'}
                )  
        
    def validate_invoice_and_post_journal(
        self, journal_id, inv): 
        """To be used only when they request for automatic payment generation
        journal: set to the cash journal default bank journal is 7
        """
        inbound_payment_method = request.env['account.payment.method'].sudo().search(
            [('code', '=', 'manual'), ('payment_type', '=', 'inbound')], limit=1)
        payment_method = 2
        if journal_id:
            payment_method = journal_id.inbound_payment_method_line_ids[0].id if \
                journal_id.inbound_payment_method_line_ids else inbound_payment_method.id \
                    if inbound_payment_method else payment_method
        # payment_method_line_id = request.get_payment_method_line_id('inbound', journal_id)
        payment_vals = {
            'date': fields.Date.today(),
            'amount': inv.amount_total,
            'payment_type': 'inbound',
            'company_id': inv.company_id.id,
            # 'is_internal_transfer': True,
            'partner_type': 'customer',
            'ref': inv.name,
            # 'move_id': inv.id,
            # 'journal_id': 8, #inv.payment_journal_id.id,
            'currency_id': inv.currency_id.id,
            'partner_id': inv.partner_id.id,
            # 'destination_account_id': inv.line_ids[1].account_id.id,
            'payment_method_line_id': payment_method, #payment_method_line_id.id if payment_method_line_id else payment_method,
        }
        _logger.info(f"VALIDATE xxx is {payment_vals}")
        
        '''
        Add the skip context to avoid;  
        Journal Entry Draft Entry PBNK1/2023/00002 is not valid. 
        In order to proceed, the journal items must include one and only
        one outstanding payments/receipts account.
        '''
        skip_context = {
            'skip_invoice_sync':True,
            'skip_invoice_line_sync':True,
            'skip_account_move_synchronization':True,
            'check_move_validity':False,
        }
        # payments = request.env['account.payment'].sudo().with_context(**skip_context).create(payment_vals)
        # # payments = request.env['account.payment'].create(payment_vals)
        # # payments._synchronize_from_moves(False)
        
        # payments.action_post()
        # return payments
       
        
    def _update_sales_order(self, data):
        '''Update an existing sales order.'''
        data.pop('operation', None)
        order_id = int(data.pop('id')) if data.pop('id') else False
        
        order = request.env['sale.order'].sudo().browse(order_id)
        if order:
            order_lines = data.pop('order_lines', None)
            if order_lines:
                updated_order_lines = []
                existing_product_ids = order.order_line.mapped('product_id.id')

                for line in order_lines:
                    product_id = line.get('product_id')
                    
                    if product_id in existing_product_ids:
                        existing_line = order.order_line.search([('order_id', '=', order.id),('product_id.id', '=', product_id)], limit=1)
                        updated_order_lines.append((1, existing_line.id, line))
                    else:
                        updated_order_lines.append((0, 0, line))

                data['order_line'] = updated_order_lines

            order.write(data)
            return json.dumps({'success': True, 'order_id': order.id})
        else:
            return json.dumps({'success': False, 'message': 'Sales order not found'})

    def _get_sales_order(self, data):
        '''where data is equal to the sent payload for get,
        e.g data = { 'id': 3, ...}
        '''
        order_id = int(data.get('id')) if data.get('id') else False
        so_number = data.get('so_number')

        if order_id or so_number:
            order = request.env['sale.order'].sudo().search([
                '|', ('id', '=', order_id), ('name', '=', so_number)
            ], limit=1)

            if not order:
                return {'success': False, 'message': 'Sales order not found'}
            
            order_data = {
                'id': order.id,
                'name': order.name,
                'partner_id': order.partner_id.id,
                'date_order': order.date_order.strftime('%Y-%m-%d %H:%M:%S'),
                'order_line': [{
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit
                } for line in order.order_line]
            }
            return json.dumps({'success': True, 'result': order_data})

        return json.dumps({'success': False, 'message': 'Missing order ID or SO number'})
 