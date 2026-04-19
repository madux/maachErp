# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import _, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paystackAcquirer.controllers.main import PaystackController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Paystack-specific rendering values.
        Note: self.ensure_one() from `_get_rendering_values`
        :param dict rendering_values: The generic rendering values of the transaction
        :return: The dict of acquirer-specific rendering values
        :rtype: dict
        """
        print("processing_values Custom")
        print(processing_values)
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'paystack' or self.operation == 'online_token':
            return res

        # Initiate the payment and retrieve the payment link data.
        base_url = self.provider_id.get_base_url()
        return_url = PaystackController._return_url
        print("Updated Value")
        processing_values.update({'pub_key': self.provider_id.paystack_public_key,
                                  'currency': self.currency_id.name,
                                  'email': self.partner_email})
        payload = {
            'reference': self.reference,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'callback_url': urls.url_join(base_url, PaystackController._return_url),
            'email': self.partner_email,
            'pub_key': self.provider_id.paystack_public_key,
            'api_url': 'https://api.paystack.co',
        }


        return payload

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Paystack data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data were received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'paystack' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')

        if not reference:
            raise ValidationError(
                "Paystack: " + _("Received data with missing reference."))

        tx = self.search([('reference', '=', reference),
                         ('provider_code', '=', 'paystack')])
        if not tx:
            raise ValidationError(
                "Paystack: " +
                _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Flutterwave data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data were received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'paystack':
            return

        # Verify the notification data.
        payment_data = self.provider_id._paystack_make_request(
            f'transaction/verify/{self.reference}', method='GET'
        )

        # Process the verified notification data.
        self.provider_reference = self.reference
        payment_status = payment_data.get('data').get('status')
        currency = payment_data.get('data').get('currency')
        amount = payment_data.get('data').get('amount')

        _logger.info("paystack verify endpoint: %s", payment_status)

        if payment_status == 'success' and (self.amount * 100) == amount and self.currency_id.name == currency:
            self._set_done()
        elif payment_status == 'failed':
            self._set_canceled(
                "Paystack: " + _("Canceled payment with status: %s", payment_status))
        elif payment_status == 'success' and (self.amount * 100) != amount or payment_status == 'success' and self.currency_id.name != currency:
            _logger.info("Successful Partial Payment Made: %s", payment_status)
            _logger.info("amount: %s", amount)
            _logger.info("self.amount: %s", self.amount)
            _logger.info("currency: %s", currency)
            _logger.info("self.currency: %s", self.currency_id.name)
            self._set_pending(state_message="Partial Payment Made")
        else:
            _logger.info(
                "Received data with invalid payment status: %s", payment_status)
            self._set_error(
                "Paystack: " +
                _("Received data with invalid payment status: %s", payment_status)
            )
