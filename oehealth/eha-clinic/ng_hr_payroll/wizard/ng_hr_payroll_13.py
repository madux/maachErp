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
import time
from datetime import datetime
from dateutil import relativedelta

from odoo import models, fields, api, _

import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning


class hr_payslip_bonus(models.Model):
    _name = 'hr.payslip.bonus'
    _description = 'Generate payslips for all selected employees for 13month'

    date_start = fields.Date(string='Date From', required=False, default=time.strftime('%Y-%m-01'))
    date_end = fields.Date(string='Date To', required=False,
                           default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    merge = fields.Boolean(string='Consolidate Salary',
                           help='Tick if you do not want to create separate payslip line for 13th month salary')
    percent = fields.Float(string='Percentage', digits=dp.get_precision('Payroll'),
                           help='% should be between 0-1 for eg 0.10 for 10%')
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_bonus_rel', 'bonus_id', 'employee_id',
                                    string='Employees')
    base = fields.Selection(
        selection=[('BASIC', 'Based on Basic'), ('GROSS', 'Based on Gross'), ('NET', 'Based on Net'),
                   ('gross_per', 'Based on % Gross'), ('net_per', 'Based on % Net')], string='Based On', required=False,
        default='BASIC')

    def compute_sheet(self):
        emp_pool = self.env['hr.employee']
        slip_pool = self.env['hr.payslip']
        slip_ids = slip_pool.browse()
        company_id = self.env.user.company_id.thirteen_salary
        if not company_id:
            raise Warning(_(
                'Your company has no policy to give 13th Month Salary, please check your company configuration under setting menu'))
        data = self.read()[0]
        from_date = data['date_start']
        to_date = data['date_end']
        if not data['employee_ids']:
            raise Warning(_('You must select employee(s) to generate payslip(s)'))
        for emp in emp_pool.browse(data['employee_ids']):
            slip_data = slip_pool.onchange_employee_id(from_date, to_date, emp.id, contract_id=False)
            res = {
                'employee_id': emp.id,
                'name': slip_data['value'].get('name', False),
                'struct_id': slip_data['value'].get('struct_id', False),
                'contract_id': slip_data['value'].get('contract_id', False),
                'payslip_run_id': self._context.get('active_id', False),
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids', False)],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids', False)],
                'date_from': from_date,
                'date_to': to_date,
            }
            slip_ids += slip_pool.create(res)
        ctx = dict(self._context or {})
        ctx.update({'bonus': True, 'base': data['base'], 'percent': data['percent'], 'merge': data['merge'], })
        #         slip_ids.compute_sheet()#totoprobuse
        action = self.env.ref('hr_payroll.action_view_hr_payslip_form')
        action_ref = action or False
        result = action_ref.read()[0]
        result['domain'] = "[('id','in', [" + ','.join(map(str, slip_ids.ids)) + "])]"
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
