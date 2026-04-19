#-*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError

class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    @api.model
    def create(self, vals):
        res = super(AccountAnalyticAccount, self).create(vals)
        res._restrict_analytic_account_creation()
        return res

    def _restrict_analytic_account_creation(self):
        for rec in self:
            if not rec.user_has_groups('eha_analytic_account_restriction.group_analytic_account_creation'):
                raise UserError('You currently do not have rights to create an analytic account, please contact admin')

# class AccountAnalyticTag(models.Model):
#     _inherit = 'account.analytic.tag'

#     @api.model
#     def create(self, vals):
#         res = super(AccountAnalyticTag, self).create(vals)
#         res._restrict_analytic_account_tag_creation()
#         return res

#     def _restrict_analytic_account_tag_creation(self):
#         for rec in self:
#             if not rec.user_has_groups('eha_analytic_account_restriction.group_analytic_account_creation'):
#                 raise UserError('You currently do not have rights to create an analytic account, please contact admin')




