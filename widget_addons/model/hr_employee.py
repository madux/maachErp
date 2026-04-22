from odoo import models, fields, api, _
import random
import logging
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class HrEmployeeQuery(models.Model):
    _name = "hr.employee.query"
    
    name = fields.Char(string="Description", copy=False)
    employee_id = fields.Many2one('hr.employee', string="Employee", copy=False)
    approved_by = fields.Many2one('res.users', string="Approved by", copy=False)
    query_date = fields.Date(string="Issue Date", copy=False, default=fields.Date.today())
    query_approved_date = fields.Date(string="Approved Date", copy=False)
    resolution = fields.Text(string="Resolution", copy=False)
    reverse_reason = fields.Text(string="Reason for reverse", copy=False)
    state = fields.Char(string="Status", copy=False, default="draft")
    
    def button_approve(self):
        self.state = 'approve'
        self.query_approved_date = fields.Date.today()
        self.approved_by = self.env.uid
        
    def button_reverse(self):
        self.state = 'draft' 
    
class HrEmployeeWarning(models.Model):
    _name = "hr.employee.warning"
    
    name = fields.Char(string="Description", copy=False)
    employee_id = fields.Many2one('hr.employee', string="Employee", copy=False)
    approved_by = fields.Many2one('res.users', string="Approved by", copy=False)
    warning_date = fields.Date(string="Issue Date", copy=False, default=fields.Date.today())
    warning_approved_date = fields.Date(string="Approved Date", copy=False)
    resolution = fields.Text(string="Resolution", copy=False)
    state = fields.Char(string="Status", copy=False, default="draft")
    
    def button_approve(self):
        self.state = 'approve'
        self.query_approved_date = fields.Date.today()
        self.approved_by = self.env.uid
        
        
    def button_reverse(self):
        self.state = 'draft' 

# class HREmployeePublic(models.Model):
#     _inherit = "hr.employee.public"

#     query_number = fields.Integer(string="Query", copy=False, compute="compute_number_queries") 
#     warning_number = fields.Integer(string="Warning", copy=False, compute="compute_number_warning")   

# class HrEmployeeBase(models.AbstractModel):
#     _inherit = "hr.employee.base"
    
#     query_number = fields.Integer(string="Query", copy=False)
#     warning_number = fields.Integer(string="Warning", copy=False, compute="compute_number_warning") 
#     employee_query_history = fields.One2many( 
#         'hr.employee.query', 
#         'employee_id', 
#         string='Query History'
#         )
#     employee_warning_history = fields.One2many( 
#         'hr.employee.warning', 
#         'employee_id', 
#         string='Warning History'
#         )


class HREmployee(models.Model):
    _inherit = "hr.employee"

    query_number = fields.Integer(string="Query", copy=False, compute="compute_number_queries") 
    warning_number = fields.Integer(string="Warning", copy=False, compute="compute_number_warning") 
    employee_query_history = fields.One2many( 
        'hr.employee.query', 
        'employee_id', 
        string='Query History'
        )
    employee_warning_history = fields.One2many( 
        'hr.employee.warning', 
        'employee_id', 
        string='Warning History'
        )
    
    @api.depends("employee_query_history")
    def compute_number_queries(self):
        for rec in self:
            if rec.employee_query_history:
                len_query = len([r.id for r in self.mapped('employee_query_history').filtered(lambda s: s.state == 'approve')])
                rec.query_number = len_query
            else:
                rec.query_number = 0
                
    @api.depends("employee_warning_history")
    def compute_number_warning(self):
        for rec in self:
            if rec.employee_warning_history:
                len_query = len([r.id for r in self.mapped('employee_warning_history').filtered(lambda s: s.state == 'approve')])
                rec.warning_number = len_query
            else:
                rec.warning_number = 0
                
    def register_employee_query(self):
        if self.env.uid != self.department_id.manager_id.user_id.id:
            raise ValidationError("You are not permitted to issue out query - Only manager of this employee can be able to raise this")
        return {
              'name': 'Employee Queries',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'hr.employee.query',
              'type': 'ir.actions.act_window',
              'target': 'new', 
        }
        
    def register_employee_warning(self):
        if self.env.uid != self.department_id.manager_id.user_id.id:
            raise ValidationError("You are not permitted to issue out query - Only manager of this employee can be able to raise this")
        return {
              'name': 'Employee Warning',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'hr.employee.warning',
              'type': 'ir.actions.act_window',
              'target': 'new', 
        }
    
    # def stats_transfer_employee_lines(self):
    #     return {
    #         'name': _('Employee Transfer'),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'hr.employee.transfer.line',
    #         'views': [[self.env.ref('eedc_addons.hr_employee_transfer_line_view_tree').id, 'tree']],
    #         'domain': [('employee_id', 'in', self.ids)],
    #     }
    
    # def stats_transfer_employee_lines(self):
    #     return {
    #           'name': 'Employee Transfer', 
    #         # 'views': [[self.env.ref('hr_holidays.hr_leave_employee_view_dashboard').id, 'tree']],
    #         #   "view_id": self.env.ref('eedc_addons.view_hr_employee_transfer_form'),
    #           'res_model': 'hr.employee.transfer',
    #           'type': 'ir.actions.act_window',
    #         #   'target': 'current',
    #           'domain': [], #[('employee_id', 'in', self.ids)],
    #           }, 
    
    
    
     

    
