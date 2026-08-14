from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta 
from odoo import http

class Send_PMS_back(models.TransientModel):
    _name = "pms.back"

    resp = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user.id)
    record_id = fields.Many2one('pms.appraisee','Record ID',)
    reason = fields.Text('Reason') 
    date = fields.Datetime('Date', default=fields.Datetime.now())
    direct_employee_id = fields.Many2one('hr.employee', 'Forward Back To')
     
    def post(self):
        record_id = self.env['pms.appraisee'].search([('id','=', self.record_id.id)])
        reasons = "<b><h4>Message From: %s </b><br/> Please refer to the reason on the refusal comment section:</h4><br/>* %s." %(self.env.user.name,self.reason)
        if self.reason and record_id:
            record_id._get_appraisal_return_state()
            msg_body = "Dear Sir/Madam, </br> We wish to notify you that {} appraisal with reference <br/>{} has been returned with reason(s) below; \
             <br/>{} <br/><br/>HR Administrator<br/>\
             Should you require any additional information, please contact ICT support for help.<br/>\
             <a href='notifications@layer3.com.ng'>Click ICT Support link</a>".format(self.direct_employee_id.name, self.record_id.name, self.reason)
            record_id.sudo().write({'reason_back': "By {}: {}".format(self.env.user.name, self.reason)})
            self.mail_sending_reject(msg_body)
        else:
            raise ValidationError('Please Add the Reasons for refusal') 
        return{'type': 'ir.actions.act_window_close'}

    def mail_sending_reject(self, msg_body):
        subject = "Rejection Notification"
        user = self.env.user
        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        email_from = user.email or employee.work_email
        mail_to = self.direct_employee_id.work_email or self.direct_employee_id.private_email
        initiator = self.record_id.employee_id.parent_id.work_email
        # emails = (','.join(str(item2.work_email) for item2 in self.users_followers))
        mail_data = {
                'email_from': f'"LAYER3" <notifications@layer3.com.ng>',
                'subject': subject,
                'email_to': mail_to,
                'reply_to': email_from,
                'email_cc': initiator,  # emails if self.users_followers else [],
                'body_html': msg_body
            }
        if mail_to:
            mail_id = self.env['mail.mail'].sudo().create(mail_data)
            # self.env['mail.mail'].sudo().send(mail_id)
            # mail_id.action_send_and_close()
        