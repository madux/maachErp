# -*- coding: utf-8 -*-
import math

import time
from datetime import timedelta
import datetime


from odoo import models, fields, api, _
from odoo import tools
from odoo.exceptions import Warning


class employee(models.Model):
    _inherit = 'hr.employee'

    
    @api.depends('remaining_leaves', 'remaining_leaves_nonlegal', 'leave_ids_emp')
    def _total_leaves_available(self):
        for hol in self:
            hol.total_available_leaves = hol.remaining_leaves + hol.remaining_leaves_nonlegal

    
    @api.depends('annual_leave', 'carryfw_leave', 'leave_ids_emp', 'name')
    def _get_remaining_days(self):
        if not self.ids:
            self.remaining_leaves = 0.0
        else:
            query = ('''SELECT
                                sum(h.number_of_days) as days,
                                h.employee_id
                            from
                                hr_leave h
                                join hr_leave_type s on (s.id=h.holiday_status_id)
                            where
                                h.state='validate' and
                                s.is_legal=True and
                                h.carry_fw_ded=False and
                                h.carry_fw_allocation=False and
                                h.leave_request_done=False and
                                h.employee_id in (%s)
                            group by h.employee_id''' % (','.join(map(str, self.ids)),))
            self._cr.execute(query)

            res = self._cr.dictfetchone()
            if res:
                self.remaining_leaves = res['days']

    
    @api.depends('annual_leave', 'carryfw_leave', 'leave_ids_emp', 'name')
    def _get_remaining_days_non(self):
        if not self.ids:
            self.remaining_leaves_nonlegal = 0.0
        else:
            self._cr.execute('''SELECT
                    sum(h.number_of_days) as days,
                    h.employee_id
                from
                    hr_leave h
                    join hr_leave_type s on (s.id=h.holiday_status_id)
                where
                    h.state='validate' and
                    s.is_legal=False and
                    h.employee_id in (%s)
                group by h.employee_id''' % (','.join(map(str, self.ids)),))

            res = self._cr.dictfetchone()
            if res:
                self.remaining_leaves_nonlegal = res['days']

    
    def _set_remaining_days(self, value):
        diff = value - self.remaining_leaves
        type_obj = self.env['hr.leave.type']
        holiday_obj = self.env['hr.leave']
        # Find for holidays status
        status_ids = type_obj.search([('limit', '=', False)], limit=1)
        status_id = status_ids and status_ids.id or False
        if not status_id:
            return False
        if diff > 0:
            leave_id = holiday_obj.create({'name': _('Allocation for %s') % self.name, 'employee_id': self.id,
                                           'holiday_status_id': status_id, 'type': 'add', 'holiday_type': 'employee', 'number_of_days': diff})
        elif diff < 0:
            leave_id = holiday_obj.create({'name': _('Leave Request for %s') % self.name, 'employee_id': self.id,
                                           'holiday_status_id': status_id, 'type': 'remove', 'holiday_type': 'employee', 'number_of_days': abs(diff)})
        else:
            #            leave_id = holiday_obj.create(cr, uid, {'name': _('Carry forward settele Leave Request for %s') % employee.name, 'employee_id': employee.id, 'holiday_status_id': status_id, 'type': 'remove', 'holiday_type': 'employee', 'number_of_days_temp': value}, context=context)
            return False
        leave_id.signal_workflow('confirm')
        leave_id.signal_workflow('validate')
        leave_id.signal_workflow('second_validate')
        return True

    
    def _set_remaining_days_non(self, value):
        diff = value - self.remaining_leaves_nonlegal
        type_obj = self.env['hr.leave.type']
        holiday_obj = self.env['hr.leave']
        # Find for holidays status
        status_ids = type_obj.search([('limit', '=', False)], limit=1)
