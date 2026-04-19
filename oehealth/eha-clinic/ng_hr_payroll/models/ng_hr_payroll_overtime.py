# -*- coding: utf-8 -*-

import time
from datetime import datetime

from odoo import models, fields, api

Datetime_FORMAT = '%Y-%m-%d'


class hr_overtime(models.Model):
    _name = 'hr.overtime'
    _description = 'Employee Overtime'

    @api.model
    def _employee_get(self):
        ids = self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1)
        if ids:
            return ids

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id.category_ids:
            self.category_id = self.employee_id.category_ids[0].id
        self.company_id = self.employee_id.company_id.id
        self.manager_id = self.employee_id.parent_id.id

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Description', required=False, states={'validate': [('readonly', True)]})
    number_of_hours = fields.Float(string='Number of Hours', states={'validate': [('readonly', True)]})
    number_of_days = fields.Float(string='Number of Days', states={'validate': [('readonly', True)]})
    include_payroll = fields.Boolean(string='Include in Payroll', states={'validate': [(
        'readonly', True)]}, help='Tick if you want to include this overtime in employee payroll', default=True)
    state = fields.Selection(selection=[('draft', 'New'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'),
                                        ('validate', 'Approved'), ('cancel', 'Cancelled')],
                             string='State', readonly=True, help='The state is set to \'Draft\', when a overtime request is created.\
                                \nThe state is \'Waiting Approval\', when overtime request is confirmed by Manager.\
                                \nThe state is \'Refused\', when overtime request is refused by manager.\
                                \nThe state is \'Approved\', when overtime request is approved by manager.',
                             default='draft')
    user_id = fields.Many2one(related='employee_id.user_id', string='User',
                              store=True, default=lambda self: self.env.user)
    date_from = fields.Datetime(string='Start Date', readonly=False, states={
        'validate': [('readonly', True)]}, default=fields.datetime.now())
    date_to = fields.Datetime(string='End Date', readonly=False, states={'validate': [('readonly', True)]})
    approve_date = fields.Datetime(string='Approved Date', readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", index=True, required=False,
                                  default=_employee_get, states={'validate': [('readonly', True)]})
    manager_id = fields.Many2one('hr.employee', 'Manager', readonly=False, states={'validate': [(
        'readonly', True)]}, help='This area is automatically filled by the user who will approve the request')
    notes = fields.Text(string='Notes', )
    department_id = fields.Many2one(related='employee_id.department_id', string='Department',
                                    type='many2one', relation='hr.department', readonly=True, store=True)
    category_id = fields.Many2one('hr.employee.category', string="Category", readonly=False, states={
        'validate': [('readonly', True)]}, help='Category of Employee')
    company_id = fields.Many2one('res.company', string='Company', required=False,
                                 readonly=False, states={'validate': [('readonly', True)]})

    def set_to_draft(self):
        self.write({
            'state': 'draft',
            'approve_date': False
        })
        return True

    @api.model
    def _get_number_of_days(self, date_from, date_to):
        """Returns a Float equals to the timedelta between two dates given as string."""

        Datetime_FORMAT = "%Y-%m-%d %H:%M:%S"
        from_dt = datetime.strptime(date_from, Datetime_FORMAT)
        to_dt = datetime.strptime(date_to, Datetime_FORMAT)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days + float(timedelta.seconds) / 86400
        return diff_day

    def onchange_date_from(self, date_to, date_from):
        result = {}
        if date_to and date_from:
            diff_day = self._get_number_of_days(date_from, date_to)
            result['value'] = {
                'number_of_days': round(diff_day) + 1
            }
            return result
        result['value'] = {
            'number_of_days': 0,
        }
        return result

    def ot_refuse(self):
        obj_emp = self.env['hr.employee']
        ids2 = obj_emp.search([('user_id', '=', self._uid)], limit=1)
        manager = ids2 or False
        self.write({'state': 'refuse', 'manager_id': manager.id})
        return True

    def ot_validate(self):
        obj_emp = self.env['hr.employee']
        ids2 = obj_emp.search([('user_id', '=', self._uid)], limit=1)
        manager = ids2 or False
        return self.write({'state': 'validate', 'manager_id': manager.id, 'approve_date': time.strftime('%Y-%m-%d')})

    def ot_confirm(self):
        return self.write({'state': 'confirm'})


class Employee(models.Model):
    _inherit = 'hr.employee'

    overtime_ids = fields.One2many('hr.overtime', 'employee_id', string='Overtimes')
