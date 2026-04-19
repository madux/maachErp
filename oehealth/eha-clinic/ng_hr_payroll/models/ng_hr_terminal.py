# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning


class notice_policy(models.Model):
    _name = 'notice.period'
    _description = 'Terminal Notice Policy'

    name = fields.Char(string='Description', required=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    category_id = fields.Many2one('hr.employee.category', string='Category', required=False)
    days = fields.Float(string='Days', required=False, help='Give the number of days notice period required')
    company_base = fields.Selection(selection=[
        ('basic', 'Basic Salary'),
        ('gross', 'Gross Salary'),
        ('fixed', 'Fix Amount'),
        ('', '')], string='Company Payment Basis', select=False, default='fixed')
    emp_base = fields.Selection(selection=[
        ('basic', 'Basic Salary'),
        ('gross', 'Gross Salary'),
        ('fixed', 'Fix Amount'),
        ('', '')], string='Employee Payment Basis', select=False, default='fixed')
    notes = fields.Text(string='Notes')
    company_value = fields.Float(string='Company Value',
                                 help='If Basis is Fixed Amount, then set value as a fixed amount.')
    emp_value = fields.Float(string='Employee Value',
                             help='If Basis is Fixed Amount, then set value as a fixed amount.')


class terminal_policy(models.Model):
    _name = 'terminal.policy'
    _description = 'Terminal Benefit Policy'

    name = fields.Char(string='Name', required=False)
    code = fields.Char(string='Code')
    allowance_ids = fields.Many2many('hr.salary.rule', 'terminal_allow_rel', 'terminal_id', 'allow_id',
                                     string='Allowances')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    base = fields.Selection(selection=[
        ('basic', 'Basic Salary'),
        ('gross', 'Gross Salary'),
        ('allow', 'Allowances'),
        ('fixed', 'Fix Amount'),
        ('', '')], string='Based On', required=False, index=True, default='fixed')
    value = fields.Float(string='Value', required=False,
                         help='For Basic/ Gross enter ratio between 0 and 1. If Basis is Fixed Amount, then set value as a fixed amount.')
    years = fields.Float(string='Qualification',
                         help='The qualification is minimum number of years to stay with the company before employee is entitled to terminal benefits.')
    value_month = fields.Float(string='Month Value',
                               help='Enter number of months terminal pay due based on years completed with the company.')
    retrospect = fields.Boolean(string='Retrospect',
                                help='Tick is you want to count the years from employment date otherwise it will count from qualified date.')

    @api.constrains('value')
    def _check_value(self):
        if self.value == 0:
            raise Warning(_('Value should not be set to 0'))
        return True


class hr_employee_category(models.Model):
    _inherit = 'hr.employee.category'
    _description = 'Employee Category'

    terminal_policy = fields.Many2one('terminal.policy', string='Terminal Policy')


class hr_employee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    terminal_policy = fields.Many2one('terminal.policy', string='Terminal Policy')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