#        if len(status_ids) != 1 :
#            raise osv.except_osv(_('Warning!'),_("The feature behind the field 'Remaining Legal Leaves' can only be used when there is only one leave type with the option 'Allow to Override Limit' unchecked. (%s Found). Otherwise, the update is ambiguous as we cannot decide on which leave type the update has to be done. \nYou may prefer to use the classic menus 'Leave Requests' and 'Allocation Requests' located in 'Human Resources \ Leaves' to manage the leave days of the employees if the configuration does not allow to use this field.") % (len(status_ids)))
        status_id = status_ids and status_ids.id or False
        if not status_id:
            return False
        if diff > 0:
            leave_id = holiday_obj.create({'name': _('Allocation for %s') % self.name, 'employee_id': self.id,
                                           'holiday_status_id': status_id, 'type': 'add', 'holiday_type': 'employee', 'number_of_days': diff})
        elif diff < 0:
            leave_id = holiday_obj.create({'name': _('Leave Request for %s') % self.name, 'employee_id': self.id,
                                           'holiday_status_id': status_id, 'type': 'remove', 'holiday_type': 'employee', 'number_of_days': abs(diff)})
        else:
            return False
        leave_id.signal_workflow('confirm')
        leave_id.signal_workflow('validate')
        leave_id.signal_workflow('second_validate')
        return True

    annual_leave = fields.Float(string='Annual Leave', default=0.0)
    carryfw_leave = fields.Float(string='Carried Forward Leave', readonly=True, default=0.0)
    total_available_leaves = fields.Float(
        compute='_total_leaves_available', store=True, string='Total Available Leave')

    remaining_leaves = fields.Float(compute='_get_remaining_days', string='Remaining Legal Leaves',
                                    help='Total number of legal leaves allocated to this employee, change this value to create allocation/leave request. Total based on all the leave types without overriding limit.', store=True, readonly=True)
    remaining_leaves_nonlegal = fields.Float(
        compute='_get_remaining_days_non', string='Remaining Non-Legal Leaves', store=True)

    leave_ids_emp = fields.One2many('hr.leave', 'employee_id',
                                    string='Employee Leaves', readonly=True)


class leaves(models.Model):
    _inherit = 'hr.leave'

    annual_leave = fields.Float(related='employee_id.annual_leave',
                                string='Annual Entitled Leave', store=True)
    leave_request_done = fields.Boolean(string='Leave Request Done', readonly=True)

    @api.model
    def _check_date(self):
        # Hide this warning for carry fw wizard.... moved to create and write with conditions...
        #        for holiday in self.browse(cr, uid, ids):
        #            holiday_ids = self.search(cr, uid, [('date_from', '<=', holiday.date_to), ('date_to', '>=', holiday.date_from), ('employee_id', '=', holiday.employee_id.id), ('id', '<>', holiday.id)])
        #            if holiday_ids:
        #                return False
        return True

    @api.model
    def create(self, vals):
        if self._context and not 'carry_fw' in self._context and 'number_of_days' in vals:
            if (vals['number_of_days'] < 0.0 or vals['number_of_days'] == 0.0):
                raise Warning(_('Error! Please enter a positive number for Allocation/Leave days!'))

        if self._context and not 'carry_fw' in self._context and 'date_from' in vals:
            #            self.search(cr, uid, [('date_from', '<=', vals['date_to']), ('date_to', '>=', vals['date_from']), ('employee_id', '=', vals['employee_id']), ('id', '<>', holiday.id)])
            hids = self.search([('date_from', '<=', vals['date_to']), ('date_to',
                                                                       '>=', vals['date_from']), ('employee_id', '=', vals['employee_id'])])
            if hids:
                raise Warning(_('Error! You can not have 2 leaves that overlaps on same day!'))
        return super(leaves, self).create(vals)

    
    def write(self, vals):
        if self._context and not 'carry_fw' in self._context and 'number_of_days' in vals:
            if (vals['number_of_days'] < 0.0 or vals['number_of_days'] == 0.0):
                raise Warning(_('Error! Please enter a positive number for Allocation/Leave days!'))
        brow = self
        if self._context and not 'carry_fw' in self._context and 'date_from' in vals and 'date_to' in vals:
            hids = self.search([('date_from', '<=', vals['date_to']), ('date_to', '>=', vals['date_from']),
                                ('employee_id', '=', brow.employee_id.id), ('id', '<>', self.ids[0])])
            if hids:
                raise Warning(_('Error! You can not have 2 leaves that overlaps on same day!'))
        elif self._context and not 'carry_fw' in self._context and 'date_from' in vals and not 'date_to' in vals:
            hids = self.search([('date_from', '<=', brow.date_to), ('date_to', '>=', vals['date_from']),
                                ('employee_id', '=', brow.employee_id.id), ('id', '<>', self.ids[0])])
            if hids:
                raise Warning(_('Error! You can not have 2 leaves that overlaps on same day!'))
        elif self._context and not 'carry_fw' in self._context and not 'date_from' in vals and 'date_to' in vals:
            hids = self.search([('date_from', '<=', vals['date_to']), ('date_to', '>=', brow.date_from),
                                ('employee_id', '=', brow.employee_id.id), ('id', '<>', self.ids[0])])
            if hids:
                raise Warning(_('Error! You can not have 2 leaves that overlaps on same day!'))

        for s in self:
            # Setting: Since name is depend on function fields.
            # remaining_leaves_nonlegal and remaining_leaves So that it can update on
            # employee form. 21march2015 probuse
            s.employee_id.write({'name': s.employee_id.name})
        return super(leaves, self).write(vals)

     # _constraints = [(_check_date, 'You can not have 2 leaves that overlaps
     # on same day!', ['date_from', 'date_to'])     ] #probusetodo


