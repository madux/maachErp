# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields, api


class employee_notice(models.Model):
    _name = 'employee.notice'
    _description = 'Notice Details'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def onchange_employee_id(self, employee_id=False):
        res = {}
        hr_obj = self.env['hr.employee']
        if not employee_id:
            return {'value': res}
        employee = hr_obj.browse(employee_id)
        if employee.category_ids:
            res.update({'category_id': employee.category_ids[0].id})
        else:
            res.update({'category_id': False})
        return {'value': res}

    def onchange_date(self, res_date=False, exit_date=False):
        res = {}
        res.update({'days': 0})
        if not res_date and not exit_date:
            return {'value': res}
        days = self._get_number_of_days(res_date, exit_date)
        res.update({'days': days})
        return {'value': res}

    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: browse record of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        contract_obj = self.env['hr.contract']
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = [('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), '|', '|'] + clause_1 + clause_2 + clause_3
        contract_ids = contract_obj.search(clause_final)
        return contract_ids

    def onchange_cat_id(self, cat_id=False, emp_id=False, days=False, reason=False, r_date=False):
        res = {}
        hr_obj = self.env['hr.employee']
        not_obj = self.env['notice.period']
        res.update({'emp_pay': 0, 'company_pay': 0})
        if not cat_id and not emp_id and not reason and not days:
            return {'value': res}

        not_ids = not_obj.search([('category_id', '=', cat_id)], limit=1)
        if not not_ids:
            return {'value': res}

        notes = not_ids
        wage = 0.0
        employee = hr_obj.browse(emp_id)

        contract_ids = self.get_contract(employee, r_date, r_date)
        contract_id = contract_ids and contract_ids[0] or False
        if contract_id:
            #            contract = self.env['hr.contract'].browse(contract_id)
            wage = contract_id.wage

        if days >= notes.days:
            return {'value': res}
        elif days < notes.days:
            if reason == 'employee':
                if notes.emp_base == 'fixed':
                    res.update({'emp_pay': notes.emp_value, 'company_pay': 0})
                elif notes.emp_base == 'basic':
                    res.update({'emp_pay': wage, 'company_pay': 0})
                else:
                    domain = [('employee_id', '=', emp_id), ('contract_id', '=', contract_id), ('code', '=', 'GROSS')]
                    line_ids = self.env['hr.payslip.line'].search(domain, limit=1)
                    if line_ids:
                        line = line_ids
                        res.update({'emp_pay': line.amount, 'company_pay': 0})
        else:
            if notes.company_base == 'fixed':
                res.update({'company_pay': notes.company_value, 'emp_pay': 0})
            elif notes.emp_base == 'basic':
                res.update({'emp_pay': 0, 'company_pay': wage})
            else:
                domain = [('employee_id', '=', emp_id), ('contract_id', '=', contract_id), ('code', '=', 'GROSS')]
                line_ids = self.env['hr.payslip.line'].search(domain, limit=1)
                if line_ids:
                    line = line_ids
                    res.update({'emp_pay': line.amount, 'company_pay': 0})
            return {'value': res}

    def onchange_days(self, days=False, employee_id=False, category_id=False, reason=False):
        res = {}
        hr_obj = self.env['hr.employee.category']
        if not reason:
            res.update({'emp_pay': 0, 'company_pay': 0})
            return {'value': res}
        if not employee_id and not category_id:
            res.update({'emp_pay': 0, 'company_pay': 0})
            return {'value': res}
        if category_id:
            cat = hr_obj.browse(category_id)
            if days >= cat.notice_period:
                res.update({'emp_pay': 0, 'company_pay': 0})
                return {'value': res}
            elif days < cat.notice_period:
                if reason == 'employee':
                    res.update({'emp_pay': cat.emp_pay, 'company_pay': 0})
                else:
                    res.update({'company_pay': cat.company_pay, 'emp_pay': 0})
        if not category_id and employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            if employee.category_ids:
                cat = employee.category_ids[0]
                if days >= cat.notice_period:
                    res.update({'emp_pay': 0, 'company_pay': 0})
                    return {'value': res}
                elif days < cat.notice_period:
                    if reason == 'employee':
                        res.update({'emp_pay': cat.emp_pay, 'company_pay': 0})
                    else:
                        res.update({'company_pay': cat.company_pay, 'emp_pay': 0})
        return {'value': res}

    @api.model
    def _get_number_of_days(self, date_from, date_to):
        """Returns a float equals to the timedelta between two dates given as string."""

        DATETIME_FORMAT = "%Y-%m-%d"
        from_dt = datetime.strptime(date_from, DATETIME_FORMAT)
        to_dt = datetime.strptime(date_to, DATETIME_FORMAT)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days + float(timedelta.seconds) / 86400
        return diff_day

    @api.model
    def _employee_get(self):
        ids = self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1)
        if ids:
            return ids

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Description', required=False, readonly=False, states={'validate': [('readonly', True)]})
    user_id = fields.Many2one('res.users', string='Responsible User', readonly=False,
                              states={'validate': [('readonly', True)]})
    employee_id = fields.Many2one('hr.employee', string='Employee', required=False, readonly=False, states={
        'validate': [('readonly', True)]}, default=_employee_get)
    category_id = fields.Many2one('hr.employee.category', string='Category', required=False,
                                  readonly=False, states={'validate': [('readonly', True)]})
    resigning_date = fields.Date(string='Resign Date', required=False, readonly=False,
                                 states={'validate': [('readonly', True)]})
    exit_date = fields.Date(string='Exit Date', required=False, readonly=False,
                            states={'validate': [('readonly', True)]})
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', required=False, readonly=False, states={
        'validate': [('readonly', True)]}, default=lambda self: self.env.user.company_id)
    days = fields.Float(string='Days', required=False, help='Give the number of days employee has given notice',
                        readonly=False, states={'validate': [('readonly', True)]})
    company_pay = fields.Float(string='Company Payment',
                               help='Give the amount company has to pay to its employee based on policy',
                               readonly=False, states={'validate': [('readonly', True)]})
    emp_pay = fields.Float(string='Employee Payment',
                           help='Give the amount employee has to pay to his/her company based on policy',
                           readonly=False, states={'validate': [('readonly', True)]})
    state = fields.Selection(selection=[('draft', 'New'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'),
                                        ('validate', 'Approved'), ('cancel', 'Cancelled')],
                             default='draft',
                             string='State', readonly=True, help='The state is set to \'Draft\', when a termination request is created.\
                              \nThe state is \'Waiting Approval\', when termination request is confirmed by Manager.\
                              \nThe state is \'Refused\', when termination request is refused by manager.\
                              \nThe state is \'Approved\', when termination request is approved by manager.')
    reason = fields.Selection(selection=[
        ('employee', 'Employee'),
        ('company', 'Employer')], string='Reason', required=False, readonly=False,
        states={'validate': [('readonly', True)]}, default='employee')

    def set_to_draft(self):
        self.write({'state': 'draft'})
        return True

    def nt_refuse(self):
        self.write({'state': 'refuse'})
        return True

    def nt_validate(self):
        return self.write({'state': 'validate', 'user_id': self._uid})

    def nt_confirm(self):
        return self.write({'state': 'confirm'})


class union_policy(models.Model):
    _name = 'union.policy'
    _description = 'union Policy Details'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=False)
    code = fields.Char(string='Code', required=False)
    employee_categ_ids = fields.Many2many(
        'hr.employee.category', 'employee_category_policy_rel_union', 'union_id', 'category_id',
        string='Employee Categories')
    employee_ids = fields.Many2many('hr.employee', 'union_employee_rel', 'union_id', 'employee_id', string="Employee's")
    company_id = fields.Many2one('res.company', string='Company', required=False,
                                 default=lambda self: self.env.user.company_id)
    base = fields.Selection(selection=[
        ('basic', 'Based On Basic'),
        ('fixed', 'Fix Amount'),
        ('', '')], string='Basis', required=False, index=True, help='Based On.', default='basic')
    value = fields.Float(
        string='Value',
        help='For Basic enter ratio between 0 and 1. If Basis is Fixed Amount, then set value as a fixed amount.')


class union(models.Model):
    _name = "emp.union"
    _description = "Union"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=False)
    code = fields.Char(string='Code')
    company_id = fields.Many2one('res.company', string='Company', required=False,
                                 default=lambda self: self.env.user.company_id)
    union_policy_ids = fields.Many2many('union.policy', 'union_policy_rel',
                                        'policy_id', 'loan_id', string='Active Policies')


class hr_employee_category(models.Model):
    _inherit = 'hr.employee.category'
    _description = 'Employee Category'

    union_policy = fields.Many2many('union.policy', 'employee_category_policy_rel_union',
                                    'category_id', 'union_id', string='Union Policies')
    notice_period = fields.Float(string='Notice Period Allowed', help='Please enter notice period in days')
    company_pay = fields.Float(string='Company Payment',
                               help='Give the amount company has to pay to its employee based on policy')
    emp_pay = fields.Float(string='Employee Payment',
                           help='Give the amount employee has to pay to his/her company based on policy')


class hr_employee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    union_policy = fields.Many2many('union.policy', 'union_employee_rel',
                                    'employee_id', 'union_id', string='Union Policies')
    union_ids = fields.Many2many('emp.union', 'union_employee_master_rel1', 'employee_id', 'u_id', string='Unions')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
