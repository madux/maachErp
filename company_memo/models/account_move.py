from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta 
from odoo import http


class AccountMoveMemo(models.Model):
    _inherit = 'account.move'
    _check_company_auto = False

    depreciation_percentage = fields.Float(string="Depreciation percentage(%)", required=False) 
    is_asset_additional_period = fields.Boolean(string="Is asset additional period", required=False) 
    is_first_depreciation = fields.Boolean(string="Is First Depreciation", store= True, required=False) 
    select = fields.Boolean(string="")
    asset_batch_number = fields.Char(string="Asset batch number")
    asset_modified_amount = fields.Float(string="Modified Asset Value", 
                                         help="During asset computation, If asset has been modified, system finds it and generate move for the modified different value")
   
    lock_fields_from_memo = fields.Boolean(
        string='locks field',
        default=False
    )
    invoice_date = fields.Date(
        string='Invoice/Bill Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
        index=True,
        copy=False,
        default=fields.Date.today(),
    )
    memo_id = fields.Many2one('memo.model', string="Request Reference")
    # district_id = fields.Many2one('hr.district', string="District")
    origin = fields.Char(string="Source")
    stage_invoice_name = fields.Char(
        string="Stage invoice name", 
        store=True,
        help="Used to track if invoice is from the stage configuration",
        )
    stage_invoice_required = fields.Boolean(string="Stage invoice required?", store=True,
        help="Used to track if invoice is required based on the stage configuration")
    is_locked = fields.Boolean(string="Is locked", default=False)
    memo_state = fields.Char(string="Request state", compute="compute_memo_state")
    payment_journal_id = fields.Many2one(
        'account.journal', 
        string="Payment Journal", 
        required=False,
        domain="[('id', 'in', suitable_journal_ids)]"
        )
    example_amount = fields.Float(store=False, compute='_compute_payment_term_example')
    example_date = fields.Date(store=False, compute='_compute_payment_term_example')
    example_invalid = fields.Boolean(compute='_compute_payment_term_example')
    example_preview = fields.Html(compute='_compute_payment_term_example')
    legacy_id = fields.Integer(string="legacy_id")
    external_id = fields.Char(string="External ID")
    hide_invoice_line = fields.Boolean()
    
    @api.depends('memo_id')
    def _compute_payment_term_example(self):
        for rec in self:
            if rec.invoice_payment_term_id:
                rec.example_amount = rec.invoice_payment_term_id.example_amount
                rec.example_date = rec.invoice_payment_term_id.example_date
                rec.example_invalid = rec.invoice_payment_term_id.example_invalid
                rec.example_preview = rec.invoice_payment_term_id.example_preview
            else:
                rec.example_amount =False
                rec.example_date = False
                rec.example_invalid = False
                rec.example_preview = False

    @api.depends('memo_id')
    def compute_memo_state(self):
        for rec in self:
            if rec.memo_id:
                rec.memo_state = rec.memo_id.state
            else:
                rec.memo_state = rec.memo_id.state

    def action_post(self):
        if self.memo_id and self.memo_id.memo_setting_id.stage_ids:
            if self.memo_id.memo_setting_id.stage_ids[-1].id != self.memo_id.stage_id.id:
                if self.memo_id.memo_type.memo_key == "soe":
                    '''This is added to help send the soe reference to the related cash advance'''
                    self.sudo().memo_id.cash_advance_reference.soe_advance_reference = self.memo_id.id
                    self.sudo().memo_id.set_cash_advance_as_retired()
                self.memo_id.is_request_completed = True
                self.sudo().memo_id.move_id = self.id
                self.sudo().memo_id.update_final_state_and_approver()
                # self.memo_id.state = "Done"
                self.sudo().memo_id.update_status_badge()
        return super(AccountMoveMemo, self).action_post()
    
class AccountMove(models.Model):
    _inherit = 'account.move.line'
    _check_company_auto = False


    code = fields.Char(string="Code")
    lock_fields_from_memo = fields.Boolean(
        string='locks field',
        related="move_id.lock_fields_from_memo"
    )
    
    # _sql_constraints = [
    #     (
    #         "check_credit_debit",
    #         "CHECK(display_type IN ('line_section', 'line_note') OR credit * debit=0)",
    #         "Wrong credit or debit value in accounting entry !: debit * credit cannot be equal to 0"
    #     ),
    #     (
    #         "check_amount_currency_balance_sign",
    #         """CHECK(
    #             display_type IN ('line_section', 'line_note')
    #             OR (
    #                 (balance <= 0 AND amount_currency <= 0)
    #                 OR
    #                 (balance >= 0 AND amount_currency >= 0)
    #             )
    #         )""",
    #         "The amount expressed in the secondary currency must be positive when account is debited and negative when "
    #         "account is credited. If the currency is the same as the one from the company, this amount must strictly "
    #         "be equal to the balance."
    #     ),
    #     (
    #         "check_accountable_required_fields",
    #         "CHECK(display_type IN ('line_section', 'line_note') OR account_id IS NOT NULL)",
    #         "The is not account set on the transaction line"
    #     ),
    #     (
    #         "check_non_accountable_fields_null",
    #         "CHECK(display_type NOT IN ('line_section', 'line_note') OR (amount_currency = 0 AND debit = 0 AND credit = 0 AND account_id IS NULL))",
    #         "Forbidden balance or account on non-accountable line: Ensure account ID is set, Also The debit and credit line must not be equal to 0."
    #     ),
    # ]
    

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    memo_id = fields.Many2one('memo.model', string="Request Reference")
    # district_id = fields.Many2one('hr.district', string="District")

    # def reverse_moves(self):
    #     res = super(AccountMoveReversal, self).post()
    #     for rec in self.move_ids:
    #         if rec.memo_id:
    #             rec.memo_id.state = "Approve" # waiting for payment and confirmation
    #     return res

     