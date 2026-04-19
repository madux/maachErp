# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from odoo import models, fields, api, _


class payslip_lines_contribution_register(models.TransientModel):
    _inherit = 'payslip.lines.contribution.register'
    _description = 'PaySlip Lines by Contribution Registers'

    employee_ids = fields.Many2many('hr.employee', 'emp_reg_rel_employee', 'employee_id', 'wiz_id', string='Employees')

    def print_report(self):
        datas = {
            'ids': self._context.get('active_ids', []),
            'model': 'hr.contribution.register',
            'form': self.read()[0]
        }
        #        return {
        #            'type': 'ir.actions.report.xml',
        #            'report_name': 'contribution.register.lines.employee',
        #            'datas': datas,
        #        }
        return self.env['report'].get_action(self, 'ng_hr_payroll.contribution_register_mod_report', data=datas)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
