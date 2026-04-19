# models/__init__.py
from . import res_patient_pharmacy_history
from . import pharmacy_config_stage
from . import pharmacy_prescription_line
from . import product_product
from . import res_partner
from . import api_token

# models/api_token.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import secrets
import hashlib
from datetime import datetime, timedelta

class APIToken(models.Model):
    _name = 'api.token'
    _description = 'API Authentication Token'
    _order = 'create_date desc'
    
    name = fields.Char(string='Token Name', required=True, help='Descriptive name for this token')
    token = fields.Char(string='Token', readonly=True, copy=False, index=True)
    token_hash = fields.Char(string='Token Hash', readonly=True, copy=False, index=True)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    active = fields.Boolean(string='Active', default=True)
    expiry_date = fields.Datetime(string='Expiry Date')
    is_expired = fields.Boolean(string='Expired', compute='_compute_is_expired', store=True)
    last_used = fields.Datetime(string='Last Used', readonly=True)
    usage_count = fields.Integer(string='Usage Count', default=0, readonly=True)
    ip_whitelist = fields.Text(string='IP Whitelist', help='Comma-separated list of allowed IP addresses. Leave empty to allow all.')
    scopes = fields.Selection([
        ('read', 'Read Only'),
        ('write', 'Write Only'),
        ('read_write', 'Read & Write'),
        ('admin', 'Admin'),
    ], string='Scope', default='read_write', required=True)
    notes = fields.Text(string='Notes')
    
    _sql_constraints = [
        ('token_hash_unique', 'unique(token_hash)', 'Token must be unique!'),
    ]
    
    @api.depends('expiry_date')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            if record.expiry_date:
                record.is_expired = record.expiry_date < now
            else:
                record.is_expired = False
    
    def _generate_token(self):
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)
    
    def _hash_token(self, token):
        """Hash the token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    @api.model
    def create(self, vals):
        """Override create to generate token"""
        token = self._generate_token()
        vals['token'] = token
        vals['token_hash'] = self._hash_token(token)
        
        record = super(APIToken, self).create(vals)
        
        # Return the token only once during creation
        # It won't be stored in plaintext after this
        record.message_post(
            body=_('API Token generated. Please save it securely as it will not be shown again: <br/><b>%s</b>') % token
        )
        
        return record
    
    def write(self, vals):
        """Prevent token modification"""
        if 'token' in vals or 'token_hash' in vals:
            raise ValidationError(_('Token cannot be modified. Please create a new token.'))
        return super(APIToken, self).write(vals)
    
    def action_regenerate_token(self):
        """Regenerate token"""
        self.ensure_one()
        token = self._generate_token()
        
        super(APIToken, self).write({
            'token': token,
            'token_hash': self._hash_token(token),
            'last_used': None,
            'usage_count': 0,
        })
        
        self.message_post(
            body=_('API Token regenerated. Please save it securely: <br/><b>%s</b>') % token
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Token Regenerated'),
                'message': _('New token has been generated. Check the chatter for the token value.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_deactivate(self):
        """Deactivate token"""
        self.write({'active': False})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Token Deactivated'),
                'message': _('The API token has been deactivated.'),
                'type': 'success',
            }
        }
    
    @api.model
    def validate_token(self, token, required_scope=None, ip_address=None):
        """
        Validate API token
        
        :param token: The API token to validate
        :param required_scope: Required scope for this operation (read, write, read_write, admin)
        :param ip_address: Client IP address
        :return: res.users record if valid, False otherwise
        """
        if not token:
            return False
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        token_hash = self._hash_token(token)
        
        # Find token record
        token_record = self.search([
            ('token_hash', '=', token_hash),
            ('active', '=', True)
        ], limit=1)
        
        if not token_record:
            return False
        
        # Check if expired
        if token_record.is_expired:
            return False
        
        # Check IP whitelist
        if token_record.ip_whitelist and ip_address:
            allowed_ips = [ip.strip() for ip in token_record.ip_whitelist.split(',')]
            if ip_address not in allowed_ips:
                return False
        
        # Check scope
        if required_scope:
            if token_record.scopes == 'read' and required_scope not in ['read']:
                return False
            elif token_record.scopes == 'write' and required_scope not in ['write']:
                return False
            elif token_record.scopes == 'read_write' and required_scope not in ['read', 'write']:
                return False
            # Admin has access to everything
        
        # Update usage statistics
        token_record.sudo().write({
            'last_used': fields.Datetime.now(),
            'usage_count': token_record.usage_count + 1
        })
        
        return token_record.user_id
    
    @api.model
    def cleanup_expired_tokens(self):
        """Cron job to cleanup expired tokens"""
        expired_tokens = self.search([
            ('is_expired', '=', True),
            ('active', '=', True)
        ])
        if expired_tokens:
            expired_tokens.write({'active': False})
        return True


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    api_token_ids = fields.One2many('api.token', 'user_id', string='API Tokens')
    api_token_count = fields.Integer(string='API Token Count', compute='_compute_api_token_count')
    
    @api.depends('api_token_ids')
    def _compute_api_token_count(self):
        for user in self:
            user.api_token_count = len(user.api_token_ids.filtered(lambda t: t.active))
    
    def action_view_api_tokens(self):
        """Open API tokens for this user"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('API Tokens'),
            'res_model': 'api.token',
            'view_mode': 'tree,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'default_user_id': self.id},
            'target': 'current',
        }