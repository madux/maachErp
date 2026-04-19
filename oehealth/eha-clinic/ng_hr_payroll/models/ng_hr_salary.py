# -*- coding: utf-8 -*-


import time

from odoo import fields, models, api, _
import odoo.addons.decimal_precision as dp
import re
from odoo.exceptions import Warning

DATETIME_FORMAT = "%Y-%m-%d"


class pfa(models.Model):
    _name = 'pfa'

    name = fields.Char(string='Name of PFA', required=False)
    contact_address = fields.Text(string='Contact Address')
    #        'partner_id': fields.many2one('res.partner', string='Contact Information'),
    email = fields.Char(string='Email')
    name_person = fields.Char(string='Name of Contact Person')
    notes = fields.Text(string='Notes')
    phone = fields.Char(string='Phone')
    code = fields.Char(string='PFA ID')

    @api.constrains('email')
    def _check_email(self):
        email_re = re.compile(r"""
        ([a-zA-Z][\w\.-]*[a-zA-Z0-9]     # username part
        @                                # mandatory @ sign
        [a-zA-Z0-9][\w\.-]*              # domain must start with a letter
         \.
         [a-z]{2,3}                      # TLD
        )
        """, re.VERBOSE)
        if self.email:
            if not email_re.match(self.email):
                raise Warning(_('Please enter valid email address'))
        return True


class hmo(models.Model):
    _name = 'hmo'

    name = fields.Char(string='Name of Hospital', required=False)
    code = fields.Char(string='HMO ID')
    contact_address = fields.Text(string='Contact Address')
    #        'partner_id': fields.many2one('res.partner', string='Contact Information'),
    email = fields.Char(string='Email')
    name_person = fields.Char(string='Name of Contact Person')
    notes = fields.Text(string='Notes')
    phone = fields.Char(string='Phone')

    @api.constrains('email')
    def _check_email(self):
        email_re = re.compile(r"""
        ([a-zA-Z][\w\.-]*[a-zA-Z0-9]     # username part
        @                                # mandatory @ sign
        [a-zA-Z0-9][\w\.-]*              # domain must start with a letter
         \.
         [a-z]{2,3}                      # TLD
        )
        """, re.VERBOSE)

        if self.email:
            if not email_re.match(self.email):
                raise Warning(_('Please enter valid email address'))
        return True


class hr_employee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    join_date = fields.Date(string='Join Date')
    left_date = fields.Date(string='Left Date')
    reason = fields.Text(string='Reason For Leaving')
    pfa_id = fields.Many2one('pfa', string='Pension Funds Administrator')
    hmo_id = fields.Many2one('hmo', string='Health Management Organization')
    #        'ref_ids': fields.one2many('refs', 'emp_id', string='References'),
    #        'gua_ids': fields.one2many('guarantor', 'emp_id', string='Guarantors'),
    #        'kin_ids': fields.one2many('nextofkin', 'emp_id', string='Next of Kin'),
    pfa_id_ref = fields.Char(string='PFA ID')
    hmo_id_ref = fields.Char(string='HMO ID')

    _sql_constraints = [
        ('pfa_id_ref_unique', 'unique(pfa_id_ref)', _('The PFA ID must be unique!')),
        ('hmo_id_ref_unique', 'unique(hmo_id_ref)', _('The HMO ID must be unique!'))
    ]


class contract_history(models.Model):
    '''
    Employee Contract history
    '''
    _name = 'contract.history'
    _description = 'Contract History'

    name = fields.Char(string='Name', required=False)
    revision_date = fields.Datetime(string='Date')
    contract_id = fields.Many2one('hr.contract', string='Contract')
    increment_id = fields.Many2one('salary.increment', string='Increment')
    #     apprisal_id = fields.Many2one('hr_evaluation.evaluation', string='Apprisal')#todoprobuse
    wage = fields.Float(string='Wage', digits=(16, 2), help='Basic Salary of the employee')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure')


class contract(models.Model):
    '''
    Employee Contract
    '''
    _inherit = 'hr.contract'
    _description = 'Contract'

    history_ids = fields.One2many('contract.history', 'contract_id', 'History')
    schedule_pay = fields.Selection(selection=[
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
        ('daily', 'Daily'),
        ('hourly', 'Hourly'),
    ], string='Scheduled Pay', index=True)


