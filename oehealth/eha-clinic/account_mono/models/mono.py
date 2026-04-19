# -*- coding: utf-8 -*-
import requests
import json
import datetime
import logging
import uuid
import re

from odoo import models, api, fields
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


# class MonoProviderAccount(models.Model):
#     _inherit = ['account.online.provider']

#     provider_type = fields.Selection(selection_add=[('mono', 'Mono')])

#     def _get_available_providers(self):
#         ret = super(MonoProviderAccount, self)._get_available_providers()
#         ret.append('mono')
#         return ret


class AccountBankStatement(models.Model):
    _inherit = ['account.bank.statement']

    @api.model
    def create(self, vals):
        if self.env.context.get('from_mono'):
            journal_id = vals.get('journal_id')
            journal_id = self.env['account.journal'].browse(journal_id)
            vals['name'] = journal_id.name + ' From Date: ' + str(journal_id.last_sync_date) + ' To Date: ' + str(fields.Date.today().strftime(
                '%d-%m-%Y'))
        res = super(AccountBankStatement, self).create(vals)
        return res
