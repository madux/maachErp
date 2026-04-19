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

from odoo import models, fields, api, _


class yearly_carry_fw(models.Model):
    _name = 'carry.fw'
    _description = 'carry.fw'

    date_from = fields.Date(string='Start Date', required=False, help='Start date of last year',
                            default=time.strftime('%Y-01-01'))
    date_to = fields.Date(string='End Date', required=False, help='End date of last year')
    type = fields.Selection(selection=[('all', 'All'), ('none', 'None'), ('few', 'Number Of Days')], string='Type',
                            required=False, default='all')
    days = fields.Integer(string='Days to Carry Forward', default=0)

    def carry_fw(self):  # already override to ng_hr_hgolidays module..
        alloc = {}
        leaves = {}
        holiday_obj = self.env['hr.leave']
        emp_ids = self.env['hr.employee'].search([])
        type_ids = self.env['hr.leave.type'].search([('can_carryfw', '=', True)])

        allocation_ids = holiday_obj.search(
            [('holiday_type', '=', 'employee'), ('state', 'in', ('validate', 'validate1')), ('type', '=', 'add'),
             ('holiday_status_id', 'in', type_ids.ids), ('carry_fw', '=', False)])
        type_ids = []
        for a in allocation_ids:
            alloc[a.holiday_status_id.id] = a.number_of_days
            type_ids.append(a.holiday_status_id.id)

        for e in emp_ids:
            for t in allocation_ids:
                if not e.id in leaves:
                    leaves[e.id] = {}
                if t.holiday_type == 'employee' and t.employee_id.id == e.id:
                    if not t.holiday_status_id.id in leaves[e.id]:
                        leaves[e.id].update({t.holiday_status_id.id: t.number_of_days})
                    else:
                        leaves[e.id][t.holiday_status_id.id] += t.number_of_days
                #                elif t.holiday_type == 'category':
                #                    cr.execute('select emp_id, category_id from employee_category_rel where emp_id = %s and category_id = %s ', (e.id, t.category_id.id))
                #                    if cr.fetchall():
                #                        if not t.holiday_status_id.id in leaves[e.id]:
                #                            leaves[e.id].update({t.holiday_status_id.id: t.number_of_days_temp})
                #                        else:
                #                            leaves[e.id][t.holiday_status_id.id] += t.number_of_days_temp
                else:
                    pass

        res = self.read()
        res = res and res[0] or {}

        leave_ids = holiday_obj.search(
            [('date_from', '>=', res['date_from']), ('date_to', '<=', res['date_to']), ('type', '=', 'remove'),
             ('holiday_status_id', 'in', type_ids), ('state', 'in', ('validate', 'validate1'))])
        leaves1 = {}
        hlist = []
        for l in leave_ids:
            if not l.employee_id.id in leaves1:
                leaves1[l.employee_id.id] = {}
            if not l.holiday_status_id.id in leaves1[l.employee_id.id]:
                leaves1[l.employee_id.id][l.holiday_status_id.id] = l.number_of_days
            else:
                leaves1[l.employee_id.id][l.holiday_status_id.id] += l.number_of_days
        for t, m in leaves.items():
            for k, s in m.items():
                if not t in leaves1:
                    name = 'Carry Forwarded ' + self.env['hr.leave.type'].browse(k)[0].name
                    vals = {'employee_id': t, 'holiday_status_id': k, 'name': name, 'carry_fw': True,
                            'number_of_days': s, 'notes': 'Carry Forward leave'}
                    holiday_id = holiday_obj.create(vals)
                    hlist.append(holiday_id.id)
                elif t in leaves1:
                    if leaves1[t][k] == s:
                        pass
                    if leaves1[t][k] < s:
                        diff = s - leaves1[t][k]
                        name = 'Carry Forwarded ' + self.env['hr.leave.type'].browse(k).name
                        vals = {'state': 'draft', 'employee_id': t, 'holiday_status_id': k, 'name': name,
                                'carry_fw': True, 'number_of_days': diff, 'notes': 'Carry Forward leave'}
                        holiyday_id = holiday_obj.create(vals)
                        hlist.append(holiyday_id.id)
        result = self.env.ref('hr_holidays.open_allocation_holidays')
        action_ref = result or False
        result = action_ref.read()[0]
        result['domain'] = "[('id','in', [" + ','.join(map(str, hlist)) + "])]"
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
