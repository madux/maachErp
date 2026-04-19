#!/usr/bin/env python
# -*- coding:utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
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
from datetime import datetime
from dateutil import relativedelta
from odoo import api, fields, models


class contrib_reg_employee_report(models.AbstractModel):
    _name = "report.ng_hr_payroll.contribution_register_emp_report"

    sum_total_grand_amount = 0.0

    def _get_objects(self, data):
        return self.env['hr.contribution.register'].browse(data['ids'])

    def set_context(self, objects, data, ids, report_type=None):
        self.date_from = data['form'].get('date_from', time.strftime('%Y-%m-%d'))
        self.date_to = data['form'].get('date_to',
                                        str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[
                                        :10])
        return super(contrib_reg_employee_report, self).set_context(objects, data, ids, report_type=report_type)

    def sum_total(self):
        self.sum_total_grand_amount += self.regi_total
        return self.regi_total

    def sum_total_grand(self):
        return self.sum_total_grand_amount

    def _get_emp(self, emp_id):
        return self.env['hr.employee'].browse(emp_id)

    def _get_payslip_lines(self, obj, employee, data):
        payslip_obj = self.env['hr.payslip']
        payslip_line = self.env['hr.payslip.line']
        payslip_lines = []
        res = []
        self.regi_total = 0.0
        self._cr.execute("SELECT pl.id from hr_payslip_line as pl " \
                         "LEFT JOIN hr_payslip AS hp on (pl.slip_id = hp.id) " \
                         "WHERE (hp.date_from >= %s) AND (hp.date_to <= %s) " \
                         "AND pl.register_id = %s " \
                         "AND hp.state = 'done' " \
                         "AND pl.employee_id = %s " \
                         "ORDER BY pl.slip_id, pl.sequence",
                         (data['date_from'], data['date_to'], obj.id, employee))

        payslip_lines = [x[0] for x in self._cr.fetchall()]
        for line in payslip_line.browse(payslip_lines):
            res.append({
                'employee': line.employee_id.name,
                'payslip_name': line.slip_id.number,
                'name': line.name,
                'code': line.code,
                'quantity': line.quantity,
                'amount': line.amount,
                'total': line.total,
            })
            self.regi_total += line.total
        return res

    @api.model
    def render_html(self, docids, data=None):
        docs = self.env[data['model']].browse(data['ids'])
        docargs = {
            'get_emp': self._get_emp,
            'get_payslip_lines': self._get_payslip_lines,
            'sum_total': self.sum_total,
            'sum_total_grand': self.sum_total_grand,
            'get_objects': docs,
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'data': data,
            'docs': docs,
            'company': self.env.user.company_id
        }
        return self.env['report'].render('ng_hr_payroll.contribution_register_emp_report', values=docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
