# coding: utf-8
import requests
import json
import logging
from tokenize import group
from werkzeug.urls import url_join

from odoo import api, fields, service, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('paystack', "Paystack")], ondelete={'paystack': 'set default'})
    paystack_public_key = fields.Char(
        required_if_provider='paystack')
    paystack_secret_key = fields.Char(
        required_if_provider='paystack', groups='base.group_system')

    @api.model
    def _get_paystack_api_url(self):
        return 'https://api.paystack.co'

    def _paystack_make_request(self, endpoint, payload=None, method='POST', offline=False):
        """ Make a request to Paystack API at the specified endpoint.
        Note: self.ensure_one()
        :param str endpoint: The endpoint to be reached by the request
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :param bool offline: Whether the operation of the transaction being processed is 'offline'
        :return The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """
        self.ensure_one()

        url = url_join('https://api.paystack.co', endpoint)
        headers = {
            'Authorization': f'Bearer {self.paystack_secret_key}',
            "Content-Type": "application/json"
        }
        try:
            _logger.info("headers: %s", headers)
            _logger.info("method: %s", method)
            _logger.info("payload: %s", payload)
            
            if method == 'GET':
                response = requests.get(
                    url, headers=headers, timeout=3600)
                response.raise_for_status()
                j = json.loads(response.text)
                _logger.info("response: %s", j)
            else:
                response = requests.post(
                    url, json=payload, headers=headers, timeout=3600)


        except requests.exceptions.HTTPError:
            _logger.exception(
                "invalid API request at %s with data %s", url, payload)
            error_msg = response.json().get('error', {}).get('message', '')
            raise ValidationError("Paystack: " + _(
                "The communication with the API failed.\n"
                "Paystack gave us the following info about the problem:\n'%s'", error_msg
            ))

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError(
                "Paystack: " + _("Could not establish the connection to the API."))
        _logger.info("Response json: %s", response.json())
        return response.json()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'paystack':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_paystackAcquirer.payment_method_paystack').id

    def _should_build_inline_form(self, is_validation=False):
        """ Return whether the inline form should be instantiated if it exists.
        For an acquirer to handle both direct payments and payment with redirection, it should
        override this method and return whether the inline form should be instantiated (i.e. if the
        payment should be direct) based on the operation (online payment or validation).
        :param bool is_validation: Whether the operation is a validation
        :return: Whether the inline form should be instantiated
        :rtype: bool
        """
        return True
