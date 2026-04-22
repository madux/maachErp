from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    selected = fields.Boolean(string="Select", default=False)
    legacy_id = fields.Integer(string="legacy_id")
    external_id = fields.Char(string="External ID")
    partner_id = fields.Many2one(
        'res.partner', string='Vendor', 
        required=False, change_default=True, 
        tracking=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", 
        help="You can find a vendor by its Name, TIN, Email or Internal Reference."
        )
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
    
    def button_view_po(self):
        view_id = self.env.ref('purchase.purchase_order_form').id
        ret = {
            'name': "Project Purchase Order",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'purchase.order',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            # 'domain': [],
            'target': 'current'
            }
        return ret
    
    def print_voucher_order_report(self):
        picking_ids = self.picking_ids
        for pick in picking_ids:
            pick.write({'printed': True})
        return self.env.ref('stock.action_report_picking').report_action([picking_ids.ids])
    
    # def button_confirm(self):
    #     # is request completed is used to determine if the entire process is done
    #     if self.memo_id:
    #         self.memo_id.is_request_completed = True
    #         self.sudo().memo_id.update_final_state_and_approver()
    #     res = super(PurchaseOrder, self).button_confirm()
    #     return res
    
    
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
    
    def button_confirm(self):
        # is request completed is used to determine if the entire process is done
        if not self.partner_id:
            raise ValidationError("Please enter a partner")
        if self.memo_id:
            if not self.memo_id.stage_id.require_po_confirmation:
                raise ValidationError('You are not required to confirm this PO at this stage. Set require confirmation on the current stage')
            else:
                if self.memo_id.stage_id.approver_ids and \
                    self.env.user.id not in [r.user_id.id for r in self.memo_id.stage_id.approver_ids]:
                    raise ValidationError("You are not allowed to confirm this Purchase Order")
        
        res = super(PurchaseOrder, self).button_confirm()
        return res
    
    # def action_create_invoice(self):
    #     if self.memo_id:
    #         if not self.memo_id.stage_id.require_bill_payment:
    #             raise ValidationError('You are not required to create bill at this stage. Set require bill payment on the current stage')
    #         else:
    #             if self.memo_id.stage_id.approver_ids and \
    #                 self.env.user.id not in [r.user_id.id for r in self.memo_id.stage_id.approver_ids]:
    #                 raise ValidationError("You are not allowed to create bill for this Purchase Order")
    #     res = super(PurchaseOrder, self).button_confirm()
    #     return res
    
    
    # def button_confirm(self):
    #     # is request completed is used to determine if the entire process is done
    #     if self.memo_id:
    #         # memo_setting_stages = self.memo_id.memo_setting_id.stage_ids.ids[-1]
    #         # if self.memo_id.stage_id.id != memo_setting_stages:
    #         users_to_approve = [r.user_id.id for r in self.memo_id.stage_id.approver_ids] + [r.user_id.id for r in self.memo_id.memo_setting_id.approver_ids]
    #         # raise ValidationError(users_to_approve)
    #         if self.env.user.id not in users_to_approve:
    #             raise ValidationError("You are not allowed to confirm this Purchase Order")
    #         self.memo_id.is_request_completed = True
    #         self.sudo().memo_id.update_final_state_and_approver()
    #     res = super(PurchaseOrder, self).button_confirm()
    #     return res
    # def action_view_picking(self):
    #     if self.memo_id:
    #         appr2 = [r.user_id.id for r in self.memo_id.project_memo_id.stage_id.approver_ids]
    #         approver_ids = appr1 + appr2
    #         if self.env.user.id not in approver_ids:
    #             # [r.user_id.id for r in self.memo_id.stage_id.approver_ids]:
    #             raise ValidationError("You are not allowed to confirm this product receipts")
    #     result = super(PurchaseOrder, self).action_view_picking()
    #     return result
    
    def action_view_picking(self):
        if self.memo_id:
            appr1 = [r.user_id.id for r in self.memo_id.stage_id.approver_ids]
            approver_ids = appr1 
            if self.env.user.id not in approver_ids and self.memo_id.state not in ['Done']: # memo_id.state Used for optimization 
                # and self.env.user.id not in [r.user_id.id for r in self.memo_id.stage_id.approver_ids]:
                raise ValidationError("You are not allowed to confirm this product receipts")
        result = super(PurchaseOrder, self).action_view_picking()
        return result
    
    ## dont cancel the memo because it might affect memo record
    # def button_cancel(self):
    #     res = super(PurchaseOrder, self).button_cancel()
    #     # self.update_memo_status('Done') 
    #     return res