# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Mattobell (<http://www.mattobell.com>)
#    Copyright (C) 2010-Today OpenERP SA (<http://www.odoo.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from odoo import models, fields, api, _


class company(models.Model):
    _inherit = 'res.company'
    _description = 'Company'

    thirteen_salary = fields.Boolean(
        string='13 Month Salary',
        help='Tick if your company provide thirteen month salary to employees',
    )
    union_policy = fields.Many2many(
        'union.policy',
        'company_policy_rel',
        'company_id',
        'union_id',
        string='Union Policies',
    )
    notice_period = fields.Float(string='Notice Period by Employee', help='In Months')
    terminal_policy = fields.Many2one('terminal.policy', string='Terminal Policy')
    company_notice_period = fields.Float(string='Notice Period by Employer', help='In Months')
    no_payroll_run = fields.Integer(string='Total Number of Payroll', default=1,
                                    help='Please specify total number of payroll company can run in month for single employee or batch of employee')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
