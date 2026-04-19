from odoo import models, fields, api
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError

class HrExpense(models.Model):
    _inherit = "hr.expense"
    branch_id = fields.Many2one('eha.branch', 'Branch', default=lambda self: self.env['res.partner']._branch_default_get())

    
    def _get_account_move_by_sheet(self):
        """ Return a mapping between the expense sheet of current expense and its account move
            :returns dict where key is a sheet id, and value is an account move record
        """
        move_grouped_by_sheet = {}
        for expense in self:
            # create the move that will contain the accounting entries
            account_date = expense.sheet_id.accounting_date or expense.date
            if expense.sheet_id.id not in move_grouped_by_sheet:
                journal = expense.sheet_id.bank_journal_id if expense.payment_mode == 'company_account' else expense.sheet_id.journal_id
                move = self.env['account.move'].create({
                    'journal_id': journal.id,
                    'company_id': self.env.user.company_id.id,
                    'branch_id': self.env.user.partner_id.branch_id.id,
                    'date': account_date,
                    'ref': expense.sheet_id.name,
                    # force the name to the default value, to avoid an eventual 'default_name' in the context
                    # to set it to '' which cause no number to be given to the account.move when posted.
                    'name': '/',
                })
                move_grouped_by_sheet[expense.sheet_id.id] = move
            else:
                move = move_grouped_by_sheet[expense.sheet_id.id]
        return move_grouped_by_sheet