# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class HrContract(models.Model):
    _inherit = 'hr.contract'

    # analytic_tag_ids = fields.Many2many(
    #     'account.analytic.tag', string='Analytic Tags',
    #     domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    # analytic_tag_ids = fields.Many2many(
    #     'account.analytic.tag', string='Analytic Tags')

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    def _prepare_line_values(self, line, account_id, date, debit, credit):
        res = super()._prepare_line_values(line, account_id, date, debit, credit)
        # res["analytic_tag_ids"] = line.slip_id.contract_id.analytic_tag_ids or line.salary_rule_id.analytic_tag_ids
        return res
    