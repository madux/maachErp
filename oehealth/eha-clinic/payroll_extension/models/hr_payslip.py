#
# Extensions to Odoo 12 payroll module

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo import api, fields, models, tools, _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    _description = 'Pay Slip Extension'

    worked_days_in_month = fields.Integer(string="Days worked", help="Number of days worked in month", default="21")

    @api.constrains('worked_days_in_month')
    def _check_worked_days(self):
        '''
        checks if the worked_days_in_month variable is a digit between 1 and 31
        '''
        for record in self:
            worked_days = record.worked_days_in_month

            if worked_days < 1 or worked_days > 31:
                raise ValidationError('Number of days worked must be a number between 1 and 31')

    
    def refund_sheet(self):
        copy_list = []
        for payslip in self:
            copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name})
            '''Copy returns a list and provides no attribute for the recordset'''
            for pay_slip_id in copied_payslip:
                pay_slip_id.compute_sheet()
                pay_slip_id.action_payslip_done()
                copy_list.append(pay_slip_id.id)
        formview_ref = self.env.ref('hr_payroll.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('hr_payroll.view_hr_payslip_tree', False)
        return {
            'name': ("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copy_list,
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'), (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }
    