class yearly_carry_fw(models.Model):
    _inherit = 'carry.fw'
    _description = 'carry.fw leaves entry on employee record.'

    
    def carry_fw(self):
        ctx = dict(self._context)
        ctx.update({'carry_wizard': True})
        alloc = {}
        leaves = {}
        holiday_obj = self.env['hr.leave']
        emp_ids = self.env['hr.employee'].search([])
        emp_ids.with_context(ctx).write({})
        type_ids = self.env['hr.leave.type'].search([('can_carryfw', '=', True)])

        allocation_ids = holiday_obj.search([('carry_fw_allocation', '=', False), ('holiday_type', '=', 'employee'), ('state', 'in', (
            'validate', 'validate1')), ('type', '=', 'add'), ('holiday_status_id', 'in', type_ids.ids), ('carry_fw', '=', False)])

        self._cr.execute(
            'update hr_leave set carry_fw_allocation=False where carry_fw_allocation is Null')
        self._cr.execute('update hr_leave set carry_fw_ded=False where carry_fw_ded is Null')

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
                else:
                    pass

        res = self.read()
        res = res and res[0] or {}

        leave_ids = holiday_obj.search([('carry_fw_ded', '=', False), ('date_from', '>=', res['date_from']), ('date_to', '<=', res['date_to']), ('type', '=', 'remove'), ('holiday_status_id', 'in', type_ids), ('state', 'in', ('validate', 'validate1'))])
        leaves1 = {}
        hlist = []
        for l in leave_ids:
            if not l.employee_id.id in leaves1:
                leaves1[l.employee_id.id] = {}
            if not l.holiday_status_id.id in leaves1[l.employee_id.id]:
                leaves1[l.employee_id.id][l.holiday_status_id.id] = l.number_of_days
            else:
                leaves1[l.employee_id.id][l.holiday_status_id.id] += l.number_of_days

        number_of_days_carry = res['days']
        if res['type'] == 'none':
            for t, m in leaves.items():
                for k, s in m.items():
                    if not t in leaves1:
                        name = 'Carry Forwarded Deduction for old Allocation / ' + \
                            self.env['hr.leave.type'].browse(k).name
                        vals1 = {'carry_fw_ded': True, 'employee_id': t, 'holiday_status_id': k, 'date_from': time.strftime('%Y-%m-%d %H:%M:%S'), 'date_to': time.strftime(
                            '%Y-%m-%d %H:%M:%S'), 'name': name, 'type': 'remove', 'carry_fw': False, 'number_of_days': s, 'notes': 'Carry Forward leave'}
                        io = holiday_obj.with_context(ctx).create(vals1)
                        hlist.append(io)
                        io.signal_workflow('confirm')
                        io.signal_workflow('validate')
                        io.signal_workflow('second_validate')

                    elif t in leaves1:
                        if k in leaves1[t]:
                            if leaves1[t][k] == s:
                                pass
                            if leaves1[t][k] < s:
                                diff = s - leaves1[t][k]
                                name = 'Carry Forwarded Deduction for Old Allocation / ' + \
                                    self.env['hr.leave.type'].browse(k).name
                                vals1 = {'carry_fw_ded': True, 'state': 'draft', 'employee_id': t, 'holiday_status_id': k, 'date_from': time.strftime(
                                    '%Y-%m-%d %H:%M:%S'), 'date_to': time.strftime('%Y-%m-%d %H:%M:%S'), 'type': 'remove', 'name': name, 'carry_fw': False, 'number_of_days': diff, 'notes': 'Carry Forward leave'}
                                io = holiday_obj.with_context(ctx).create(vals1)
                                hlist.append(io)
                                io.signal_workflow('confirm')
                                io.signal_workflow('validate')
                                io.signal_workflow('second_validate')
                        else:
                            pass
                            # situaction where you are directly using the leave request without any allocation request.. like sick leave ..i can put sick leave even if i do not have allocation for that
                            # in this case lets skip that carry forward part...

        elif res['type'] == 'all':
            for t, m in leaves.items():
                for k, s in m.items():
                    if not t in leaves1:
                        name = 'Carry Forwarded ' + self.env['hr.leave.type'].browse(k).name
                        vals = {'employee_id': t, 'holiday_status_id': k, 'type': 'add', 'name': name,
                                'carry_fw': True, 'number_of_days': s, 'notes': 'Carry Forward leave'}
                        io1 = holiday_obj.with_context(ctx).create(vals)
                        hlist.append(io1)
                        io1.signal_workflow('confirm')
                        io1.signal_workflow('validate')
                        io1.signal_workflow('second_validate')

                        name = 'Carry Forwarded Deduction for old Allocation / ' + \
                            self.env['hr.leave.type'].browse(k).name
                        vals1 = {'carry_fw_ded': True, 'employee_id': t, 'holiday_status_id': k, 'date_from': time.strftime('%Y-%m-%d %H:%M:%S'), 'date_to': time.strftime(
                            '%Y-%m-%d %H:%M:%S'), 'type': 'remove', 'name': name, 'carry_fw': False, 'number_of_days': s, 'notes': 'Carry Forward leave'}
                        io = holiday_obj.with_context(ctx).create(vals1)
                        hlist.append(io)
                        io.signal_workflow('confirm')
                        io.signal_workflow('validate')
                        io.signal_workflow('second_validate')

                        emp = self.env['hr.employee'].browse(t)
                        carry = emp.carryfw_leave + s  # new
                        emp.with_context(ctx).write({'carryfw_leave': carry})
                    elif t in leaves1:
                        if k in leaves1[t]:
                            if leaves1[t][k] == s:
                                pass
                            if leaves1[t][k] < s:
                                diff = s - leaves1[t][k]
                                name = 'Carry Forwarded ' + \
                                    self.env['hr.leave.type'].browse(k).name
                                vals = {'state': 'draft', 'employee_id': t, 'holiday_status_id': k, 'type': 'add',
                                        'name': name, 'carry_fw': True, 'number_of_days': diff, 'notes': 'Carry Forward leave'}
                                io1 = holiday_obj.with_context(ctx).create(vals)
                                hlist.append(io1)
                                io1.signal_workflow('confirm')
                                io1.signal_workflow('validate')
                                io1.signal_workflow('second_validate')

                                name = 'Carry Forwarded Deduction for Old Allocation / ' + \
                                    self.env['hr.leave.type'].browse(k).name
                                vals1 = {'carry_fw_ded': True, 'state': 'draft', 'employee_id': t, 'holiday_status_id': k, 'date_from': time.strftime(
                                    '%Y-%m-%d %H:%M:%S'), 'date_to': time.strftime('%Y-%m-%d %H:%M:%S'), 'type': 'remove', 'name': name, 'carry_fw': False, 'number_of_days': diff, 'notes': 'Carry Forward leave'}
                                io = holiday_obj.with_context(ctx).create(vals1)
                                hlist.append(io)
                                io.signal_workflow('confirm')
                                io.signal_workflow('validate')
                                io.signal_workflow('second_validate')

                                emp = self.env['hr.employee'].browse(t)
                                carry = emp.carryfw_leave + diff
                                emp.with_context(ctx).write({'carryfw_leave': carry})
                        else:
                            pass
                            # situaction where you are directly using the leave request without any allocation request.. like sick leave ..i can put sick leave even if i do not have allocation for that
                            # in this case lets skip that carry forward part...

        else:  # few option for number of days input for carry fw
            if res['days'] <= 0.0:
                raise Warning(
                    _('Error! Number of days to carry forward should not be zero or less than zero.'))
            for t, m in leaves.items():
                for k, s in m.items():
                    if not t in leaves1:
                        name = 'Carry Forwarded ' + self.env['hr.leave.type'].browse(k).name
                        vals = {'employee_id': t, 'holiday_status_id': k, 'type': 'add', 'name': name,
                                'carry_fw': True, 'number_of_days': number_of_days_carry, 'notes': 'Carry Forward leave'}
                        io1 = holiday_obj.with_context(ctx).create(vals)
                        hlist.append(io1)
                        io1.signal_workflow('confirm')
                        io1.signal_workflow('validate')
                        io1.signal_workflow('second_validate')

                        name = 'Carry Forwarded Deduction for old Allocation / ' + \
                            self.env['hr.leave.type'].browse(k).name
                        vals1 = {'carry_fw_ded': True, 'employee_id': t, 'holiday_status_id': k, 'date_from': time.strftime('%Y-%m-%d %H:%M:%S'), 'date_to': time.strftime(
                            '%Y-%m-%d %H:%M:%S'), 'type': 'remove', 'name': name, 'carry_fw': False, 'number_of_days': s, 'notes': 'Carry Forward leave'}
                        io = holiday_obj.with_context(ctx).create(vals1)
                        hlist.append(io)
                        io.signal_workflow('confirm')
                        io.signal_workflow('validate')
                        io.signal_workflow('second_validate')

                        emp = self.env['hr.employee'].browse(t)
                        carry = emp.carryfw_leave + number_of_days_carry  # new
                        emp.with_context(ctx).write({'carryfw_leave': carry})
                    elif t in leaves1:
                        if k in leaves1[t]:
                            if leaves1[t][k] == s:
                                pass
                            if leaves1[t][k] < s:
                                diff = s - leaves1[t][k]
                                name = 'Carry Forwarded ' + \
                                    self.env['hr.leave.type'].browse(k).name
                                vals = {'state': 'draft', 'employee_id': t, 'holiday_status_id': k, 'type': 'add', 'name': name,
                                        'carry_fw': True, 'number_of_days': number_of_days_carry, 'notes': 'Carry Forward leave'}
                                io1 = holiday_obj.with_context(ctx).create(vals)
                                hlist.append(io1)
                                io1.signal_workflow('confirm')
                                io1.signal_workflow('validate')
                                io1.signal_workflow('second_validate')

                                name = 'Carry Forwarded Deduction for Old Allocation / ' + \
                                    self.env['hr.leave.type'].browse(k).name
                                vals1 = {'carry_fw_ded': True, 'state': 'draft', 'employee_id': t, 'holiday_status_id': k, 'date_from': time.strftime(
                                    '%Y-%m-%d %H:%M:%S'), 'date_to': time.strftime('%Y-%m-%d %H:%M:%S'), 'type': 'remove', 'name': name, 'carry_fw': False, 'number_of_days': diff, 'notes': 'Carry Forward leave'}
                                io = holiday_obj.with_context(ctx).create(vals1)
                                hlist.append(io)
                                io.signal_workflow('confirm')
                                io.signal_workflow('validate')
                                io.signal_workflow('second_validate')

                                emp = self.env['hr.employee'].browse(t)
                                carry = emp.carryfw_leave + number_of_days_carry
                                emp.with_context(ctx).write({'carryfw_leave': carry})
                        else:
                            pass
                            # situaction where you are directly using the leave request without any allocation request.. like sick leave ..i can put sick leave even if i do not have allocation for that
                            # in this case lets skip that carry forward part...
        if leave_ids:
            # closd the previous allocation request !!!
            leave_ids.with_context(ctx).write(
                {'carry_fw_allocation': True, 'leave_request_done': True})
        if allocation_ids:
            # closd the previous allocation request !!!
            allocation_ids.with_context(ctx).write(
                {'carry_fw_allocation': True, 'leave_request_done': True})
        if emp_ids:
            emp_ids.with_context(ctx).write({})
        result = self.env.ref('hr_holidays.open_allocation_holidays')
        result = result.read()[0]
        if hlist:
            result['domain'] = "[('id','in', [" + ','.join(map(str, hlist)) + "])]"
        return result


