# controllers/pharmacy_api_controller.py (Updated with token validation)
from odoo import http
from odoo.http import request, Response
import json
import logging
from datetime import datetime
from functools import wraps

_logger = logging.getLogger(__name__)


def validate_api_token(required_scope='read'):
    """
    Decorator to validate API token
    
    :param required_scope: Required scope (read, write, read_write, admin)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get token from header
            auth_header = request.httprequest.headers.get('Authorization')
            
            if not auth_header:
                return self._error_response('Authorization header is required', status=401)
            
            # Get client IP
            ip_address = request.httprequest.environ.get('REMOTE_ADDR')
            
            # Validate token
            user = request.env['api.token'].sudo().validate_token(
                token=auth_header,
                required_scope=required_scope,
                ip_address=ip_address
            )
            
            if not user:
                return self._error_response('Invalid or expired token', status=401)
            
            # Set the user context for this request
            request.env.user = user
            
            # Call the original function
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


class PharmacyAPIController(http.Controller):
    
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
    
    # ==================== TOKEN MANAGEMENT ENDPOINTS ====================
    
    @http.route('/api/v1/auth/token/create', type='json', auth='user', methods=['POST'], csrf=False)
    def create_api_token(self, **params):
        """
        POST /api/v1/auth/token/create
        Description: Create a new API token for the authenticated user
        Authentication: Basic Auth (Odoo username/password)
        
        Request Body (JSON):
        {
            "name": "My API Token",
            "expiry_days": 365,
            "scopes": "read_write",
            "ip_whitelist": "192.168.1.1,10.0.0.1",
            "notes": "Token for external app"
        }
        
        Returns:
        - New API token (shown only once)
        
        Example:
        curl -X POST http://localhost:8069/api/v1/auth/token/create \
          -u "admin:admin" \
          -H "Content-Type: application/json" \
          -d '{"name": "My Token", "expiry_days": 30}'
        """
        try:
            data = request.jsonrequest
            
            expiry_date = None
            if data.get('expiry_days'):
                expiry_date = datetime.now() + timedelta(days=int(data['expiry_days']))
            
            token_vals = {
                'name': data.get('name', 'API Token'),
                'user_id': request.env.user.id,
                'expiry_date': expiry_date,
                'scopes': data.get('scopes', 'read_write'),
                'ip_whitelist': data.get('ip_whitelist'),
                'notes': data.get('notes'),
            }
            
            token_record = request.env['api.token'].create(token_vals)
            
            return {
                'status': 'success',
                'message': 'API token created successfully. Please save it securely as it will not be shown again.',
                'data': {
                    'id': token_record.id,
                    'name': token_record.name,
                    'token': token_record.token,  # Only shown once
                    'expiry_date': token_record.expiry_date.isoformat() if token_record.expiry_date else None,
                    'scopes': token_record.scopes,
                }
            }
        except Exception as e:
            _logger.error(f"Error creating API token: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    @http.route('/api/v1/auth/token/list', type='json', auth='user', methods=['GET'], csrf=False)
    def list_api_tokens(self, **params):
        """
        GET /api/v1/auth/token/list
        Description: List all API tokens for the authenticated user
        Authentication: Basic Auth (Odoo username/password)
        
        Returns:
        - List of user's API tokens (without token values)
        """
        try:
            tokens = request.env['api.token'].search([
                ('user_id', '=', request.env.user.id)
            ])
            
            data = []
            for token in tokens:
                data.append({
                    'id': token.id,
                    'name': token.name,
                    'active': token.active,
                    'expiry_date': token.expiry_date.isoformat() if token.expiry_date else None,
                    'is_expired': token.is_expired,
                    'last_used': token.last_used.isoformat() if token.last_used else None,
                    'usage_count': token.usage_count,
                    'scopes': token.scopes,
                    'created_date': token.create_date.isoformat() if token.create_date else None,
                })
            
            return {
                'status': 'success',
                'message': 'Tokens retrieved successfully',
                'data': data
            }
        except Exception as e:
            _logger.error(f"Error listing API tokens: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    @http.route('/api/v1/auth/token/revoke/<int:token_id>', type='json', auth='user', methods=['POST'], csrf=False)
    def revoke_api_token(self, token_id, **params):
        """
        POST /api/v1/auth/token/revoke/{token_id}
        Description: Revoke/deactivate an API token
        Authentication: Basic Auth (Odoo username/password)
        
        Returns:
        - Success message
        """
        try:
            token = request.env['api.token'].browse(token_id)
            
            if not token.exists() or token.user_id.id != request.env.user.id:
                return {
                    'status': 'error',
                    'message': 'Token not found or unauthorized',
                    'data': None
                }
            
            token.write({'active': False})
            
            return {
                'status': 'success',
                'message': 'Token revoked successfully',
                'data': {'id': token_id}
            }
        except Exception as e:
            _logger.error(f"Error revoking API token: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    @http.route('/api/v1/auth/validate', type='http', auth='public', methods=['GET'], csrf=False)
    @validate_api_token(required_scope='read')
    def validate_token(self, **params):
        """
        GET /api/v1/auth/validate
        Description: Validate if the provided token is valid
        
        Headers:
        Authorization: Bearer YOUR_TOKEN_HERE
        
        Returns:
        - Token validation status and user info
        """
        try:
            return self._success_response({
                'valid': True,
                'user': {
                    'id': request.env.user.id,
                    'name': request.env.user.name,
                    'email': request.env.user.email,
                }
            })
        except Exception as e:
            _logger.error(f"Error validating token: {str(e)}")
            return self._error_response(str(e))
    