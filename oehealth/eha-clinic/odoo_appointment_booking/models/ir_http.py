import odoo
from odoo import models
from odoo.http import request, Response
from werkzeug.exceptions import BadRequest

class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_api_token(cls):
        token = False
        error_message = False
        token = request.httprequest.headers.get("Token")
        if not token:
            error_message = "Header missing a valid token"
        access_token_data = (
            request.env["api.token"]
            .sudo()
            .search([("token", "=", token)], order="id DESC", limit=1)
        )
        if (access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id) != token):
            error_message = "Wrong token provided!"

        request.session.uid = access_token_data.user_id.id
        uid_id = access_token_data.user_id.id
        request.update_env(user=uid_id, context=None, su=None)
        if error_message:
            Response.status = "401"
            raise BadRequest(error_message)
        return True