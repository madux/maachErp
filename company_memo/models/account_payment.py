from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta 
from odoo import http


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    memo_reference = fields.Many2one('memo.model', string="Request Reference")
    legacy_id = fields.Integer(string="legacy_id")
    external_id = fields.Char(string="External ID")
    
    # def post(self):
    #     res = super(AccountPayment, self).post()
    #     if self.memo_reference:
    #         # self.memo_reference.state = "Done"
    #         self.memo_reference.is_request_completed = True
    #         self.sudo().memo_reference.update_final_state_and_approver()
    #     return res

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        if self.memo_reference and self.memo_reference.memo_setting_id.stage_ids:
            if self.memo_reference.memo_setting_id.stage_ids[-1].id != self.memo_reference.stage_id.id:
                # self.memo_reference.state = "Done"
                self.memo_reference.is_request_completed = True
                self.sudo().memo_reference.update_final_state_and_approver()
        return res
 