class salary_increment(models.Model):
    _name = 'salary.increment'
    _description = 'Salary increment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _employee_get(self):
        ids = self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1)
        if ids:
            return ids

    @api.model
    def get_contract(self, employee, date_from, date_to):
        '''
        @param employee: browse record of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        '''
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

    def onchange_employee_id(self, date_from, date_to, employee_id=False):
        empolyee_obj = self.env['hr.employee']
        contract_obj = self.env['hr.contract']

        # defaults
        res = {'value': {
            'contract_id': False,
        }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        employee_id = empolyee_obj.browse(employee_id)
        if employee_id.category_ids:
            res['value'].update({'category_id': employee_id.category_ids[0].id})
        else:
            res['value'].update({'category_id': False})

        res['value'].update({
            'company_id': employee_id.company_id.id,
            'manager_id': employee_id.parent_id.id,
        })

        contract_ids = self.get_contract(employee_id, date_from, date_to)
        contract_id = contract_ids and contract_ids[0] or False
        wage = 0.0
        if contract_id:
            #            contract = contract_obj.browse(contract_id)
            wage = contract_id.wage
        res['value'].update({
            'contract_id': contract_ids and contract_ids.id or False,
            'old_salary': wage or 0.0
        })
        return res

    name = fields.Char(string='Name', required=False, readonly=False, states={'validate': [('readonly', True)]})
    state = fields.Selection(selection=[
        ('draft', 'New'),
        ('confirm', 'Waiting Approval'),
        ('refuse', 'Refused'),
        ('validate', 'Approved'),
        ('cancel', 'Cancelled')],
        string='State', readonly=True, help='The state is set to \'Draft\', when a increment request is created.\
                    \nThe state is \'Waiting Approval\', when increment request is confirmed by Manager.\
                    \nThe state is \'Refused\', when increment request is refused by manager.\
                    \nThe state is \'Approved\', when increment request is approved by manager.', default='draft')
    user_id = fields.Many2one(related='employee_id.user_id', comodel='res.users', string='User', store=True,
                              default=lambda self: self.env.user)
    date_from = fields.Datetime(string='Create Date', states={'validate': [('readonly', True)]},
                                default=time.strftime('%Y-%m-01'))
    date_to = fields.Datetime(string='Approved Date', readonly=True)
    last_date = fields.Datetime(string='Last Increment Date', readonly=False, states={'validate': [('readonly', True)]})
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True, required=False, readonly=False,
                                  states={'validate': [('readonly', True)]},
                                  help='Leave Manager can let this field empty if this leave request/allocation is for every employee',
                                  default=_employee_get)
    manager_id = fields.Many2one('hr.employee', string='Manager', readonly=False,
                                 states={'validate': [('readonly', True)]},
                                 help='This area is automatically filled by the user who will approve the request')
    notes = fields.Text(string='Notes', readonly=False, states={'validate': [('readonly', True)]})
    #    case_id = fields.Many2one('crm.meeting', string='Meeting', help='Related Meeting for Increment', readonly=False, states={'validate':[('readonly', True)]})
    case_id = fields.Char('Meeting')
    department_id = fields.Many2one(related='employee_id.department_id', string='Department', comodel='hr.department',
                                    readonly=True, store=True)
    category_id = fields.Many2one('hr.employee.category', string='Category', help='Category of Employee',
                                  readonly=False, states={'validate': [('readonly', True)]})
    contract_id = fields.Many2one('hr.contract', 'Contract', states={'validate': [('readonly', True)]}, index=True)
    old_salary = fields.Float(string='Current Wage', states={'validate': [('readonly', True)]},
                              help='Basic Pay of employee')
    expected_salary = fields.Float(string='Expected Wage', readonly=False, states={'validate': [('readonly', True)]},
                                   help='Expected Basic Pay of employee')
    new_salary = fields.Float(string='New Salary', help='New Basic Pay/Salary Approved by Management', readonly=False,
                              states={'validate': [('readonly', True)]})
    company_id = fields.Many2one('res.company', string='Company', required=False, readonly=False,
                                 states={'validate': [('readonly', True)]},
                                 default=lambda self: self.env['res.company']._company_default_get('salary.increment'))

    def set_to_draft(self):
        self.write({
            'state': 'draft',
            'date_to': False,
            'new_salary': 0.0
        })
        history_ids = self.env['contract.history'].search([('increment_id', '=', self.id)])
        history_ids.unlink()
        self.contract_id.write({'wage': self.old_salary})
        self.delete_workflow()
        self.create_workflow()
        return True

    def salary_refuse(self):
        obj_emp = self.env['hr.employee']
        ids2 = obj_emp.search([('user_id', '=', self._uid)])
        manager = ids2 and ids2[0] or False
        return self.write({'state': 'refuse', 'manager_id': manager})

    def salary_validate(self):
        for sal in self:
            if not sal.new_salary:
                raise Warning(_('Can not approve salary if New Salary set to Zero'))
            obj_emp = self.env['hr.employee']
            ids2 = obj_emp.search([('user_id', '=', self._uid)], limit=1)
            manager = ids2 or False
            vals = {'wage': sal.old_salary, 'employee_id': sal.employee_id.id,
                    'revision_date': time.strftime('%Y-%m-%d'), 'increment_id': sal.id, 'name': 'Increment',
                    'contract_id': sal.contract_id.id, 'struct_id': sal.contract_id.struct_id.id}
            self.env['contract.history'].create(vals)
            sal.contract_id.write({'wage': sal.new_salary})
        return self.write({'state': 'validate', 'manager_id': manager.id, 'date_to': time.strftime('%Y-%m-%d')})

    def salary_confirm(self):
        for sal in self:
            if not sal.contract_id:
                raise Warning(_('No Contract Defined on Salary Increment'))
        return self.write({'state': 'confirm'})
