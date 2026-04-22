from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta 
from odoo import http


class AccountAccount(models.Model):
    _inherit = 'account.account'

    # district_id = fields.Many2one('hr.district', string="District")
    
    is_migrated = fields.Boolean(string="Is migrated")
    legacy_id = fields.Integer(string="legacy_id")
    external_id = fields.Char(string="External ID")
    active = fields.Boolean(string="Active", default=True)
    

class AccountJournal(models.Model):
    _inherit = "account.journal"

    # def __get_bank_statements_available_sources(self):
    #     rslt = super(AccountJournal, self).__get_bank_statements_available_sources()
    #     rslt.append(("online_sync", _("Automated Bank Synchronization")))
    #     return rslt

    # @api.model
    # def get_statement_creation_possible_values(self):
    #     return [('none', 'Create one statement per synchronization'),
    #             ('day', 'Create daily statements'),
    #             ('week', 'Create weekly statements'),
    #             ('bimonthly', 'Create bi-monthly statements'),
    #             ('month', 'Create monthly statements')]

    next_synchronization = fields.Datetime("Next synchronization")#, compute='_compute_next_synchronization')
    account_online_journal_id = fields.Integer('account.online.journal')
    account_online_provider_id = fields.Integer('account.online.provider',readonly=False)
    synchronization_status = fields.Char(string="synchronization_status", readonly=False)
    bank_statement_creation = fields.Char()
    
    legacy_id = fields.Integer(string="legacy_id")
    external_id = fields.Char(string="External ID")
