# -*- coding: utf-8 -*-

from odoo import api, models, fields
import random
import qrcode
import base64
from io import BytesIO
import json
from odoo import api, fields, models
from odoo.exceptions import AccessDenied, UserError
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons import base

base.models.res_users.USER_PRIVATE_FIELDS.append('oauth_access_token')


class Users(models.Model):
    _inherit = 'res.users'

    is_2fa_enable = fields.Boolean(string="2FA Status", default=False, copy=False)
    secret_key = fields.Char(string="Secret Key", readonly=True, copy=False)
    qr_code = fields.Binary(string="QR Code", copy=False)
    file_name = fields.Char(string="File Name", copy=False)
    # TODO: create secret key while creating user if 2fa enabled
    
    def _generate_secret_key(self):
        """Generate 16 digit secret key for 2FA"""
        valid_letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        secret_key = ''.join((random.choice(valid_letters) for i in xrange(16)))
        find_key = self.env['res.users'].search([('secret_key', '=', secret_key)])
        if find_key:
            self._generate_secret_key()
        secret_key = ' '.join(secret_key[i:i + 4] for i in xrange(0, len(secret_key), 4))
        return secret_key

    
    def _generate_qr_code(self, key):
        # generate qr code
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=20, border=4, )
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        new_key = "otpauth://totp/" + str(base_url) + "- ODOO " + "(" + str(
            self.login) + ")" + "?secret=" + key.replace(" ", "")
        qr.add_data(new_key)  # you can put here any attribute

        qr.make(fit=True)
        img = qr.make_image()
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        encode_img = base64.b64encode(buffer.getvalue())
        return encode_img

    @api.model
    def create(self, vals):
        if vals.get('is_2fa_enable') == True:
            key = self._generate_secret_key()
            encode_img = self._generate_qr_code(key)
            vals.update({'secret_key': key, 'qr_code': encode_img, 'file_name': "QR Code"})
        return super(Users, self).create(vals)

    
    def write(self, vals):
        if vals.get('is_2fa_enable') == False:
            vals.update({'secret_key': '', 'qr_code': False, 'file_name': ''})
        if vals.get('is_2fa_enable') == True:
            key = self._generate_secret_key()
            encode_img = self._generate_qr_code(key)
            vals.update({'secret_key': key, 'qr_code': encode_img, 'file_name': "QR Code"})
        return super(Users, self).write(vals)

    
    def send_two_factor_auth_mail(self):
        if self.is_2fa_enable:
            try:
                mail_id = self.env.ref('two_factor_authentication.two_factor_auth_template').send_mail(self.id)
            #                 mail_id.send()
            except:
                pass

    """
    Google Auth Issue
    * we are checking if there is an auth toke provided then just attach the use *
    """
    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """ retrieve and sign in the user corresponding to provider and validated access token
            :param provider: oauth provider id (int)
            :param validation: result of validation of access token (dict)
            :param params: oauth parameters (dict)
            :return: user login (str)
            :raise: AccessDenied if signin failed

            This method can be overridden to add alternative signin methods.
        """
        oauth_uid = validation['user_id']
        try:
            oauth_user = self.search([("oauth_uid", "=", oauth_uid), ('oauth_provider_id', '=', provider)])
            if not oauth_user and params:
                oauth_user = self.search([("login", "=", validation.get('email'))])

            if not oauth_user:
                raise AccessDenied()
            assert len(oauth_user) == 1
            oauth_user.write({'oauth_access_token': params['access_token']})
            return oauth_user.login
        except AccessDenied as access_denied_exception:
            if self.env.context.get('no_user_creation'):
                return None
            state = json.loads(params['state'])
            token = state.get('t')
            values = self._generate_signup_values(provider, validation, params)
            try:
                _, login, _ = self.signup(values, token)
                return login
            except (SignupError, UserError):
                raise access_denied_exception
