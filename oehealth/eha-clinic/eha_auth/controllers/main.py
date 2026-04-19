import json
import logging

import werkzeug.wrappers

from odoo import http
from .helpers import invalid_response, valid_response
from odoo.http import request

_logger = logging.getLogger(__name__)


class APITokencontroller(http.Controller):
    """."""

    @http.route("/api/v1/auth/token", methods=["POST"], type="http", auth="none", csrf=False)
    def token(self, **post):

        ''' 
        Sample Request: 
        Note: do not specify headers in the request
        url = "http://localhost:8069/api/v1/auth/token"
        data = {
        'db': 'prod2',
        'login': 'admin', 
        'password': 'admin'
        }
        req = requests.post(url, data=data)
        req.json()
        '''

        _token = request.env["api.token"].sudo()
        db, username, password = (
            post.get("db"),
            post.get("login"),
            post.get("password"),
        )
        _credentials_includes_in_body = all([db, username, password])
        if not _credentials_includes_in_body:
            # check the headers to see if credentials were passed via the header.
            headers = request.httprequest.headers
            db = headers.get("db")
            username = headers.get("login")
            password = headers.get("password")
            _credentials_includes_in_headers = all([db, username, password])
            if not _credentials_includes_in_headers:
                return invalid_response(
                    "missing_parameter",
                    "either of the following are missing [db, username,password] db = %s" % post.get('db'),
                    403,
                )

        # Login in odoo database:
        try:
            request.session.authenticate(db, username, password)
        except Exception as e:
            # Invalid database:
            info = "Invalid Login {}".format((e))
            error = "invalid_login"
            _logger.error(info)
            return invalid_response("wrong login credentials", error, 403)

        uid = request.session.uid
        # if odoo session uid is not set, then login failed:
        if not uid:
            info = "Login failed because the session UID was not set"
            error = "session_uid_not_found"
            _logger.error(info)
            return invalid_response(401, error, info)

        # retrieve or create a tokens
        token = _token.find_one_or_create_token(user_id=uid, create=True)
        # Return unsuccessful response:
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "uid": uid,
                    "user_context": request.session.get_context() if uid else {},
                    "company_id": request.env.user.company_id.id if uid else None,
                    "token": token,
                }
            ),
        )