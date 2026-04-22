from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    selected = fields.Boolean(string="Select", default=False)
    legacy_id = fields.Integer(string="legacy_id")
    external_id = fields.Char(string="External ID")
    origin = fields.Char(string='Source')
    memo_id = fields.Many2one('memo.model', string='Request Reference')
    code = fields.Char(string='Source')
    memo_state = fields.Char(string='Request state')
    memo_type = fields.Many2one(
        'memo.type',
        string='Request type',
        required=False,
        copy=False
        )
    memo_type_key = fields.Char('Request type key', readonly=True)
    
    def update_memo_status(self, status):
        if self.memo_id:
            self.memo_id.state = status
        else: 
            if self.origin:
                memo = self.env['memo.model'].browse([
                    ('code', '=', self.origin)
                    ])
                if memo:
                    memo.state = status
    
    
    def action_confirm(self):
        # is request completed is used to determine if the entire process is done
        if not self.partner_id:
            raise ValidationError("Please enter a partner")
        if self.memo_id:
            if not self.memo_id.stage_id.require_so_confirmation:
                raise ValidationError('You are not required to confirm this SO at this stage. Set require confirmation on the current stage')
            else:
                if self.memo_id.stage_id.approver_ids and \
                    self.env.user.id not in [r.user_id.id for r in self.memo_id.stage_id.approver_ids]:
                    raise ValidationError("You are not allowed to confirm this sale Order")
        
        res = super(SaleOrder, self).action_confirm()
        return res
    
    def button_view_po(self):
        view_id = self.env.ref('sale.view_order_form').id
        ret = {
            'name': "Sale Order",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'sale.order',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            # 'domain': [],
            'target': 'current'
            }
        return ret