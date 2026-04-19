# -*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://odoo.com>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

from odoo import models, fields, api, _


class yearly_salary_detail(models.TransientModel):
    _name = 'yearly.salary.detail'
    _description = 'Hr Salary Employee By Category Report'

    employee_ids = fields.Many2many('hr.employee', 'payroll_emp_rel', 'payroll_id', 'employee_id', string='Employees',
                                    required=False)
    date_from = fields.Date(string='Start Date', required=False, default=time.strftime('%Y-01-01'))
    date_to = fields.Date(string='End Date', required=False, default=time.strftime('%Y-%m-%d'))

    def print_report(self, data):
        """
         To get the date and print the report
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: return report
        """
        context = dict(self._context or {})
        active_ids = self.env.context.get('active_ids', [])

        res = self.read()
        res = res and res[0] or {}
        datas = {'ids': active_ids}
        datas.update({'form': res, })
        #        return {
        #            'type': 'ir.actions.report.xml',
        #            'report_name': 'salary.detail.byyear.ng',
        #            'datas': datas,
        #       }
        return self.env['report'].get_action(self, 'ng_hr_payroll.yearly_salary_ng_report', data=datas)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
