from datetime import datetime
from dateutil.parser import parse
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class resCompany(models.Model):
    _inherit = 'res.company'

    user_signature = fields.Binary("Upload User Signature")
    account_default_debit_account_id = fields.Many2one(
        "account.account", 
        string="Default Expense Account",
        ) 
    
    default_cash_advance_account_id = fields.Many2one(
        "account.account", 
        string="Employee Cash Advance(Other Asset)",
        )
    
    default_bank_cash_account_id = fields.Many2one(
        "account.account", 
        string="Default Bank/Cash Account",
        domain="[('account_type', 'in', ['asset_cash'])]"
        )
    
    default_revenue_account_id = fields.Many2one(
        "account.account", 
        string="Default Revenue Account",
        domain="[('account_type', 'in', ['income', 'other_income'])]"
        )