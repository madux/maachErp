from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = "account.move"

    payer_id = fields.Many2one('res.partner', 'Payer', help='Specify the partner that will make the payment')


    def action_move_create(self):
        """ To achieve direct billing without affecting the parent partner ledger, override the action_move_create 
            method in account.move model to substitute the partner id in account.move.line based on the value of the Payer above.
            Once the invoice is confirmed, it will use the payer as the commercial partner and thus this will not affect parent legder.

            The override is done in eha_multi_branch account.py. for some reasons, the override in that module takes precedence
        """
        return super(AccountInvoice, self).action_move_create()

