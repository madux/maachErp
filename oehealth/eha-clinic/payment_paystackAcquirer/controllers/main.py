# -*- coding: utf-8 -*-
import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


_logger = logging.getLogger(__name__)


class PaystackController(http.Controller):
    _return_url = '/payment/paystack/return'
    _webhook_url = '/payment/paystack/webhook'

    @http.route(_return_url, type='json', auth='public', methods=['POST'])
    def paystack_return_from_checkout(self, **data):
        """ Process the notification data sent by Paystack after redirection from checkout.

        :param dict data: The notification data.
        """
        data=data['data']
        _logger.info(
            "Handling redirection from Paystack with data:\n%s", pprint.pformat(data))
        
        # Handle the notification data.
        if data.get('status') != 'cancel':
            request.env['payment.transaction'].sudo(
            )._handle_notification_data('paystack', data)
        else:  # The customer cancelled the payment by clicking on the close button.
            # Don't try to process this case because the transaction id was not provided.
            pass

        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def paystack_webhook(self):
        """ Process the notification data sent by Paystack to the webhook.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        _logger.info(
            "Notification received from Paystack with data:\n%s", pprint.pformat(data))

        if data['event'] == 'charge.completed':
            try:
                # Check the origin of the notification.
                tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                    'paystack', data['data']
                )
                signature = request.httprequest.headers.get('verif-hash')
                self._verify_notification_signature(signature, tx_sudo)

                # Handle the notification data.
                notification_data = data['data']
                tx_sudo._handle_notification_data(
                    'paystack', notification_data)
            except ValidationError:  # Acknowledge the notification to avoid getting spammed.
                _logger.exception(
                    "Unable to handle the notification data; skipping to acknowledge")
        return request.make_json_response('')

    @staticmethod
    def _verify_notification_signature(received_signature, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict received_signature: The signature received with the notification data.
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        # Check for the received signature.
        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden()

        # Compare the received signature with the expected signature.
        expected_signature = tx_sudo.provider_id.paystack_webhook_secret
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden()
