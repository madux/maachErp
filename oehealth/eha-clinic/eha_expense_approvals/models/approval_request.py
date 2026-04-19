# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    hr_expense_ids = fields.One2many('hr.expense', 'approvals_id', string='Expenses')
    hr_expense_count = fields.Integer(string='# Expenses', compute='_compute_hr_expense_ids')

    @api.depends('hr_expense_ids')
    def _compute_hr_expense_ids(self):
        for rec in self:
            rec.hr_expense_count = len(rec.hr_expense_ids)

    def action_view_expenses(self):
        action = self.env.ref('eha_expense_approvals.hr_expense_actions_all')
        result = action.read()[0]
        if self.hr_expense_count != 1:
            result['domain'] = "[('id', 'in', " + str(self.hr_expense_ids.ids) + ")]"
        elif self.hr_expense_count == 1:
            res = self.env.ref('hr_expense.hr_expense_view_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.hr_expense_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return result

    def create_hr_expense(self):
        for rec in self:
            return {
                'res_model': 'hr.expense',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_approvals_id': rec.id,
                    'default_name': rec.name,
                    'default_unit_amount': rec.amount,
                    'default_reference': rec.reference,
                    },
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': self.env.ref("hr_expense.hr_expense_view_form").id,
                'target': 'self'
            }