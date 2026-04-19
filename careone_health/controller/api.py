# controllers/__init__.py
# from . import pharmacy_api_controller

# controllers/pharmacy_api_controller.py
from odoo import http
from odoo.http import request, Response
import json
import logging
from datetime import datetime
import werkzeug.wrappers
import functools

_logger = logging.getLogger(__name__)

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
    
    
class PharmacyAPIController(http.Controller):
    
    # def _validate_token(self):
    #     """Validate API token - implement your authentication logic"""
    #     token = request.httprequest.headers.get('Authorization')
    #     if not token:
    #         return False
    #     # Implement your token validation logic here
    #     return True
    
    def _success_response(self, data, message="Success"):
        """Return success response"""
        return Response(
            json.dumps({
                'status': 'success',
                'message': message,
                'data': data
            }),
            status=200,
            mimetype='application/json'
        )
    
    def _error_response(self, message, status=400):
        """Return error response"""
        return Response(
            json.dumps({
                'status': 'error',
                'message': message,
                'data': None
            }),
            status=status,
            mimetype='application/json'
        )
        
    
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
    
    # ==================== GET ENDPOINTS ====================
    
    @validate_token
    @http.route('/api/v1/products', type='http', auth='public', methods=['GET'], csrf=False)
    def get_products(self, **params):
        """
        GET /api/v1/products
        Description: Get all drug products or filter by id/code
        
        Parameters:
        - id (optional): Product ID
        - code (optional): Product default_code
        
        Returns:
        - List of products with fields: id, name, default_code, active_ingredient, 
          dosage_form, strength, list_price, uom_id, drug_category_id, etc.
        
        Example:
        GET /api/v1/products
        GET /api/v1/products?id=123
        GET /api/v1/products?code=DRUG001
        """
        try:
            domain = [('is_drugs', '=', True)]
            
            if params.get('id'):
                domain.append(('id', '=', int(params['id'])))
            if params.get('code'):
                domain.append(('default_code', '=', params['code']))
            
            products = request.env['product.product'].sudo().search(domain)
            
            data = []
            for product in products:
                data.append({
                    'id': product.id,
                    'name': product.name,
                    'default_code': product.default_code,
                    'active_ingredient': product.active_ingredient,
                    'dosage_form': product.dosage_form,
                    'strength': product.strength,
                    'list_price': product.list_price,
                    'standard_price': product.standard_price,
                    'uom_id': {
                        'id': product.uom_id.id,
                        'name': product.uom_id.name
                    },
                    'drug_category_id': {
                        'id': product.drug_category_id.id,
                        'name': product.drug_category_id.name
                    } if product.drug_category_id else None,
                    'manufacturer_id': {
                        'id': product.manufacturer_id.id,
                        'name': product.manufacturer_id.name
                    } if product.manufacturer_id else None,
                    'requires_prescription': product.requires_prescription,
                    'controlled_substance': product.controlled_substance,
                    'qty_available': product.qty_available,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching products: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/prescription-lines', type='http', auth='public', methods=['GET'], csrf=False)
    def get_prescription_lines(self, **params):
        """
        GET /api/v1/prescription-lines
        Description: Get prescription lines with optional filters
        
        Parameters:
        - id (optional): Prescription line ID
        - history_id (optional): Pharmacy history ID
        - patient_id (optional): Patient ID
        - sale_order_id (optional): Sale Order ID
        - invoice_id (optional): Invoice ID
        - prescriber_id (optional): Prescriber ID
        - pharmacist_id (optional): Pharmacist ID
        - company_id (optional): Company ID
        - dispensed_date_from (optional): Dispensed date from (YYYY-MM-DD)
        - dispensed_date_to (optional): Dispensed date to (YYYY-MM-DD)
        
        Returns:
        - List of prescription lines with all relevant fields
        
        Example:
        GET /api/v1/prescription-lines?patient_id=45
        GET /api/v1/prescription-lines?dispensed_date_from=2024-01-01&dispensed_date_to=2024-12-31
        """
        try:
            domain = []
            
            if params.get('id'):
                domain.append(('id', '=', int(params['id'])))
            if params.get('history_id'):
                domain.append(('history_id', '=', int(params['history_id'])))
            if params.get('patient_id'):
                domain.append(('history_id.patient_id', '=', int(params['patient_id'])))
            if params.get('sale_order_id'):
                domain.append(('history_id.sale_order_id', '=', int(params['sale_order_id'])))
            if params.get('invoice_id'):
                domain.append(('history_id.invoice_id', '=', int(params['invoice_id'])))
            if params.get('prescriber_id'):
                domain.append(('history_id.prescriber_id', '=', int(params['prescriber_id'])))
            if params.get('pharmacist_id'):
                domain.append(('history_id.pharmacist_id', '=', int(params['pharmacist_id'])))
            if params.get('company_id'):
                domain.append(('history_id.company_id', '=', int(params['company_id'])))
            if params.get('dispensed_date_from'):
                domain.append(('dispensed_date', '>=', params['dispensed_date_from']))
            if params.get('dispensed_date_to'):
                domain.append(('dispensed_date', '<=', params['dispensed_date_to']))
            
            lines = request.env['pharmacy.prescription.line'].sudo().search(domain)
            
            data = []
            for line in lines:
                data.append({
                    'id': line.id,
                    'history_id': {
                        'id': line.history_id.id,
                        'name': line.history_id.name,
                        'patient_id': {
                            'id': line.history_id.patient_id.id,
                            'name': line.history_id.patient_id.name,
                            'patient_no': line.history_id.patient_id.patient_no if hasattr(line.history_id.patient_id, 'patient_no') else None
                        }
                    } if line.history_id else None,
                    'product_id': {
                        'id': line.product_id.id,
                        'name': line.product_id.name,
                        'default_code': line.product_id.default_code
                    },
                    'dosage': line.dosage,
                    'quantity': line.quantity,
                    'uom_id': {
                        'id': line.uom_id.id,
                        'name': line.uom_id.name
                    },
                    'frequency_duration': line.frequency_duration,
                    'frequency': line.frequency,
                    'route_of_administration': line.route_of_administration,
                    'start_date': line.start_date.isoformat() if line.start_date else None,
                    'end_date': line.end_date.isoformat() if line.end_date else None,
                    'expected_next_visit': line.expected_next_visit.isoformat() if line.expected_next_visit else None,
                    'is_dispensed': line.is_dispensed,
                    'dispensed_quantity': line.dispensed_quantity,
                    'dispensed_date': line.dispensed_date.isoformat() if line.dispensed_date else None,
                    'dispensed_by': {
                        'id': line.dispensed_by.id,
                        'name': line.dispensed_by.name
                    } if line.dispensed_by else None,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                    'instructions': line.instructions,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching prescription lines: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/partners', type='http', auth='public', methods=['GET'], csrf=False)
    def get_partners(self, **params):
        """
        GET /api/v1/partners
        Description: Get partners/patients
        
        Parameters:
        - id (optional): Partner ID
        - patient_no (optional): Patient number
        
        Returns:
        - List of partners with fields: id, name, patient_no, phone, mobile, 
          email, street, city, state, country, etc.
        
        Example:
        GET /api/v1/partners
        GET /api/v1/partners?patient_no=PAT001
        """
        try:
            domain = []
            
            if params.get('id'):
                domain.append(('id', '=', int(params['id'])))
            if params.get('patient_no'):
                domain.append(('patient_no', '=', params['patient_no']))
            
            partners = request.env['res.partner'].sudo().search(domain)
            
            data = []
            for partner in partners:
                data.append({
                    'id': partner.id,
                    'name': partner.name,
                    'patient_no': partner.patient_no if hasattr(partner, 'patient_no') else None,
                    'phone': partner.phone,
                    'mobile': partner.mobile,
                    'email': partner.email,
                    'street': partner.street,
                    'street2': partner.street2,
                    'city': partner.city,
                    'state_id': {
                        'id': partner.state_id.id,
                        'name': partner.state_id.name
                    } if partner.state_id else None,
                    'country_id': {
                        'id': partner.country_id.id,
                        'name': partner.country_id.name
                    } if partner.country_id else None,
                    'zip': partner.zip,
                    'is_company': partner.is_company,
                    'image_url': f'/web/image/res.partner/{partner.id}/image_1920' if partner.image_1920 else None,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching partners: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/pharmacy-history', type='http', auth='public', methods=['GET'], csrf=False)
    def get_pharmacy_history(self, **params):
        """
        GET /api/v1/pharmacy-history
        Description: Get pharmacy history records
        
        Parameters:
        - patient_id (optional): Patient ID
        - patient_no (optional): Patient number
        - id (optional): History ID
        
        Returns:
        - List of pharmacy history records with patient details
        
        Example:
        GET /api/v1/pharmacy-history?patient_no=PAT001
        """
        try:
            domain = []
            
            if params.get('id'):
                domain.append(('id', '=', int(params['id'])))
            if params.get('patient_id'):
                domain.append(('patient_id', '=', int(params['patient_id'])))
            if params.get('patient_no'):
                domain.append(('patient_id.patient_no', '=', params['patient_no']))
            
            histories = request.env['res.patient.pharmacy.history'].sudo().search(domain)
            
            data = []
            for history in histories:
                data.append({
                    'id': history.id,
                    'name': history.name,
                    'patient_id': {
                        'id': history.patient_id.id,
                        'name': history.patient_id.name,
                        'patient_no': history.patient_id.patient_no if hasattr(history.patient_id, 'patient_no') else None
                    },
                    'branch_id': {
                        'id': history.branch_id.id,
                        'name': history.branch_id.name
                    },
                    'date': history.date.isoformat() if history.date else None,
                    'stage_id': {
                        'id': history.stage_id.id,
                        'name': history.stage_id.name
                    } if history.stage_id else None,
                    'state': history.state,
                    'total_amount': history.total_amount,
                    'prescriber_id': {
                        'id': history.prescriber_id.id,
                        'name': history.prescriber_id.name
                    } if history.prescriber_id else None,
                    'pharmacist_id': {
                        'id': history.pharmacist_id.id,
                        'name': history.pharmacist_id.name
                    } if history.pharmacist_id else None,
                    'sale_order_id': {
                        'id': history.sale_order_id.id,
                        'name': history.sale_order_id.name
                    } if history.sale_order_id else None,
                    'invoice_id': {
                        'id': history.invoice_id.id,
                        'name': history.invoice_id.name
                    } if history.invoice_id else None,
                    'diagnosis': history.diagnosis,
                    'notes': history.notes,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching pharmacy history: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/journals', type='http', auth='public', methods=['GET'], csrf=False)
    def get_journals(self, **params):
        """
        GET /api/v1/journals
        Description: Get account journals
        
        Parameters:
        - id (optional): Journal ID
        - code (optional): Journal code
        
        Returns:
        - List of journals with id, name, code, type
        
        Example:
        GET /api/v1/journals
        GET /api/v1/journals?code=BANK
        """
        try:
            domain = []
            
            if params.get('id'):
                domain.append(('id', '=', int(params['id'])))
            if params.get('code'):
                domain.append(('code', '=', params['code']))
            
            journals = request.env['account.journal'].sudo().search(domain)
            
            data = []
            for journal in journals:
                data.append({
                    'id': journal.id,
                    'name': journal.name,
                    'code': journal.code,
                    'type': journal.type,
                    'company_id': {
                        'id': journal.company_id.id,
                        'name': journal.company_id.name
                    }
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching journals: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/invoices', type='http', auth='public', methods=['GET'], csrf=False)
    def get_invoices(self, **params):
        """
        GET /api/v1/invoices
        Description: Get account moves/invoices
        
        Parameters:
        - id (optional): Invoice ID
        - patient_no (optional): Patient number (filters by partner.patient_no)
        
        Returns:
        - List of invoices with details
        
        Example:
        GET /api/v1/invoices?patient_no=PAT001
        """
        try:
            domain = [('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund'])]
            
            if params.get('id'):
                domain.append(('id', '=', int(params['id'])))
            if params.get('patient_no'):
                domain.append(('partner_id.patient_no', '=', params['patient_no']))
            
            invoices = request.env['account.move'].sudo().search(domain)
            
            data = []
            for invoice in invoices:
                invoice_lines = []
                for line in invoice.invoice_line_ids:
                    invoice_lines.append({
                        'id': line.id,
                        'product_id': {
                            'id': line.product_id.id,
                            'name': line.product_id.name,
                            'default_code': line.product_id.default_code
                        } if line.product_id else None,
                        'name': line.name,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                        'price_subtotal': line.price_subtotal,
                        'price_total': line.price_total,
                        'tax_ids': [{
                            'id': tax.id,
                            'name': tax.name,
                            'amount': tax.amount
                        } for tax in line.tax_ids]
                    })
                
                data.append({
                    'id': invoice.id,
                    'name': invoice.name,
                    'move_type': invoice.move_type,
                    'partner_id': {
                        'id': invoice.partner_id.id,
                        'name': invoice.partner_id.name,
                        'patient_no': invoice.partner_id.patient_no if hasattr(invoice.partner_id, 'patient_no') else None
                    },
                    'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                    'invoice_date_due': invoice.invoice_date_due.isoformat() if invoice.invoice_date_due else None,
                    'state': invoice.state,
                    'amount_untaxed': invoice.amount_untaxed,
                    'amount_tax': invoice.amount_tax,
                    'amount_total': invoice.amount_total,
                    'amount_residual': invoice.amount_residual,
                    'invoice_line_ids': invoice_lines,
                    'journal_id': {
                        'id': invoice.journal_id.id,
                        'name': invoice.journal_id.name,
                        'code': invoice.journal_id.code
                    }
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching invoices: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/sale-orders', type='http', auth='public', methods=['GET'], csrf=False)
    def get_sale_orders(self, **params):
        """
        GET /api/v1/sale-orders
        Description: Get sale orders
        
        Parameters:
        - id (optional): Sale Order ID
        - patient_no (optional): Patient number
        - so_number (optional): Sale order number (name field)
        
        Returns:
        - List of sale orders with order lines
        
        Example:
        GET /api/v1/sale-orders?patient_no=PAT001
        GET /api/v1/sale-orders?so_number=SO001
        """
        try:
            domain = []
            
            if params.get('id'):
                domain.append(('id', '=', int(params['id'])))
            if params.get('patient_no'):
                domain.append(('partner_id.patient_no', '=', params['patient_no']))
            if params.get('so_number'):
                domain.append(('name', '=', params['so_number']))
            
            sale_orders = request.env['sale.order'].sudo().search(domain)
            
            data = []
            for order in sale_orders:
                order_lines = []
                for line in order.order_line:
                    order_lines.append({
                        'id': line.id,
                        'product_id': {
                            'id': line.product_id.id,
                            'name': line.product_id.name,
                            'default_code': line.product_id.default_code
                        },
                        'name': line.name,
                        'product_uom_qty': line.product_uom_qty,
                        'qty_delivered': line.qty_delivered,
                        'qty_invoiced': line.qty_invoiced,
                        'price_unit': line.price_unit,
                        'price_subtotal': line.price_subtotal,
                        'price_total': line.price_total,
                        'tax_id': [{
                            'id': tax.id,
                            'name': tax.name,
                            'amount': tax.amount
                        } for tax in line.tax_id]
                    })
                
                data.append({
                    'id': order.id,
                    'name': order.name,
                    'partner_id': {
                        'id': order.partner_id.id,
                        'name': order.partner_id.name,
                        'patient_no': order.partner_id.patient_no if hasattr(order.partner_id, 'patient_no') else None
                    },
                    'date_order': order.date_order.isoformat() if order.date_order else None,
                    'state': order.state,
                    'amount_untaxed': order.amount_untaxed,
                    'amount_tax': order.amount_tax,
                    'amount_total': order.amount_total,
                    'order_line': order_lines,
                    'user_id': {
                        'id': order.user_id.id,
                        'name': order.user_id.name
                    } if order.user_id else None
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching sale orders: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/taxes', type='http', auth='public', methods=['GET'], csrf=False)
    def get_taxes(self, **params):
        """
        GET /api/v1/taxes
        Description: Get account taxes
        
        Parameters:
        - company_id (optional): Company ID
        
        Returns:
        - List of taxes with id, name, amount
        
        Example:
        GET /api/v1/taxes
        GET /api/v1/taxes?company_id=1
        """
        try:
            domain = []
            
            if params.get('company_id'):
                domain.append(('company_id', '=', int(params['company_id'])))
            
            taxes = request.env['account.tax'].sudo().search(domain)
            
            data = []
            for tax in taxes:
                data.append({
                    'id': tax.id,
                    'name': tax.name,
                    'amount': tax.amount,
                    'amount_type': tax.amount_type,
                    'type_tax_use': tax.type_tax_use,
                    'company_id': {
                        'id': tax.company_id.id,
                        'name': tax.company_id.name
                    }
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching taxes: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/branches', type='http', auth='public', methods=['GET'], csrf=False)
    def get_branches(self, **params):
        """
        GET /api/v1/branches
        Description: Get all branches
        
        Returns:
        - List of branches with id, name, code
        
        Example:
        GET /api/v1/branches
        """
        try:
            branches = request.env['multi.branch'].sudo().search([])
            
            data = []
            for branch in branches:
                data.append({
                    'id': branch.id,
                    'name': branch.name,
                    'code': branch.code if hasattr(branch, 'code') else None,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching branches: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/pharmacy-stages', type='http', auth='public', methods=['GET'], csrf=False)
    def get_pharmacy_stages(self, **params):
        """
        GET /api/v1/pharmacy-stages
        Description: Get pharmacy stages
        
        Parameters:
        - branch_id (optional): Branch ID to filter stages
        
        Returns:
        - List of pharmacy stages
        
        Example:
        GET /api/v1/pharmacy-stages?branch_id=1
        """
        try:
            domain = []
            
            if params.get('branch_id'):
                domain.append(('branch_ids', 'in', int(params['branch_id'])))
            
            stages = request.env['pharmacy.config.stage'].sudo().search(domain)
            
            data = []
            for stage in stages:
                data.append({
                    'id': stage.id,
                    'name': stage.name,
                    'sequence': stage.sequence,
                    'is_finance_stage': stage.is_finance_stage,
                    'is_issued_stage': stage.is_issued_stage,
                    'is_verification_stage': stage.is_verification_stage,
                    'is_dispensing_stage': stage.is_dispensing_stage,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching pharmacy stages: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/purchase-orders', type='http', auth='public', methods=['GET'], csrf=False)
    def get_purchase_orders(self, **params):
        """
        GET /api/v1/purchase-orders
        Description: Get purchase orders
        
        Parameters:
        - id (optional): Purchase Order ID
        - patient_no (optional): Patient number
        - po_number (optional): Purchase order number (name field)
        
        Returns:
        - List of purchase orders with order lines
        
        Example:
        GET /api/v1/purchase-orders?po_number=PO001
        """
        try:
            domain = []
            
            if params.get('id'):
                domain.append(('id', '=', int(params['id'])))
            if params.get('patient_no'):
                domain.append(('partner_id.patient_no', '=', params['patient_no']))
            if params.get('po_number'):
                domain.append(('name', '=', params['po_number']))
            
            purchase_orders = request.env['purchase.order'].sudo().search(domain)
            
            data = []
            for order in purchase_orders:
                order_lines = []
                for line in order.order_line:
                    order_lines.append({
                        'id': line.id,
                        'product_id': {
                            'id': line.product_id.id,
                            'name': line.product_id.name,
                            'default_code': line.product_id.default_code
                        },
                        'name': line.name,
                        'product_qty': line.product_qty,
                        'qty_received': line.qty_received,
                        'qty_invoiced': line.qty_invoiced,
                        'price_unit': line.price_unit,
                        'price_subtotal': line.price_subtotal,
                        'price_total': line.price_total,
                        'taxes_id': [{
                            'id': tax.id,
                            'name': tax.name,
                            'amount': tax.amount
                        } for tax in line.taxes_id]
                    })
                
                data.append({
                    'id': order.id,
                    'name': order.name,
                    'partner_id': {
                        'id': order.partner_id.id,
                        'name': order.partner_id.name,
                        'patient_no': order.partner_id.patient_no if hasattr(order.partner_id, 'patient_no') else None
                    },
                    'date_order': order.date_order.isoformat() if order.date_order else None,
                    'date_approve': order.date_approve.isoformat() if order.date_approve else None,
                    'state': order.state,
                    'amount_untaxed': order.amount_untaxed,
                    'amount_tax': order.amount_tax,
                    'amount_total': order.amount_total,
                    'order_line': order_lines,
                    'user_id': {
                        'id': order.user_id.id,
                        'name': order.user_id.name
                    } if order.user_id else None
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching purchase orders: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/stock-locations', type='http', auth='public', methods=['GET'], csrf=False)
    def get_stock_locations(self, **params):
        """
        GET /api/v1/stock-locations
        Description: Get stock locations
        
        Parameters:
        - branch_id (optional): Branch ID
        
        Returns:
        - List of stock locations
        
        Example:
        GET /api/v1/stock-locations?branch_id=1
        """
        try:
            domain = []
            
            if params.get('branch_id'):
                domain.append(('branch_id', '=', int(params['branch_id'])))
            
            locations = request.env['stock.location'].sudo().search(domain)
            
            data = []
            for location in locations:
                data.append({
                    'id': location.id,
                    'name': location.name,
                    'complete_name': location.complete_name,
                    'usage': location.usage,
                    'location_id': {
                        'id': location.location_id.id,
                        'name': location.location_id.name
                    } if location.location_id else None,
                    'barcode': location.barcode,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching stock locations: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/stock-moves', type='http', auth='public', methods=['GET'], csrf=False)
    def get_stock_moves(self, **params):
        """
        GET /api/v1/stock-moves
        Description: Get stock moves
        
        Parameters:
        - branch_id (optional): Branch ID
        
        Returns:
        - List of stock moves with move lines
        
        Example:
        GET /api/v1/stock-moves?branch_id=1
        """
        try:
            domain = []
            
            if params.get('branch_id'):
                domain.append(('location_id.branch_id', '=', int(params['branch_id'])))
            
            moves = request.env['stock.move'].sudo().search(domain)
            
            data = []
            for move in moves:
                move_lines = []
                for line in move.move_line_ids:
                    move_lines.append({
                        'id': line.id,
                        'product_id': {
                            'id': line.product_id.id,
                            'name': line.product_id.name,
                            'default_code': line.product_id.default_code
                        },
                        'quantity': line.quantity,
                        'lot_id': {
                            'id': line.lot_id.id,
                            'name': line.lot_id.name
                        } if line.lot_id else None,
                        'location_id': {
                            'id': line.location_id.id,
                            'name': line.location_id.name
                        },
                        'location_dest_id': {
                            'id': line.location_dest_id.id,
                            'name': line.location_dest_id.name
                        }
                    })
                
                data.append({
                    'id': move.id,
                    'name': move.name,
                    'product_id': {
                        'id': move.product_id.id,
                        'name': move.product_id.name,
                        'default_code': move.product_id.default_code
                    },
                    'product_uom_qty': move.product_uom_qty,
                    'quantity': move.quantity,
                    'state': move.state,
                    'location_id': {
                        'id': move.location_id.id,
                        'name': move.location_id.name
                    },
                    'location_dest_id': {
                        'id': move.location_dest_id.id,
                        'name': move.location_dest_id.name
                    },
                    'move_line_ids': move_lines,
                    'date': move.date.isoformat() if move.date else None,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching stock moves: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/stock-warehouses', type='http', auth='public', methods=['GET'], csrf=False)
    def get_stock_warehouses(self, **params):
        """
        GET /api/v1/stock-warehouses
        Description: Get stock warehouses
        
        Parameters:
        - branch_id (optional): Branch ID
        
        Returns:
        - List of warehouses
        
        Example:
        GET /api/v1/stock-warehouses?branch_id=1
        """
        try:
            domain = []
            
            if params.get('branch_id'):
                domain.append(('branch_id', '=', int(params['branch_id'])))
            
            warehouses = request.env['stock.warehouse'].sudo().search(domain)
            
            data = []
            for warehouse in warehouses:
                data.append({
                    'id': warehouse.id,
                    'name': warehouse.name,
                    'code': warehouse.code,
                    'partner_id': {
                        'id': warehouse.partner_id.id,
                        'name': warehouse.partner_id.name
                    } if warehouse.partner_id else None,
                    'lot_stock_id': {
                        'id': warehouse.lot_stock_id.id,
                        'name': warehouse.lot_stock_id.name
                    },
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching warehouses: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/stock-quants', type='http', auth='public', methods=['GET'], csrf=False)
    def get_stock_quants(self, **params):
        """
        GET /api/v1/stock-quants
        Description: Get stock quants (inventory levels)
        
        Parameters:
        - product_code (optional): Product default_code
        - id (optional): Product ID
        
        Returns:
        - List of stock quants with available quantities
        
        Example:
        GET /api/v1/stock-quants?product_code=DRUG001
        """
        try:
            domain = []
            
            if params.get('product_code'):
                domain.append(('product_id.default_code', '=', params['product_code']))
            if params.get('id'):
                domain.append(('product_id', '=', int(params['id'])))
            
            quants = request.env['stock.quant'].sudo().search(domain)
            
            data = []
            for quant in quants:
                data.append({
                    'id': quant.id,
                    'product_id': {
                        'id': quant.product_id.id,
                        'name': quant.product_id.name,
                        'default_code': quant.product_id.default_code
                    },
                    'location_id': {
                        'id': quant.location_id.id,
                        'name': quant.location_id.name,
                        'complete_name': quant.location_id.complete_name
                    },
                    'quantity': quant.quantity,
                    'reserved_quantity': quant.reserved_quantity,
                    'available_quantity': quant.quantity - quant.reserved_quantity,
                    'lot_id': {
                        'id': quant.lot_id.id,
                        'name': quant.lot_id.name
                    } if quant.lot_id else None,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching stock quants: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/allergies', type='http', auth='public', methods=['GET'], csrf=False)
    def get_allergies(self, **params):
        """
        GET /api/v1/allergies
        Description: Get all allergies
        
        Returns:
        - List of allergies
        
        Example:
        GET /api/v1/allergies
        """
        try:
            allergies = request.env['pharmacy.allergy'].sudo().search([])
            
            data = []
            for allergy in allergies:
                data.append({
                    'id': allergy.id,
                    'name': allergy.name,
                    'severity': allergy.severity,
                    'description': allergy.description,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching allergies: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/chronic-conditions', type='http', auth='public', methods=['GET'], csrf=False)
    def get_chronic_conditions(self, **params):
        """
        GET /api/v1/chronic-conditions
        Description: Get all chronic conditions
        
        Returns:
        - List of chronic conditions
        
        Example:
        GET /api/v1/chronic-conditions
        """
        try:
            conditions = request.env['pharmacy.chronic.condition'].sudo().search([])
            
            data = []
            for condition in conditions:
                data.append({
                    'id': condition.id,
                    'name': condition.name,
                    'code': condition.code,
                    'description': condition.description,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching chronic conditions: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/drug-categories', type='http', auth='public', methods=['GET'], csrf=False)
    def get_drug_categories(self, **params):
        """
        GET /api/v1/drug-categories
        Description: Get all drug categories
        
        Returns:
        - List of drug categories
        
        Example:
        GET /api/v1/drug-categories
        """
        try:
            categories = request.env['pharmacy.drug.category'].sudo().search([])
            
            data = []
            for category in categories:
                data.append({
                    'id': category.id,
                    'name': category.name,
                    'code': category.code,
                    'parent_id': {
                        'id': category.parent_id.id,
                        'name': category.parent_id.name
                    } if category.parent_id else None,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching drug categories: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/drug-interactions', type='http', auth='public', methods=['GET'], csrf=False)
    def get_drug_interactions(self, **params):
        """
        GET /api/v1/drug-interactions
        Description: Get all drug interactions
        
        Returns:
        - List of drug interactions
        
        Example:
        GET /api/v1/drug-interactions
        """
        try:
            interactions = request.env['pharmacy.drug.interaction'].sudo().search([])
            
            data = []
            for interaction in interactions:
                data.append({
                    'id': interaction.id,
                    'drug_1_id': {
                        'id': interaction.drug_1_id.id,
                        'name': interaction.drug_1_id.name,
                        'default_code': interaction.drug_1_id.default_code
                    },
                    'drug_2_id': {
                        'id': interaction.drug_2_id.id,
                        'name': interaction.drug_2_id.name,
                        'default_code': interaction.drug_2_id.default_code
                    },
                    'severity': interaction.severity,
                    'description': interaction.description,
                    'management': interaction.management,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching drug interactions: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/stock-batches', type='http', auth='public', methods=['GET'], csrf=False)
    def get_stock_batches(self, **params):
        """
        GET /api/v1/stock-batches
        Description: Get pharmacy stock batches
        
        Returns:
        - List of stock batches
        
        Example:
        GET /api/v1/stock-batches
        """
        try:
            batches = request.env['pharmacy.stock.batch'].sudo().search([])
            
            data = []
            for batch in batches:
                data.append({
                    'id': batch.id,
                    'name': batch.name,
                    'product_id': {
                        'id': batch.product_id.id,
                        'name': batch.product_id.name,
                        'default_code': batch.product_id.default_code
                    },
                    'manufacturing_date': batch.manufacturing_date.isoformat() if batch.manufacturing_date else None,
                    'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                    'quantity': batch.quantity,
                    'is_expired': batch.is_expired,
                    'days_to_expiry': batch.days_to_expiry,
                    'branch_id': {
                        'id': batch.branch_id.id,
                        'name': batch.branch_id.name
                    } if batch.branch_id else None,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching stock batches: {str(e)}")
            return self._error_response(str(e))
    
    @validate_token
    @http.route('/api/v1/insurances', type='http', auth='public', methods=['GET'], csrf=False)
    def get_insurances(self, **params):
        """
        GET /api/v1/insurances
        Description: Get pharmacy insurances
        
        Returns:
        - List of insurances
        
        Example:
        GET /api/v1/insurances
        """
        try:
            insurances = request.env['pharmacy.insurance'].sudo().search([])
            
            data = []
            for insurance in insurances:
                data.append({
                    'id': insurance.id,
                    'name': insurance.name,
                    'patient_id': {
                        'id': insurance.patient_id.id,
                        'name': insurance.patient_id.name,
                        'patient_no': insurance.patient_id.patient_no if hasattr(insurance.patient_id, 'patient_no') else None
                    },
                    'insurance_company_id': {
                        'id': insurance.insurance_company_id.id,
                        'name': insurance.insurance_company_id.name
                    },
                    'policy_type': insurance.policy_type,
                    'coverage_percentage': insurance.coverage_percentage,
                    'is_active': insurance.is_active,
                    'start_date': insurance.start_date.isoformat() if insurance.start_date else None,
                    'end_date': insurance.end_date.isoformat() if insurance.end_date else None,
                })
            
            return self._success_response(data)
        except Exception as e:
            _logger.error(f"Error fetching insurances: {str(e)}")
            return self._error_response(str(e))
    
    # ==================== POST ENDPOINTS ====================
    
    @validate_token
    @http.route('/api/v1/partners', type='json', auth='public', methods=['POST'], csrf=False)
    def create_partner(self, **params):
        """
        POST /api/v1/partners
        Description: Create a new partner/patient
        
        Request Body (JSON):
        {
            "name": "John Doe",
            "patient_no": "PAT001",
            "phone": "+1234567890",
            "mobile": "+1234567890",
            "email": "john@example.com",
            "street": "123 Main St",
            "city": "New York",
            "state_id": 1,
            "country_id": 233,
            "zip": "10001"
        }
        
        Returns:
        - Created partner with id
        """
        try:
            data = request.jsonrequest
            
            partner_vals = {
                'name': data.get('name'),
                'phone': data.get('phone'),
                'mobile': data.get('mobile'),
                'email': data.get('email'),
                'street': data.get('street'),
                'street2': data.get('street2'),
                'city': data.get('city'),
                'zip': data.get('zip'),
            }
            
            if data.get('patient_no'):
                partner_vals['patient_no'] = data['patient_no']
            if data.get('state_id'):
                partner_vals['state_id'] = data['state_id']
            if data.get('country_id'):
                partner_vals['country_id'] = data['country_id']
            
            partner = request.env['res.partner'].sudo().create(partner_vals)
            
            return {
                'status': 'success',
                'message': 'Partner created successfully',
                'data': {
                    'id': partner.id,
                    'name': partner.name,
                    'patient_no': partner.patient_no if hasattr(partner, 'patient_no') else None
                }
            }
        except Exception as e:
            _logger.error(f"Error creating partner: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    @validate_token
    @http.route('/api/v1/pharmacy-history', type='json', auth='public', methods=['POST'], csrf=False)
    def create_pharmacy_history(self, **params):
        """
        POST /api/v1/pharmacy-history
        Description: Create a new pharmacy history/prescription
        
        Request Body (JSON):
        {
            "patient_id": 1,
            "branch_id": 1,
            "prescriber_id": 2,
            "diagnosis": "Hypertension",
            "notes": "Patient requires monitoring",
            "prescription_lines": [
                {
                    "product_id": 10,
                    "dosage": "10mg",
                    "quantity": 30,
                    "uom_id": 1,
                    "frequency_duration": 7,
                    "frequency": "daily",
                    "route_of_administration": "oral",
                    "instructions": "Take with food"
                }
            ]
        }
        
        Returns:
        - Created pharmacy history with id
        """
        try:
            data = request.jsonrequest
            
            prescription_lines = []
            for line_data in data.get('prescription_lines', []):
                prescription_lines.append((0, 0, {
                    'product_id': line_data.get('product_id'),
                    'dosage': line_data.get('dosage'),
                    'quantity': line_data.get('quantity'),
                    'uom_id': line_data.get('uom_id'),
                    'frequency_duration': line_data.get('frequency_duration'),
                    'frequency': line_data.get('frequency'),
                    'route_of_administration': line_data.get('route_of_administration'),
                    'instructions': line_data.get('instructions'),
                    'refills_allowed': line_data.get('refills_allowed', 0),
                }))
            
            history_vals = {
                'patient_id': data.get('patient_id'),
                'branch_id': data.get('branch_id'),
                'prescriber_id': data.get('prescriber_id'),
                'diagnosis': data.get('diagnosis'),
                'notes': data.get('notes'),
                'prescription_line_ids': prescription_lines,
            }
            
            if data.get('stage_id'):
                history_vals['stage_id'] = data['stage_id']
            
            history = request.env['res.patient.pharmacy.history'].sudo().create(history_vals)
            
            return {
                'status': 'success',
                'message': 'Pharmacy history created successfully',
                'data': {
                    'id': history.id,
                    'name': history.name,
                    'patient_id': history.patient_id.id,
                    'total_amount': history.total_amount
                }
            }
        except Exception as e:
            _logger.error(f"Error creating pharmacy history: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
            
    @validate_token  
    @http.route('/api/v1/sale-orders', type='json', auth='public', methods=['POST'], csrf=False)
    def create_sale_order(self, **params):
        """
        POST /api/v1/sale-orders
        Description: Create a new sale order
        
        Request Body (JSON):
        {
            "partner_id": 1,
            "date_order": "2024-01-15",
            "order_line": [
                {
                    "product_id": 10,
                    "product_uom_qty": 2,
                    "price_unit": 50.00,
                    "tax_id": [1, 2]
                }
            ]
        }
        
        Returns:
        - Created sale order with id
        """
        try:
            data = request.jsonrequest
            
            order_lines = []
            for line_data in data.get('order_line', []):
                order_lines.append((0, 0, {
                    'product_id': line_data.get('product_id'),
                    'product_uom_qty': line_data.get('product_uom_qty'),
                    'price_unit': line_data.get('price_unit'),
                    'tax_id': [(6, 0, line_data.get('tax_id', []))],
                }))
            
            order_vals = {
                'partner_id': data.get('partner_id'),
                'order_line': order_lines,
            }
            
            if data.get('date_order'):
                order_vals['date_order'] = data['date_order']
            
            order = request.env['sale.order'].sudo().create(order_vals)
            
            return {
                'status': 'success',
                'message': 'Sale order created successfully',
                'data': {
                    'id': order.id,
                    'name': order.name,
                    'amount_total': order.amount_total
                }
            }
        except Exception as e:
            _logger.error(f"Error creating sale order: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    @validate_token
    @http.route('/api/v1/purchase-orders', type='json', auth='public', methods=['POST'], csrf=False)
    def create_purchase_order(self, **params):
        """
        POST /api/v1/purchase-orders
        Description: Create a new purchase order
        
        Request Body (JSON):
        {
            "partner_id": 5,
            "date_order": "2024-01-15",
            "order_line": [
                {
                    "product_id": 10,
                    "product_qty": 100,
                    "price_unit": 25.00,
                    "taxes_id": [1]
                }
            ]
        }
        
        Returns:
        - Created purchase order with id
        """
        try:
            data = request.jsonrequest
            
            order_lines = []
            for line_data in data.get('order_line', []):
                order_lines.append((0, 0, {
                    'product_id': line_data.get('product_id'),
                    'product_qty': line_data.get('product_qty'),
                    'price_unit': line_data.get('price_unit'),
                    'taxes_id': [(6, 0, line_data.get('taxes_id', []))],
                }))
            
            order_vals = {
                'partner_id': data.get('partner_id'),
                'order_line': order_lines,
            }
            
            if data.get('date_order'):
                order_vals['date_order'] = data['date_order']
            
            order = request.env['purchase.order'].sudo().create(order_vals)
            
            return {
                'status': 'success',
                'message': 'Purchase order created successfully',
                'data': {
                    'id': order.id,
                    'name': order.name,
                    'amount_total': order.amount_total
                }
            }
        except Exception as e:
            _logger.error(f"Error creating purchase order: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    @validate_token
    @http.route('/api/v1/invoices', type='json', auth='public', methods=['POST'], csrf=False)
    def create_invoice(self, **params):
        """
        POST /api/v1/invoices
        Description: Create a new invoice
        
        Request Body (JSON):
        {
            "partner_id": 1,
            "move_type": "out_invoice",
            "invoice_date": "2024-01-15",
            "invoice_line_ids": [
                {
                    "product_id": 10,
                    "quantity": 2,
                    "price_unit": 50.00,
                    "tax_ids": [1]
                }
            ]
        }
        
        Returns:
        - Created invoice with id
        """
        try:
            data = request.jsonrequest
            
            invoice_lines = []
            for line_data in data.get('invoice_line_ids', []):
                invoice_lines.append((0, 0, {
                    'product_id': line_data.get('product_id'),
                    'quantity': line_data.get('quantity'),
                    'price_unit': line_data.get('price_unit'),
                    'tax_ids': [(6, 0, line_data.get('tax_ids', []))],
                }))
            
            invoice_vals = {
                'partner_id': data.get('partner_id'),
                'move_type': data.get('move_type', 'out_invoice'),
                'invoice_line_ids': invoice_lines,
            }
            
            if data.get('invoice_date'):
                invoice_vals['invoice_date'] = data['invoice_date']
            if data.get('journal_id'):
                invoice_vals['journal_id'] = data['journal_id']
            
            invoice = request.env['account.move'].sudo().create(invoice_vals)
            
            return {
                'status': 'success',
                'message': 'Invoice created successfully',
                'data': {
                    'id': invoice.id,
                    'name': invoice.name,
                    'amount_total': invoice.amount_total
                }
            }
        except Exception as e:
            _logger.error(f"Error creating invoice: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    @validate_token
    @http.route('/api/v1/stock-moves', type='json', auth='public', methods=['POST'], csrf=False)
    def create_stock_move(self, **params):
        """
        POST /api/v1/stock-moves
        Description: Create a new stock move
        
        Request Body (JSON):
        {
            "product_id": 10,
            "product_uom_qty": 50,
            "location_id": 8,
            "location_dest_id": 9,
            "name": "Stock Move for Product X",
            "picking_type_id": 1
        }
        
        Returns:
        - Created stock move with id
        """
        try:
            data = request.jsonrequest
            
            move_vals = {
                'name': data.get('name', 'Stock Move'),
                'product_id': data.get('product_id'),
                'product_uom_qty': data.get('product_uom_qty'),
                'product_uom': data.get('product_uom'),
                'location_id': data.get('location_id'),
                'location_dest_id': data.get('location_dest_id'),
            }
            
            if data.get('picking_type_id'):
                move_vals['picking_type_id'] = data['picking_type_id']
            if data.get('picking_id'):
                move_vals['picking_id'] = data['picking_id']
            
            move = request.env['stock.move'].sudo().create(move_vals)
            
            return {
                'status': 'success',
                'message': 'Stock move created successfully',
                'data': {
                    'id': move.id,
                    'name': move.name,
                    'state': move.state
                }
            }
        except Exception as e:
            _logger.error(f"Error creating stock move: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
 