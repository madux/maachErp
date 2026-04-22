from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# class ResourceEmployeeLeave(models.AbstractModel):
#     _inherit = "resource.employee.leave.reliever"
#     _description = "Resource Employee leave Reliever"
    
#     administrative_supervisor_id = fields.Many2one('hr.employee', string="Administrative Supervisor")
    
    
    
class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    administrative_supervisor_id = fields.Many2one('hr.employee', string="Administrative Supervisor")
    legacy_id = fields.Integer(string="legacy_id")
    external_id = fields.Char(string="External ID")
    leave_reliever_memo_stage_ids = fields.Char(string="Request stages reliever is assigned")
    maximum_cash_advance_limit = fields.Integer(
        string="Maximum Limit Cash Advance", 
        default=5
        )
    leave_reliever = fields.Many2one(
        'hr.employee', 
        string="Leave Reliever",  
        )
    
    def reset_leave_reliever(self):
        # for rec in self:
        #     rec.action_reset_leave_reliever()
        stage_obj = self.env['memo.stage'].sudo()
        for rec in self:
            if not rec.leave_reliever:
                raise ValidationError("No relieve found to update")
            if rec.leave_reliever_memo_stage_ids:
                slms = eval(rec.leave_reliever_memo_stage_ids)
                for st in slms:
                    st_id = stage_obj.browse([st])
                    st_id.update({
                        'approver_ids': [(3, rec.leave_reliever.id), (4,rec.id)]
                    })
            rec.leave_reliever = False
            rec.leave_reliever_memo_stage_ids = False
            
    # def action_reset_leave_reliever(self, employee_id=False):
    #     stage_obj = self.env['memo.stage'].sudo()
    #     emp = employee_id if employee_id else self 
    #     if emp.leave_reliever_memo_stage_ids:
    #         slms = eval(emp.leave_reliever_memo_stage_ids)
    #         for st in slms:
    #             st_id = stage_obj.browse([st])
    #             st_id.update({
    #                 'approver_ids': [(3, emp.leave_reliever.id), (4, emp.id)]
    #             })
    #     emp.leave_reliever = False
    #     emp.leave_reliever_memo_stage_ids = False
            
    def update_leave_reliever(self):
        if self.leave_reliever:
            self.env['memo.model'].set_reliever_to_act_as_employee_on_leave(
                self.sudo().id,
                self.sudo().leave_reliever.id,
            )
        else:
            raise ValidationError("Please kindly set the reliever to update")
    
     