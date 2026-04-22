from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_saved = fields.Boolean(string='Is Saved')
    allow_bypass = fields.Boolean(string='Allow Bypass', 
                                  default=True,
                                   help="Used to bypass validations of outstanding/payment reciepts account")
    origin = fields.Char(string='Source')
    memo_id = fields.Many2one('memo.model', string='Request Reference')

    # def _synchronize_from_moves(self, changed_fields):
    #     ''' Update the account.payment regarding its related account.move.
    #     Also, check both models are still consistent.
    #     :param changed_fields: A set containing all modified fields on account.move.
    #     '''
    #     pass
    
    def _synchronize_from_moves(self, changed_fields):
        # EXTENDS account
        for rec in self:
            if rec.allow_bypass:
                # Constraints bypass when entry is linked to an customized modules like easypay, eedc, 
                # jos_plateau.
                # Context is not enough, as we want to be able to delete
                # and update those entries later on.
                return
        return super()._synchronize_from_moves(changed_fields)
     
    
    def write(self, vals):
        'is saved is used to determine if the cashier has properly entered his account lines correctly'
        if 'is_saved' in vals:
            vals['is_saved'] = True 
        res = super(AccountPayment, self).write(vals)
        return res
    
    @api.model
    def create(self, vals):
        if 'is_saved' in vals:
            vals['is_saved'] = True 
        res = super(AccountPayment, self).create(vals)
        return res
    
    
    
