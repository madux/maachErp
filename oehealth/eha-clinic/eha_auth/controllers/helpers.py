from odoo.http import request, Response
from odoo import http
import datetime
import logging
import functools
from datetime import datetime
import json
import werkzeug.wrappers
from odoo.http import request
# aether
import hashlib
from typing import (Any, List, Mapping)
# ncdc
import dateutil.parser as parser
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz


# Aether Messages have some required metadata in order to validate and process them
def structure_message(
    hashed_id: str,
    schemadecorator_id: str,
    body: Mapping[str, Any]
) -> Mapping[str, Any]:
    return {
        'id': hashed_id,
        'status': 'Publishable',
        'schemadecorator': schemadecorator_id,
        'payload': dict(**body, **{'id': hashed_id})
    }

# Simple hashing function to make an internal ID Aether compliant


def id_hash(internal_uuid: str, size=36):
    return hashlib.md5(internal_uuid.encode('utf-8')).hexdigest()[:size]

# Convenience function to turn a list of internal records into a ready payload.


def prepare_many(
    records: List[Mapping[str, Any]],
    id_field_name: str,
    schemadecorator_id: str
) -> List[Mapping[str, Any]]:
    return [
        structure_message(
            id_hash(
                msg.get(id_field_name)
            ),
            schemadecorator_id,
            msg
        ) for msg in records
    ]


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
            request.env["api.token"]
            .sudo()
            .search([("token", "=", token)], order="id DESC", limit=1)
        )

        if (access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id) != token):
            return invalid_response(
                "token", "Invalid Token", 401
            )

        request.session.uid = access_token_data.user_id.id
        request.update_env(user=access_token_data.user_id.id, context=None, su=None)
        return func(self, *args, **kwargs)

    return wrap


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


def validate_token2(func):
    """This additional class has been created because of the required header label for the token which is 'Access-Token' instead of 'token' as implemented in 'validate_token'."""

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        """."""
        token = request.httprequest.headers.get("Access-Token")
        if not token:
            return invalid_response(
                "token_not_found", "please provide token in the request header", 401
            )
        access_token_data = (
            request.env["api.token"]
            .sudo()
            .search([("token", "=", token)], order="id DESC", limit=1)
        )

        if (access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id) != token):
            return invalid_response(
                "token", "Invalid Token", 401
            )

        request.session.uid = access_token_data.user_id.id
        # request.uid = access_token_data.user_id.id
        request.update_env(user=access_token_data.user_id.id, context=None, su=None)
        return func(self, *args, **kwargs)

    return wrap


def convert_date_to_iso(date):
    new_date = parser.parse(date)
    return new_date.isoformat()


def tolocale_time(input_time):
    ''' This method converts UTC to current user timezone
        By default, odoo records date in UTC. 
        This is bcos odoo users can login from any place in the world 
        and thus will not be able to save in different timezone
        odoo converts the UTC date to users timezone on the view
    '''
    try:
        ftime = input_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        local = pytz.timezone('Africa/Lagos')
        return str(datetime.strftime(pytz.utc.localize(datetime.strptime(ftime, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT))
    except:
        pass


def convert_time(miliTime):
    hours, minutes, seconds = miliTime.split(":")
    hours, minutes, seconds = int(hours), int(minutes), int(seconds)
    setting = "AM"
    if hours > 12:
        setting = "PM"
        hours -= 12
    return ("%02d:%02d" + " " + setting) % (hours, minutes)


def validate_secret_key(func):
    """Decorator for Validating public key """

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        """."""
        key = request.httprequest.headers.get("Secret-key")
        if not key:
            # if request.endpoint.routing['type'] == 'json':
            #     # Response.status = '400'
            #     return {
            #         "error": "secret_key_not_found",
            #         "message": "Unauthorized Access"
            #     }
            # else:
            return invalid_response(
                "secret_key_not_found", "Unauthorized Access", 400
            )

        pub_key = http.request.env['ir.config_parameter'].sudo(
        ).get_param('healthmate_api.secret_key', '')

        if (key != pub_key):
            # if request.endpoint.routing['type'] == 'json':
                # Response.status = '400'
            return {
                "error": "secret_key",
                "message": "Unauthorized Access"
            }
            # else:
            #     return invalid_response(
            #         "secret_key", "Unauthorized Access", 400
            #     )

        return func(self, *args, **kwargs)

    return wrap


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()


def valid_response(data={}, status=200, message="successful"):
    """Valid Response
    This will be return when the http request was successfully processed."""
    return werkzeug.wrappers.Response(
        status=status,
        content_type="application/json; charset=utf-8",
        response=json.dumps({
            "data": data,
            "status": status,
            "message": message
        }),
    )
