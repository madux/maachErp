from odoo import api,fields, models

class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'
    _description = 'Enhancements to the Employee Module'

    employee_identification_code = fields.Char(string="Employee ID", help="Employee ID")
    pfa_id_ref = fields.Char(string='PFA ID')
    
    # request_id = fields.Many2one('hr.recruitment.request', string="Recruitment Request", index=True)

    
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('hr.employee')
        vals['employee_identification_code'] = sequence
        employee = super(HrEmployeeBase, self).create(vals)
        return employee
