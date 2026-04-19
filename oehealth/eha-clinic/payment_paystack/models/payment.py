# coding: utf-8

import logging
import requests
import pprint
import json

from odoo import api, fields, models, _
# from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)



class PaymentAcquirerPaystack(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('paystackAcquirer', 'PaystackAcquirer')])
    paystack_public_key = fields.Char(required_if_provider='paystackAcquirer', groups='base.group_user')
    paystack_secret_key = fields.Char(required_if_provider='paystackAcquirer', groups='base.group_user')
    environment = fields.Char(required_if_provider='paystackAcquirer', groups='base.group_user')

    @api.model
    def _get_paystack_api_url(self):
        """ Paystack URLs"""
        if self.environment == 'prod':
            return 'paystack.com'
        else :
            return 'paystack.com'

    def paystack_form_generate_values(self, tx_values):
        self.ensure_one()
        paystack_tx_values = dict(tx_values)
        temp_paystack_tx_values = {
            'company': self.company_id.name,
            'amount': tx_values['amount'],  # Mandatory
            'currency': tx_values['currency'].name,  # Mandatory anyway
            'currency_id': tx_values['currency'].id,  # same here
            'address_line1': tx_values.get('partner_address'),  # Any info of the partner is not mandatory
            'address_city': tx_values.get('partner_city'),
            'address_country': tx_values.get('partner_country') and tx_values.get('partner_country').name or '',
            'email': tx_values.get('partner_email') or tx_values.get('billing_partner_email'),
            'address_zip': tx_values.get('partner_zip'),
            'name': tx_values.get('partner_name'),
            'phone': tx_values.get('partner_phone'),
        }

        paystack_tx_values.update(temp_paystack_tx_values)
        return paystack_tx_values


class PaymentTransactionPaystack(models.Model):
    _inherit = 'payment.transaction'

    def _paystack_verify_charge(self, data):
        # data for verification'
        
        url = 'https://api.paystack.co/transaction/verify/'+self.reference

        headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+self.acquirer_id.paystack_secret_key,
        }

        r = requests.request("GET", url, headers=headers,)

        #_logger.info('_paystack_verify_charge: Values received:\n%s', pprint.pformat(r))
        #return self._paystack_validate_tree(r.json(),data)
        tree = r.json()
        #def _paystack_validate_tree(self, tree, data):
        self.ensure_one()
        if self.state != 'draft':
            _logger.info('Paystack: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = tree["data"]["status"]
        amount = tree["data"]["amount"]
        currency = tree["data"]["currency"]
        if status == 'success' and amount == int(float(data['amount'])*100):
            self.write({
                'date': fields.datetime.now(),
                'acquirer_reference': self.reference,
            })
            self._set_transaction_done()
            self.execute_callback()
            if self.payment_token_id:
                self.payment_token_id.verified = True
            return True
        else:
            error = tree['message']
            _logger.warn(error)
            self.sudo().write({
                'state_message': error,
                'acquirer_reference':tree["data"]["reference"],
                'date': fields.datetime.now(),
            })
            self._set_transaction_cancel()
            return False