# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models
from odoo.tools.translate import _
from odoo.exceptions import UserError, AccessError


class HrPayrollBatchPayslipEmailing(models.TransientModel):
    _name = "batch.payslip.emailing"
    _description = "Transient Model for Emailing payslip "

    
    def batch_payslip_emailing(self):

        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        PayslipObj = self.env['hr.payslip']
        ids = self.env.context.get('active_ids', [])
        ctx = dict()
        employee_name = ''
        for id in ids:
            payslip = PayslipObj.browse([id])
            # join all employees without email to report to HR manager later 
            if not payslip.employee_id.work_email:
                employee_name += payslip.employee_id.name + ' ,'
            if payslip.state == 'done':
                if payslip.employee_id.work_email:
                    try:
                        template_id = ir_model_data.get_object_reference('payroll_extension', 'email_tpl_payslip')[1]
                    except ValueError:
                        template_id = False

                    ctx.update({
                        'default_model': 'hr.payslip',
                        'default_res_id': payslip.id,
                        'default_use_template': bool(template_id),
                        'default_template_id': template_id,
                        'default_composition_mode': 'comment',
                        'email_to': payslip.employee_id.work_email,
                    })
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(payslip.id, True)
            else:
                raise UserError(_(str(employee_name) + 'Payslip is not yet confirmed. Kindly confirm the payslip and try again.'))
        if employee_name:
            raise UserError(_('Payslip was not sent to ' + str(employee_name) + '. Kindly provide employees official email in employee form'))
        return True
