from odoo import api, exceptions, fields, models
from odoo.tools.translate import _
from odoo.exceptions import UserError, AccessError, ValidationError
import base64
from dateutil.relativedelta import relativedelta
from datetime import datetime
import time
import ast

class BatchLabtestEmail(models.Model):
    _name = "batch.labtest.emailing"
    _description = "Model for Emailing Labtest to thirdparty Partners "

    @api.depends('active_list_ids')
    def default_labtest_ids_get(self):
        if self.active_list_ids:
            rec_ids = self.env.context.get('active_ids', [])
            LabTestObj = self.env['oeh.medical.lab.test']
            ids = []
            if self.cif_mail_type not in ["inbound", "referral", "outbound"]:
                """Assumes that recordset not in ["inbound","referral","outbound"] is meant for lab tests"""
                for rec in rec_ids:
                    LabObj = LabTestObj.browse([rec])
                    if LabObj.state in ["Completed", "Reviewed"] and LabObj.test_type.code == 'COVID-19':
                        ids.append(LabObj.id)

                self.active_lab_ids = [(6, 0, ids)]

    def _default_get(self):
        rec_ids = self.env.context.get('active_ids', [])
        ids = []
        for rec in rec_ids:
            ids.append(rec)
        return ids

    partner_ids = fields.Many2many('res.partner', string="Partners")
    mail_type = fields.Selection([
        ('individual', 'Individual'),
        ('organization', 'Organization'),
        ('both', 'Both'),
    ],
        string='Mail Type',
        required=False,
        index=True,
        copy=True,
        default='individual',
    )

    cif_mail_type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound'), ('referral', 'Referral')],
                                     string='Mail Type', index=True,
                                     copy=True,
                                     )

    request_type = fields.Selection([('triage', 'Triage'),
                                     ('appointment', 'Appointment')],
                                    string='Request Type', index=True,
                                    copy=True)
    appointment_booking = fields.Boolean('Is Appointment Booking?', default=False)
    subject = fields.Char(string="Subject", size=40)
    is_individual_mail = fields.Boolean(string="Is Individual mail", default=False)
    is_specific_mail = fields.Boolean(string="Send to alternate email address", default=False)
    specific_mail_address = fields.Char(string="Mail Address", size=40, help="Use this if sending to personal mail address")
    template_id = fields.Many2one('mail.template')
    email_ids = fields.Many2many('mail.mail', string="Emails")
    active_lab_ids = fields.Many2many('oeh.medical.lab.test', string="Active IDs", compute="default_labtest_ids_get",
                                      store=False) 
    active_cif_ids = fields.Many2many('oeha.covid19.cif', string="Active CIF IDs") 
    active_list_ids = fields.Char(string="Active IDS List", default=_default_get)
    notification_type = fields.Selection([('email', 'Email'), ('sms', 'SMS'), ('both', 'Both')],
                                          required=False, default='email')
    sms_template_id = fields.Many2one('sms.template', string="SMS Template")

    @api.onchange('cif_mail_type')
    def domain_template_id(self):
        ''' Domain filter to determine the template to display when a mail type of inbound is selected '''
        if self.cif_mail_type in ["inbound", "outbound"]:
            temp1 = self.env.ref('oehealth_extension.covid19_inbound_email_template')
            temp2 = self.env.ref('oehealth_extension.covid19_inbound_booking_template')
            temp3 = self.env.ref('oehealth_extension.covid19_followup_template')
            temp4 = self.env.ref('oehealth_extension.covid19_inbound_payment_template') or False
            temp5 = self.env.ref('oehealth_extension.covid19_followup_payment_template') or False
            tmps = [temp1.id if temp1 else False, temp2.id if temp2 else False, temp3.id]
            tmps.append(temp4.id)
            tmps.append(temp5.id)

            # SMS templates
            smstemp1 = self.env.ref('oehealth_extension.sms_template_payment_link').id or False
            smstemp2 = self.env.ref('oehealth_extension.sms_template_payment_followup').id or False
            domain = {'template_id': [('id', 'in', tmps)],
                      'sms_template_id': [('id', 'in', [smstemp1, smstemp2])]
                      }
            return {'domain': domain}
        elif self.cif_mail_type == "referral":
            """Would have shortened to a function but possibility of adding
             extra templates have not been determined"""
            temp1 = self.env.ref('oehealth_extension.covid19_referral_email_template')
            temp2 = self.env.ref('oehealth_extension.covid19_referral_booking_template')
            tmps = [temp1.id if temp1 else False, temp2.id if temp2 else False]
            domain = {'template_id': [('id', 'in', tmps)]}
            return {'domain': domain}

    def generate_report_file(self, report_name, id):
        pdf = self.env.ref(report_name).render_qweb_pdf(id)[0]
        pdf = base64.b64encode(pdf)
        return pdf

    @api.onchange('mail_type')
    def onchange_mail_type(self):
        """Removes partner records because if individual mail type is selected"""
        if self.cif_mail_type in ['inbound', 'outbound', 'referral']:
            self.partner_ids = False

    def action_send_cif_batch_mail(self):
        ids = self.env.context.get('active_ids', [])
        CIFOBJ = self.env['oeha.covid19.cif']
        self.check_mail_limit()
        type_status = True if self.request_type == 'appointment' else False
        if self.notification_type in ['email','both']:
            if self.cif_mail_type in ["inbound", "outbound"]:
                for id in ids:
                    cfobj = CIFOBJ.browse([id])
                    email = cfobj.email
                    cfobj.email_generator(self.template_id.id, cfobj.id, self.subject, email, type_status)

            elif self.cif_mail_type == "referral":
                for id in ids:
                    cfobj = CIFOBJ.browse([id])
                    if cfobj.is_payment_required:
                        email = cfobj.email
                        cfobj.email_generator(self.template_id.id, cfobj.id, self.subject, email, type_status)
        if self.notification_type in ['sms','both']:
            if self.cif_mail_type in ["inbound", "outbound"]:
                for id in ids:
                    cfobj = CIFOBJ.browse([id])
                    sms_temp = self.sms_template_id
                    cfobj.sms_generator(sms_temp,sms_temp.body, cfobj._name, cfobj.ids)

    def action_send_batch_labtest_mail(self):
        ids = self.env.context.get('active_ids', [])
        Labtest = self.env['oeh.medical.lab.test']
        self.check_mail_limit()
        filter_lbs = ast.literal_eval(self.active_list_ids) if self.active_list_ids else []
        email_from = self.env.user.company_id.email
        if self.mail_type == "individual":
            if not self.is_individual_mail:
                for id in ids:
                    labtest_id = Labtest.browse([id])
                    if labtest_id.state in ["Completed", "Reviewed"]:
                        patient_email = labtest_id.patient.email or labtest_id.patient.secondary_email
                        # if labtest_id.test_type.code == 'COVID-19':
                        labtest_id.email_generator(patient_email)
            else: 
                active_id = self.env.context.get('active_id')
                labtest_id = Labtest.browse([active_id]) if active_id else False
                if labtest_id:
                    patient_email = labtest_id.patient.email or labtest_id.patient.secondary_email
                    email_to = self.specific_mail_address if self.is_specific_mail else patient_email
                    labtest_id.email_generator(email_to)

        elif self.mail_type == "organization":
            if self.partner_ids:
                for record in self.partner_ids:
                    mail_to = record.email
                    self.attach_send_mail(email_from, mail_to, filter_lbs)

        else:
            for id in ids:
                labtest_id = Labtest.browse([id])
                if labtest_id.state in ["Completed", "Reviewed"]:
                    email_to = labtest_id.patient.email or labtest_id.patient.secondary_email
                    labtest_id.email_generator(email_to)

            for record in self.partner_ids:
                mail_to = record.email
                email_from = self.env.user.company_id.email
                self.attach_send_mail(email_from, mail_to, filter_lbs)

    def check_mail_limit(self):
        """Validation for checking the number of limit a mail can accomodate"""
        param_obj = self.env['ir.config_parameter']
        mail_limit = param_obj.sudo().get_param('mail_limit', False)
        active_lists = self.active_list_ids.strip('][').split(
            ',')  # Converted a string representation of list to a list type
        if (len(active_lists) or len(self.active_lab_ids)) > int(mail_limit):
            raise ValidationError("You can only send {} mail at a time".format(int(mail_limit)))

    def attach_send_mail(self, email_from, mail_to, ids):
        attach_lists = []
        summary_report_binary = self.generate_report_file('oehealth_extension.action_summary_report_patient_labtest',
                                                          self.id)
        summary_attachementObj = self.attachment_render("Summary Lab Test Attachment.pdf", summary_report_binary)
        attach_lists.append(summary_attachementObj)
        self.send_mail(email_from, mail_to, attach_lists)

    def send_mail(self, email_from, mail_to, attach_lists):
        body = self.env.ref('oehealth_extension.sendboth_labtest_email_template')
        body_html = body.body_html
        subject = self.subject if self.subject else "Lab test Result"
        mail_data = {
            'email_from': email_from,
            'subject': subject,
            'email_to': mail_to,
            'reply_to': email_from,
            'attachment_ids': [(6, 0, attach_lists)] or None,
            'body_html': body_html,
        }
        mail_id = self.env['mail.mail'].create(mail_data)
        self.email_ids = [(6, 0, [mail_id.id])]
        # self.env['mail.mail'].send(mail_id)

    def attachment_render(self, attachment_name, report_binary):
        attachmentObj = self.env['ir.attachment'].create({
            'name': attachment_name,
            'type': 'binary',
            'datas': report_binary,
            'store_fname': attachment_name,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/x-pdf'
        })
        return attachmentObj.id

    
