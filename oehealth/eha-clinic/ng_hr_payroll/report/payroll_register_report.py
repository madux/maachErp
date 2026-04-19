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
import datetime
from odoo import api, fields, models


class payroll_register_report(models.AbstractModel):
    _name = "report.ng_hr_payroll.payroll_register_report"

    mnths = []
    mnths_total = []
    rules = []
    rules_data = []

    total = 0.0

    def get_periods(self, form):
        #       Get start year-month-date and end year-month-date
        #        first_year = int(form['start_date'][0:4])
        #        last_year = int(form['end_date'][0:4])
        #
        #        first_month = int(form['start_date'][5:7])
        #        last_month = int(form['end_date'][5:7])
        #        no_months = (last_year-first_year) * 12 + last_month - first_month + 1
        #        current_month = first_month
        #        current_year = first_year
        #
        ##       Get name of the months from integer
        #        mnth_name = []
        #        for count in range(0, no_months):
        #            m = datetime.date(current_year, current_month, 1).strftime('%b')
        #            mnth_name.append(m)
        #            self.mnths.append(str(current_month) + '-' + str(current_year))
        #            if current_month == 12:
        #                current_month = 0
        #                current_year = last_year
        #            current_month = current_month + 1
        #        for c in range(0, (12-no_months)):
        #            mnth_name.append('None')
        #            self.mnths.append('None')
        #

        mnth_name = []
        rules = []
        #        category_id = form.get('category_id', [])
        #        category_id = category_id and category_id[0] or False
        #        rule_ids = self.pool.get('hr.salary.rule').search(self.cr, self.uid, [('category_id', '=', category_id)])
        rule_ids = form.get('rule_ids', [])
        if rule_ids:
            for r in self.env['hr.salary.rule'].browse(rule_ids):
                mnth_name.append(r.name)
                rules.append(r.id)
        self.rules = rules
        self.rules_data = mnth_name
        return [mnth_name]

    def get_salary(self, form, emp_id, emp_salary, total_mnths):
        #        category_id = form.get('category_id', [])
        #        category_id = category_id and category_id[0] or False

        #        self.cr.execute("select to_char(date_to,'mm-yyyy') as to_date ,sum(pl.total) \
        #                             from hr_payslip_line as pl \
        #                             left join hr_payslip as p on pl.slip_id = p.id \
        #                             left join hr_employee as emp on emp.id = p.employee_id \
        #                             left join resource_resource as r on r.id = emp.resource_id  \
        #                            where p.state = 'done' and p.employee_id = %s and pl.category_id = %s \
        #                            group by r.name, p.date_to,emp.id",(emp_id, category_id,))
        #
        #        sal = self.cr.fetchall()
        #        salary = dict(sal)
        #        total = 0.0
        #        cnt = 1
        #        for month in self.mnths:
        #            if month <> 'None':
        #                if len(month) != 7:
        #                    month = '0' + str(month)
        #                if month in salary and salary[month]:
        #                    emp_salary.append(salary[month])
        #                    total += salary[month]
        #                    total_mnths[cnt] = total_mnths[cnt] + salary[month]
        #                else:
        #                    emp_salary.append(0.00)
        #            else:
        #                emp_salary.append('')
        #                total_mnths[cnt] = ''
        #            cnt = cnt + 1
        #

        #        emp_obj = self.pool.get('hr.employee')
        #        eid = emp_obj.browse(self.cr, self.uid, emp_id, context=self.context)
        #        emp_salary.append(eid.name)
        total = 0.0
        cnt = 0
        flag = 0
        #        for r in self.rules:
        for r in self.env['hr.salary.rule'].browse(self.rules):
            #            self.cr.execute("select pl.name as name ,pl.total \
            #                                 from hr_payslip_line as pl \
            #                                 left join hr_payslip as p on pl.slip_id = p.id \
            #                                 left join hr_payslip_run as pr on pr.id = p.payslip_run_id \
            #                                 left join hr_employee as emp on emp.id = p.employee_id \
            #                                 left join resource_resource as r on r.id = emp.resource_id  \
            #                                where p.employee_id = %s and pl.salary_rule_id = %s \
            #                                and (p.date_from >= %s) AND (p.date_to <= %s) \
            #                                and (pr.state != 'cancel')\
            #                                group by pl.total,r.name, pl.name,emp.id",(emp_id, r, form.get('start_date', False), form.get('end_date', False),))
            self._cr.execute("select pl.name as name ,pl.total \
                                 from hr_payslip_line as pl \
                                 left join hr_payslip as p on pl.slip_id = p.id \
                                 left join hr_employee as emp on emp.id = p.employee_id \
                                 left join resource_resource as r on r.id = emp.resource_id  \
                                where p.employee_id = %s and pl.salary_rule_id = %s \
                                and (p.date_from >= %s) AND (p.date_to <= %s) \
                                group by pl.total,r.name, pl.name,emp.id",
                             (emp_id, r.id, form.get('start_date', False), form.get('end_date', False),))
            sal = self._cr.fetchall()
            salary = dict(sal)
            cnt += 1
            flag += 1
            if flag > 8:
                continue
            if r.name in salary:
                emp_salary.append(salary[r.name])
                total += salary[r.name]
                total_mnths[cnt] = total_mnths[cnt] + salary[r.name]
            else:
                emp_salary.append('')
        #                total_mnths[cnt] = 0.0
        #            total = 0.0
        #            cnt = 1
        #            for month in self.rules_data:
        #                if month <> 'None':
        #                    if len(month) != 7:
        #                        month = '0' + str(month)
        #                    if month in salary and salary[month]:
        #                        emp_salary.append(salary[month])
        #                        total += salary[month]
        #                        total_mnths[cnt] = total_mnths[cnt] + salary[month]
        #                    else:
        #                        emp_salary.append(0.00)
        #                else:
        #                    emp_salary.append('')
        #                    total_mnths[cnt] = ''
        #                cnt = cnt + 1

        if len(self.rules) < 8:
            diff = 8 - len(self.rules)
            for x in range(0, diff):
                emp_salary.append('')
        return emp_salary, total, total_mnths

    def get_salary1(self, form, emp_id, emp_salary, total_mnths):
        #        category_id = form.get('category_id', [])
        #        category_id = category_id and category_id[0] or False

        #        self.cr.execute("select to_char(date_to,'mm-yyyy') as to_date ,sum(pl.total) \
        #                             from hr_payslip_line as pl \
        #                             left join hr_payslip as p on pl.slip_id = p.id \
        #                             left join hr_employee as emp on emp.id = p.employee_id \
        #                             left join resource_resource as r on r.id = emp.resource_id  \
        #                            where p.state = 'done' and p.employee_id = %s and pl.category_id = %s \
        #                            group by r.name, p.date_to,emp.id",(emp_id, category_id,))
        #
        #        sal = self.cr.fetchall()
        #        salary = dict(sal)
        #        total = 0.0
        #        cnt = 1
        #        for month in self.mnths:
        #            if month <> 'None':
        #                if len(month) != 7:
        #                    month = '0' + str(month)
        #                if month in salary and salary[month]:
        #                    emp_salary.append(salary[month])
        #                    total += salary[month]
        #                    total_mnths[cnt] = total_mnths[cnt] + salary[month]
        #                else:
        #                    emp_salary.append(0.00)
        #            else:
        #                emp_salary.append('')
        #                total_mnths[cnt] = ''
        #            cnt = cnt + 1
        #

        #        emp_obj = self.pool.get('hr.employee')
        #        eid = emp_obj.browse(self.cr, self.uid, emp_id, context=self.context)
        #        emp_salary.append(eid.name)
        total = 0.0
        cnt = 0
        flag = 0
        for r in self.env['hr.salary.rule'].browse(self.rules):
            #        for r in self.rules:
            #            rname = self.pool.get('hr.salary.rule').browse(self.cr, self.uid, r)
            #            self.cr.execute("select pl.name as name ,pl.total \
            #                                 from hr_payslip_line as pl \
            #                                 left join hr_payslip as p on pl.slip_id = p.id \
            #                                 left join hr_payslip_run as pr on pr.id = p.payslip_run_id \
            #                                 left join hr_employee as emp on emp.id = p.employee_id \
            #                                 left join resource_resource as r on r.id = emp.resource_id  \
            #                                where p.employee_id = %s and pl.salary_rule_id = %s \
            #                                and (p.date_from >= %s) AND (p.date_to <= %s) \
            #                                and (pr.state != 'cancel')\
            #                                group by pl.total,r.name, pl.name,emp.id",(emp_id, r, form.get('start_date', False), form.get('end_date', False),))
            self._cr.execute("select pl.name as name ,pl.total \
                                 from hr_payslip_line as pl \
                                 left join hr_payslip as p on pl.slip_id = p.id \
                                 left join hr_employee as emp on emp.id = p.employee_id \
                                 left join resource_resource as r on r.id = emp.resource_id  \
                                where p.employee_id = %s and pl.salary_rule_id = %s \
                                and (p.date_from >= %s) AND (p.date_to <= %s) \
                                group by pl.total,r.name, pl.name,emp.id",
                             (emp_id, r.id, form.get('start_date', False), form.get('end_date', False),))

            sal = self._cr.fetchall()
            salary = dict(sal)
            cnt += 1
            flag += 1
            #            if flag > 8:
            #                continue
            if r.name in salary:
                emp_salary.append(salary[r.name])
                total += salary[r.name]
                total_mnths[cnt] = total_mnths[cnt] + salary[r.name]
            else:
                emp_salary.append('')
        #                total_mnths[cnt] = 0.0
        #            total = 0.0
        #            cnt = 1
        #            for month in self.rules_data:
        #                if month <> 'None':
        #                    if len(month) != 7:
        #                        month = '0' + str(month)
        #                    if month in salary and salary[month]:
        #                        emp_salary.append(salary[month])
        #                        total += salary[month]
        #                        total_mnths[cnt] = total_mnths[cnt] + salary[month]
        #                    else:
        #                        emp_salary.append(0.00)
        #                else:
        #                    emp_salary.append('')
        #                    total_mnths[cnt] = ''
        #                cnt = cnt + 1

        #        if len(self.rules) < 8:
        #            diff = 8 - len(self.rules)
        #            for x in range(0,diff):
        #                emp_salary.append('')
        return emp_salary, total, total_mnths

    def get_employee(self, form, excel=False):
        emp_salary = []
        salary_list = []
        total_mnths = ['Total', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # only for pdf report!
        emp_obj = self.env['hr.employee']
        emp_ids = form.get('employee_ids', [])

        total_excel_months = ['Total', ]  # for excel report
        for r in range(0, len(self.rules)):
            total_excel_months.append(0)
        employees = emp_obj.browse(emp_ids)
        for emp_id in employees:
            emp_salary.append(emp_id.name)
            total = 0.0
            if excel:
                emp_salary, total, total_mnths = self.get_salary1(form, emp_id.id, emp_salary,
                                                                  total_mnths=total_excel_months)
            else:
                emp_salary, total, total_mnths = self.get_salary(form, emp_id.id, emp_salary, total_mnths)
            emp_salary.append(total)
            salary_list.append(emp_salary)
            emp_salary = []
        self.mnths_total.append(total_mnths)
        return salary_list

    def get_months_tol(self):
        return self.mnths_total

    def get_total(self):
        for item in self.mnths_total:
            for count in range(1, len(item)):
                if item[count] == '':
                    continue
                self.total += item[count]
        return self.total

    @api.model
    def render_html(self, docids, data=None):
        docs = self.env['hr.employee'].browse(data['form']['employee_ids'])
        docargs = {
            'time': time,
            'get_employee': self.get_employee,
            'get_periods': self.get_periods,
            'get_months_tol': self.get_months_tol,
            'get_total': self.get_total,
            'doc_ids': data['form']['employee_ids'],
            'doc_model': 'hr.employee',
            'docs': docs,
            'data': data,
            'company': self.env.user.company_id
        }
        return self.env['report'].render('ng_hr_payroll.payroll_register_report', values=docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