class hr_holidays_extend(models.Model):
    _inherit = 'hr.leave'

    exclude_holidays_weekend = fields.Boolean(
        string='Exclude Holidays and Weekends', help='If Checked, Public Holidays and Weekends will be Excluded', default=True)

    
    def holidays_validate(self):
        res = super(hr_holidays_extend, self).holidays_validate()
        # Send an Email
#         ans = self.send_mail('ng_hr_holidays', 'email_templ_approved')
        template = self.env.ref('ng_hr_holidays.email_templ_approved')
        template.send_mail(self.id, force_send=True)

        return res
    # ref: from aun hr holiday script

    @api.model
    def _get_number_of_days(self, date_from, date_to, employee_id):
        if employee_id:
            # DATE_FORMAT = "%Y-%m-%d"
            # date_strong_string = date_from.strftime("%Y-%m-%d")
            # date_to_string = date_to.strftime("%Y-%m-%d")
            #
            # date_from = date_strong_string[:10]
            # date_to = date_to_string[:10]
            # from_dt = datetime.datetime.strptime(date_from, DATE_FORMAT)
            # to_dt = datetime.datetime.strptime(date_to, DATE_FORMAT)
            # date_from = from_dt.strftime(DATE_FORMAT)
            # date_to = to_dt.strftime(DATE_FORMAT)
            # date_f = date_from.split()
            # df = date_f[0].split('-')
            #
            # year_df = int(df[0])
            # month_df = int(df[1])
            # day_df = int(df[2])
            #
            # date_t = date_to.split()
            # dt = date_t[0].split('-')
            #
            # year_dt = int(dt[0])
            # month_dt = int(dt[1])
            # day_dt = int(dt[2])
            #
            # start = datetime.date(year_df, month_df, day_df)
            # end = datetime.date(year_dt, month_dt, day_dt)
            #
            # daydiff = end.weekday() - start.weekday()
            #
            # self._cr.execute(
            #     "SELECT count(*) FROM public_holiday WHERE date >= %s AND date <= %s", (start, end))
            # res = self._cr.fetchone()[0] or 0

            #days = ((end - start).days - daydiff + 1) / 7 * 5 + min(daydiff, 5) - res

            time_delta = date_to - date_from

            self._cr.execute(
                "SELECT count(*) FROM public_holiday WHERE date >= %s AND date <= %s", (date_from, date_to))
            res = self._cr.fetchone()[0] or 0

            days = math.ceil(time_delta.days + float(time_delta.seconds) / 86400) - res

            return days

    @api.onchange('date_from')
    def onchange_date_from(self):
        """
        If there are no date set for date_to, automatically set one 8 hours later than
        the date_from.
        Also update the number_of_days.
        """
        # date_to has to be greater than date_from
        if (self.date_from and self.date_to) and (self.date_from > self.date_to):
            raise Warning(_('Warning! The start date must be anterior to the end date.'))

        result = {'value': {}}

        # No date_to set so far: automatically compute one 8 hours later
        if self.date_from and not self.date_to:
            date_to_with_delta = datetime.datetime.strptime(
                self.date_from, tools.DEFAULT_SERVER_DATETIME_FORMAT) + datetime.timedelta(hours=8)
            result['value']['date_to'] = str(date_to_with_delta)

        # Compute and update the number of days
        if (self.date_to and self.date_from) and (self.date_from <= self.date_to):
            if not self.exclude_holidays_weekend:
                diff_day = timedelta.days + float(timedelta.seconds) / 86400
                result['value']['number_of_days'] = diff_day
            else:
                diff_day = self._get_number_of_days(self.date_from, self.date_to, self.employee_id)
                result['value']['number_of_days'] = round(math.floor(diff_day))
        else:
            result['value']['number_of_days'] = 0

        return result

    @api.onchange('date_to')
    def onchange_date_to(self):
        """
        Update the number_of_days.
        """
        date_from = self.date_from
        date_to = self.date_to
        is_exclude_holiday_weekend = self.exclude_holidays_weekend
        employee_id = self.employee_id

        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise Warning(_('Warning! The start date must be anterior to the end date.'))

        result = {'value': {}}

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            if not is_exclude_holiday_weekend:
                DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
                from_dt = datetime.datetime.strptime(date_from, DATETIME_FORMAT)
                to_dt = datetime.datetime.strptime(date_to, DATETIME_FORMAT)
                timedelta = to_dt - from_dt
                diff_day = timedelta.days + float(timedelta.seconds) / 86400
                result['value']['number_of_days'] = diff_day
            else:
                diff_day = self._get_number_of_days(date_from, date_to, employee_id)
                result['value']['number_of_days'] = round(math.floor(diff_day))
        else:
            result['value']['number_of_days'] = 0

        return result


class public_holiday(models.Model):
    _name = 'public.holiday'

    name = fields.Char(string='Name', required=1)
    date = fields.Date(string='Date', required=1)
    description = fields.Text(string='Description')
