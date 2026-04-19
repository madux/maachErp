# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class HRExpense(models.Model):
    _inherit = 'hr.expense'

    approvals_id = fields.Many2one(comodel_name='approval.request', string='Approvals')