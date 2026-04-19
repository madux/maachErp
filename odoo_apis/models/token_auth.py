# -*-encoding: utf-8-*-
import hashlib
import os

from odoo import fields, models, api, _


def nonce(length=40, prefix="token"):
    rbytes = os.urandom(length)
    return "{}_{}".format(prefix, str(hashlib.sha1(rbytes).hexdigest()))


class Token(models.Model):
    _name = "user.api.token"
    _description = 'User API Token'

    token = fields.Char("Access Token", required=False)
    user_id = fields.Many2one("res.users", string="User", required=False)
    scope = fields.Char("Scope")

    def find_one_or_create_token(self, user_id=None, create=False):
        """Returns user api token.

        Args:
            user_id (int, optional): ID of the user. Defaults to None.
            create (bool, optional): instruction on whether to create a new token record or not. Defaults to False.

        Returns:
            string: User's token
        """
        if not user_id:
            user_id = self.env.user.id

        access_token = (
            self.env["user.api.token"]
            .sudo()
            .search([("user_id", "=", user_id)], order="id DESC", limit=1)
        )
        if access_token:
            access_token = access_token[0]
        if not access_token and create:
            vals = {
                "user_id": user_id,
                "scope": "userinfo",
                "token": nonce(),
            }
            access_token = self.env["user.api.token"].sudo().create(vals)
        if not access_token:
            return None
        return access_token.token

    def is_valid(self, scopes=None):
        """
        Checks if the access token is valid.

        :param scopes: An iterable containing the scopes to check or None
        """
        self.ensure_one()
        return self._allow_scopes(scopes)

    def _allow_scopes(self, scopes):
        self.ensure_one()
        if not scopes:
            return True

        provided_scopes = set(self.scope.split())
        resource_scopes = set(scopes)
        return resource_scopes.issubset(provided_scopes)


class Users(models.Model):
    _inherit = "res.users"
    user_token_ids = fields.One2many("user.api.token", "user_id", string="Access Tokens")
    
    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        user_token = self.env['user.api.token'].create({
            'user_id': res.id,
            'token': 'token_sasdd7e6ca6e3793e40bd6171429de6f8686ac6cd',
        })
        return res
        
        
