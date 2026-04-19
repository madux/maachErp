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

import time
from datetime import datetime
from dateutil import relativedelta
from odoo.osv import osv

from odoo import models, fields, api, _


class contribution_register_employee(models.TransientModel):
    _name = 'contribution.register.employee'
    _description = 'Contribution Registers by Employee'

    employee_ids = fields.Many2many('hr.employee', 'emp_reg_rel', 'employee_id', 'wiz_id', string="Employees",
                                    required=False)
    date_from = fields.Date(string='Date From', required=False, default=time.strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=False,
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    def print_report(self):
        datas = {
            'ids': self._context.get('active_ids', []),
            'model': 'hr.contribution.register',
            'form': self.read()[0]
        }
        #        return {
        #            'type': 'ir.actions.report.xml',
        #            'report_name': 'contribution.register',
        #            'datas': datas,
        #        }
        return self.env['report'].get_action(self, 'ng_hr_payroll.contribution_register_emp_report', data=datas)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
