import io
import xlwt
import datetime
import qrcode
import base64
import uuid
import logging
import random
import requests
from ast import literal_eval
from io import BytesIO
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.eha_auth.controllers.helpers import convert_date_to_iso, convert_time, tolocale_time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil import parser

_logger = logging.getLogger(__name__)


class OeHealthLabTestsExtension(models.Model):
    _name = 'oeh.medical.lab.test'
    _inherit = ['oeh.medical.lab.test', 'mail.thread']
    _order = "id desc"

    LABTEST_STATE = [
        ('Draft', 'Draft'),
        ('Sample Collected', 'Sample Collected'),
        ('Test In Progress', 'Test In Progress'),
        ('Completed', 'Completed'),
        ('Reviewed', 'Reviewed'),
        ('Invoiced', 'Invoiced'),
    ]

    LOCATION = [
        ('Internal', 'Internal'),
        ('External', 'External')
    ]

    LAB_PARTNERS = [
        ('Synlab', 'Synlab'),
        ('Providian', 'Providian'),
        ('Diagnostics', 'Diagnostic'),
        ('Mecure', 'Mecure'),
        ('Other', 'Other')
    ]

    lab_department = fields.Many2one(
        'oeh.medical.labtest.department', string='Department', required=False)
    test_type = fields.Many2one('oeh.medical.labtest.types', string='Test Type', required=False, readonly=True, states={
        'Draft': [('readonly', False)]}, help="Lab test type")
    active = fields.Boolean(string="Active", default=True)
    test_type_code = fields.Char(related='test_type.code')
    sample_type = fields.Many2many('oeha.sample.type', string='Sample Type')
    referring_partner = fields.Many2one('res.partner', string='Referring Partner',
                                        domain=lambda self: self._default_get_referring_partner())
    reason_for_test = fields.Many2one('oeha.lab.reason.model', string='Reason For test')
    qr_image = fields.Binary('QR Code')
    formatted_time = fields.Char(
        string="Formatted creation time", compute='_compute_creation_time')
    identification_code = fields.Char(
        string="Patient ID", related="patient.identification_code")
    cif_ref = fields.Many2one('oeha.covid19.cif', string='CIF Reference', help="Only for Covid 19 patients", copy=False,
                              readonly=False)
    passport_attachment = fields.Many2one('ir.attachment', string="Attachment", compute='_compute_passport', store=True)
    passport_no = fields.Char('Passport Number', compute='_compute_passport', store=True)
    thirdparty_partner_id = fields.Many2many('res.partner', string="Third Party Partner?", required=False)
    mail_log_ids = fields.Many2many('mail.mail', string="Mail Logs")
    number_email_count = fields.Integer(string="Number of Email Sent", default=0)
    # add new fields for linking labtest with evaluation
    evaluation_id = fields.Many2one(
        'oeh.medical.evaluation', string="Evaluation")
    results_short = fields.Char(
        string='Results (Short)', compute='_generate_short_result')
    # override state field in parent oehealth lab model
    state = fields.Selection(
        LABTEST_STATE, string='State', readonly=True, default=lambda *a: 'Draft')
    date_completed = fields.Datetime(string='Date Completed')
    reviewer = fields.Many2one('res.users', string='Reviewer')
    review_date = fields.Datetime(string='Review Date')
    # Lab Test redesign
    care_provider_who_ordered_test = fields.Many2one('res.users', string="Ordering Care Provider",
                                                     domain=lambda self: self._get_ordering_care_provider())
    care_provider_who_performed_test = fields.Many2one('res.users', string="Care Provider Performing the Test",
                                                       domain=lambda self: self._get_performing_care_provider())
    location = fields.Selection(LOCATION, string='Test Location', default=lambda *a: 'Internal')
    lab_partner = fields.Selection(LAB_PARTNERS, string='Lab Partner')
    instruction_to_lab = fields.Text("Instructions to Lab")
    sample_collected_by = fields.Many2one('res.users', string="Sample Collected By")
    # fields for NCDC sample label
    patient_age = fields.Char(string='Patient Age', compute='_compute_patient_age')
    sample_collection_date = fields.Datetime(string='Sample collection date')
    sms_status = fields.Selection([('yes', 'Yes'), ('no', 'No')], default='no',
                                  help="Indicates if sms has been sent or not")
    cif_id = fields.Many2one('oeha.covid19.cif', string="Cif Id", compute='_compute_cif')
    ncdc_sent_status = fields.Boolean(string="NCDC Sent Status", default=False)
    airline = fields.Char(string="Airline", compute="_compute_cif_ref", store=True)
    departure_country = fields.Char(string="Departure Country", compute="_compute_cif_ref", store=True)
    destination = fields.Char(string="Destination", compute="_compute_cif_ref", store=True)
    ncdc_cert_number = fields.Char(string="NCDC Certificate Number", compute="_compute_cert_number")
    ncdc_test_id = fields.Char(string="NCDC Test Id")
    ncdc_retry_count = fields.Integer(string="Number of NCDC retries", default=0)
    covid19_sms_retry_count = fields.Integer(string="Covid-19 SMS retries", default=0)
    panabios_sent_status = fields.Boolean(string="Synced with Panabios", default=False, copy=False)
    property_product_pricelist = fields.Many2one('product.pricelist', string='Pricelist', related='patient.property_product_pricelist')
    
    @api.depends('cif_ref')
    def _compute_cif_ref(self):
        for rec in self:
            if rec.cif_ref:
                rec.departure_country = rec.cif_ref.depature_country
                rec.airline = rec.cif_ref.flight
                rec.destination = rec.cif_ref.destination

            else:
                rec.departure_country = False
                rec.destination = False
                rec.airline = False

    # @api.onchange('location')
    # def _set_external_lab_user(self):
    #     if self.location == 'External' and self.state != 'Draft':
    #         external_user = self.env['res.users'].search([('login','=','external_lab')], limit=1)
    #         self.care_provider_who_performed_test = external_user.id
    #     else:
    #         self.care_provider_who_performed_test = self.env.user.id

    def get_instance_environment(self):
        # determines if the system is not the live environment
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') # e.g https://stage.eha.ng
        return True if 'stage' in base_url else False

    @api.depends('name')
    def _compute_cert_number(self):
        for rec in self:
            code = '399' if rec.get_instance_environment() else '342' # determines if the system is not the live environment
            labtest_no = rec.name
            cert_number = code + '0' + labtest_no[2:]
            rec.ncdc_cert_number = cert_number

    @api.onchange('referring_partner')
    def onchange_referring_partner(self):
        domain = {'reason_for_test': []}
        lis = []
        self.reason_for_test = False
        inbound = self.oehealth_xml_id('oehealth_extension', 'id_res_inbound_tag')
        outbound = self.oehealth_xml_id('oehealth_extension', 'id_res_outbound_tag')
        nontravel = self.oehealth_xml_id('oehealth_extension', 'id_res_nontravel_tag')
        for rec in self.env['oeha.lab.reason.model'].search([]):
            reason_ids = rec.mapped('partner_reference_line').filtered(
                lambda x: x.partner_id.id == self.referring_partner.id)
            if reason_ids:
                lis.append(rec.id)
        domain = {'reason_for_test': [('id', 'in', lis)]}
        return {'domain': domain}

    def _default_get_referring_partner(self):
        partner_ids = self.env['res.partner'].search([('category_id.name', 'in', ['REFERRING PARTNER'])])
        lis = []
        for rec in partner_ids:
            lis.append(rec.id)
        domain = [('id', 'in', lis)]
        return domain

    def oehealth_xml_id(self, module, xml_id):
        return self.env.ref('{}.{}'.format(module, xml_id)).id

    @api.onchange('test_type')
    def onchange_test_type_id(self): # Renamed to the function in oeHealth by Olalekan after Ogochukwu reported that the Department and 
    #  Test type were not updating on the view
        # domain = {'sample_type': []}
        lis = []
        for rec in self:
            if rec.test_type:
                rec.lab_test_criteria.unlink()
                lb_crt = self.env['oeh.medical.labtest.criteria'].search([('medical_type_id', '=', rec.test_type.id)])
                for crt in lb_crt:
                    crt_line = {
                        'name': crt.name,
                        'sequence': crt.sequence,
                        'normal_range': crt.normal_range,
                        'units': crt.units
                    }
                    rec.lab_test_criteria = [(0, 0, crt_line)]
        # The lines below were removed due to the reasons given in lines 169 and 170 above
        # 		smp_obj = self.env['oeha.sample.type'].search([]) 
        # 		for smp in smp_obj:
        # 			r_type = smp.mapped('related_test_type').filtered(lambda s: s.id == rec.test_type.id)
        # 			if r_type:
        # 				lis.append(smp.id)
        # domain = {'sample_type': [('id', 'in', lis)]}
        # return {'domain': domain}

    @api.depends('name')
    def _compute_cif(self):
        covid_19_cif = self.env['oeha.covid19.cif']
        for rec in self:
            cif_obj = covid_19_cif.sudo().search([('labtest_id.name', '=', rec.name)], limit=1)
            if cif_obj:
                rec.cif_id = cif_obj
            else:
                rec.cif_id = False

    def _get_care_provider(self, type_operation, username):
        '''return careprovider for a given operation type 
            Walkin patient has default username walkin_patient
            External lab has default username external_lab
        '''
        crp_obj = self.env['oeha.care.providers']
        # care.providers with code cp-001 is lab ordering care provider
        users = crp_obj.search([('type_of_operation', '=', type_operation)], limit=1).mapped('user_ids')
        default_user = self.env['res.users'].search([('login', '=', username)], limit=1)
        default_user_id = [default_user.id] if default_user else []
        user_ids = [u.id for u in users if users] + default_user_id
        domain = [('id', '=', user_ids)]
        return domain

    def _get_ordering_care_provider(self):
        return self._get_care_provider('labtest_ordering', 'walkin_patient')

    def _get_performing_care_provider(self):
        return self._get_care_provider('labtest_performing', 'external_lab')

    @api.depends('patient')
    def _compute_passport(self):
        for rec in self:
            cif = rec.env['oeha.covid19.cif'].search([('patient_id', '=', rec.patient.id)], order='id desc', limit=1)
            if cif and (rec.patient.passport_no is not None):
                rec.passport_attachment = cif.passport_attachment.id
                rec.passport_no = rec.patient.passport_no

            else:
                rec.passport_attachment = False
                rec.passport_no = False

    @api.onchange('test_type', 'patient')
    def domain_evaluation_id(self):
        ''' Dynamically filter only COVID-19 Evals when test_type is related to COVID-19 '''
        if self.test_type and self.test_type_code == 'COVID-19':
            # the use of 2 for template_id is intentional since covid-19 triage template ID will forever remain 2
            evals = self.env['oeh.medical.evaluation'].search(
                [('patient', '=', self.patient.id), ('template_id', '=', 2)], limit=5)
            domain = {'evaluation_id': [('id', 'in', evals.ids)]}
            return {'domain': domain}

    def set_to_sample_collected(self):
        return self.write({
            'state': 'Sample Collected',
            'sample_collection_date': datetime.now(),
            'sample_collected_by': self.write_uid.id
        })

    def set_to_test_inprogress(self):
        '''Set a default for care provider who is performing the test when the test is satrted '''
        external_user = self.env['res.users'].search([('login', '=', 'external_lab')], limit=1)
        care_provider = external_user if self.location == "External" else self.env.user
        return self.write({'state': 'Test In Progress', 'date_analysis': datetime.now(),
                           'care_provider_who_performed_test': care_provider.id})

    @api.depends('patient')
    def _compute_patient_age(self):
        """
        compute patient age to be displayed on the NCDC sample label
        """
        now = datetime.now()
        for rec in self:
            if rec.patient and rec.patient.dob:
                dob = datetime.strptime(rec.patient.dob.strftime("%Y-%m-%d"), '%Y-%m-%d')
                diff = now - dob
                age = diff.days // 365
                if age > 0:
                    rec.patient_age = '{} years'.format(age)
                else:
                    months = diff.days // 30
                    rec.patient_age = '{} months'.format(months)
            else:
                rec.patient_age = False 

    @api.model
    def create(self, vals):
        # generate a qr_code of the sample name and save to the database
        lab_test = super(OeHealthLabTestsExtension, self).create(vals)
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(lab_test.name)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="white", back_color="black")
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")
        qrcode_str = base64.b64encode(buffer.getvalue())
        lab_test.write({'qr_image': qrcode_str})
        lab_test.patient.write({'data_sync_hash': str(uuid.uuid4())})
        return lab_test

    def write(self, values):
        result = super(OeHealthLabTestsExtension, self).write(values)
        for res in self:
            # res.change_last_vitalsigns()
            res.patient.write({'data_sync_hash': str(uuid.uuid4())})
        return result

    @api.depends('create_date')
    def _compute_creation_time(self):
        """ This function creates a user friendly version of the time a test was created """
        for test in self:
            test.formatted_time = datetime.strftime(test.create_date, "%d %b %Y")

    def _default_account(self):
        account = self.env['ir.config_parameter'].sudo(
        ).get_param('oeh.default_lab_test_account')
        return account

    @api.depends('results')
    def _generate_short_result(self):
        for rec in self:
            if rec.results:
                rec.results_short = (
                        str(rec.results)[:180] + '..') if len(rec.results) > 180 else rec.results
            else:
                rec.results_short = {}

    def set_to_test_complete(self):
        # send lab review email
        for rec in self:
            if rec.care_provider_who_ordered_test.login:
                try:
                    ir_model_data = self.env['ir.model.data']
                    template_id = ir_model_data.get_object_reference('oehealth_extension', 'lab_review_email_template')[
                        1]
                    ctx = dict()
                    ctx.update({
                        'default_model': 'oeh.medical.lab.test',
                        'default_res_id': rec.id,
                        'default_use_template': bool(template_id),
                        'default_template_id': template_id,
                        'default_composition_mode': 'comment',
                        'email_to': rec.care_provider_who_ordered_test.login
                    })
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, True)
                except ValueError:
                    pass
                try:
                    rec._trigger_cloud_function()
                except Exception as e:
                    _logger.error(f"Error triggering labtest completion cloud function: {e}")
            # complete the test whatever happens above
            return self.write(
                {'state': 'Completed', 'date_completed': fields.Datetime.now(), 'date_analysis': fields.Datetime.now()})
            
    def _trigger_cloud_function(self):
        for rec in self:
            data = {}
            data["patientId"] = rec.patient.identification_code
            data['testName'] = rec.test_type.name
            api_key = self.env['ir.config_parameter'].sudo().get_param('healthmate_cloud_function_api_key')
            # url = "https://europe-west1-clinics-companion-app-dev.cloudfunctions.net/webApi/api/v1/notification/lab-test-available"
            url = self.env['ir.config_parameter'].sudo().get_param('oehealth_extension.labtest_complete_cloud_function_url_param')
            headers = {"X-API-KEY": api_key}
            requests.post(url=url, headers=headers, data=data)

    def set_to_test_reviewed(self):
        self.write({
            'state': 'Reviewed',
            'reviewer': self.env.user.id,
            'review_date': fields.Datetime.now()
        })

     

    def action_send_mail(self):
        view = self.env.ref('oehealth_extension.view_batch_labtest_emailing')
        return {
            'name': 'Send lab test mail',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'res_model': 'batch.labtest.emailing',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': {
                'default_is_individual_mail': True, 
                'default_is_specific_mail': False, 
            }
        }

    def email_generator(self, email_to, ids=False): 
        msg = ['Output message: \n']
        for rec in self:
            ids = rec.id if not ids else ids
            try:
                ir_model_data = self.env['ir.model.data']
                template_id = \
                ir_model_data.get_object_reference('oehealth_extension', 'labtest_email_template')[1]
                ctx = dict()

                ctx.update({
                    'default_model': 'oeh.medical.lab.test',
                    'default_res_id': ids,
                    'default_use_template': bool(template_id),
                    'default_template_id': template_id,
                    'default_composition_mode': 'comment',
                    # 'email_to': email if email else partner_mails
                    'name': '' if rec.test_type.name.endswith('Test') else 'Test'
                    # used this to pass a context that corrects the redundant tests word
                })
                 
                template_rec = self.env['mail.template'].browse(template_id)
                template_rec.write({'email_to': email_to})
                mail_rec = template_rec.with_context(ctx).send_mail(ids, True)
                rec.mail_log_ids = [(4, mail_rec)]
                msg.append(
                    "%s - successfully sent to %s" % (rec.name, email_to))
            except Exception as e:
                raise ValidationError("Error occurred while sending email %s" %e)
        if len(msg) > 1:
            message = '\n'.join(msg)
            return self.confirm_notification(message)

    def confirm_notification(self, popup_message):
        view = self.env.ref('oehealth_extension.oeh_confirm_dialog_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
            'name': 'Message!',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'res_model': 'oeh.confirm.dialog',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    @api.model
    def cron_sms_covid19_result(self):
        ''' cron method to sms covid-19 result to patients '''
        _logger.info('CRON CALLED')
        domain = [
            ('sms_status', '=', 'no'),
            ('test_type.code', '=', 'COVID-19'),
            ('state', '=', 'Completed'),
        ]
        cutoff_date = self.env['ir.config_parameter'].get_param('oehealth_extension.covid_sms_cutoff_date', False)
        max_retries = self.env['ir.config_parameter'].get_param('oehealth_extension.covid_sms_max_retries', False)
        if cutoff_date:
            domain.append(
                ('create_date', '>=', fields.Datetime.from_string(cutoff_date))
            )
        if max_retries:
            domain.append(
                ('covid19_sms_retry_count', '<', int(max_retries))
            )
        labtests = self.search(domain)
        _logger.info('LABTEST IDS %s' % labtests)
        labtests.send_sms_multi()

    @api.model
    def cron_send_lab_result_mail(self):
        ''' cron method to automatically send lab test result to patients '''
        _logger.info('LAB TEST MAIL SENT')
        """get the completed lab test which mail status is not sent (90 limit)
        then send a mail
        """
        dt_str = parser.parse(
            "05-19-2021 12:00:00").strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        print('================', dt_str)
        labs = self.env['oeh.medical.lab.test'].sudo().search([
            ('state', '=', 'Completed'),
                ('create_date', '>=', dt_str),
                ('test_type.code', '=', "COVID-19"),
                ('mail_log_ids', '=', False)
        ], order='id asc', limit=90)
        for rec in labs:
            rec.email_generator(rec.patient.email, False)

    def send_sms_multi(self):
        for rec in self:
            phone = rec.patient.phone or rec.patient.mobile
            valid_phone = rec.validate_format_phone(phone)
            if valid_phone:
                msg = '''
                    Hello {first_name} Your COVID-19 result is ready.
                    Download your result with Lab test number {labtest_no} on www.eha.ng/services/check-test-results.
                '''
                text = rec.env['ir.config_parameter'].sudo().get_param(
                    'oeha_lab.covid19.result.sms', msg)
                text = text.replace("{first_name}", rec.patient.firstname)
                text = text.replace("{labtest_no}", rec.name)
                _logger.info('QUOTED TEXT %s' % text)
                msg = 'not successful'
                try:
                    validated_phone = valid_phone.replace(
                        ' ', '')  # remove empty spaces
                    res = self.env['bulk.sms']._send_sms(
                        [validated_phone], text)
                    _logger.info('SMS Response %s' % res)
                    if res.get('status') in range(200, 205):
                        rec.sudo().write({'sms_status': 'yes'})
                        msg = 'successful'
                    else:
                        _logger.error(
                            f"{rec._name}: SMS Failed for labtest {rec.name} because {literal_eval(res.get('text')).get('title')}: {literal_eval(res.get('text')).get('detail')}")
                        print(
                            f"SMS not successful for labtest {rec.name}. The following error occured {literal_eval(res.get('text')).get('title')}: {literal_eval(res.get('text')).get('detail')}")
                except Exception as ex:
                    msg = ex.args[0]
                    _logger.exception(ex)

                vals = {
                    'model': 'oeh.medical.lab.test',
                    'ref': rec.name,
                        'phone': valid_phone,
                        'response_message': msg,
                        'text_message': text,
                }
                rec.sudo().write(
                    {'covid19_sms_retry_count': rec.covid19_sms_retry_count + 1})
                self.env['sms.log'].sudo().create(vals)

    def validate_format_phone(self, phone):
        if (not phone) or len(phone) < 11:
            return False

        forbidden_characters = [',', '.', '(', ')']
        if any((c in forbidden_characters) for c in phone):
            return False

        if (len(phone) == 11) and (phone[0] == '0'):
            return '+234' + phone[1:]
        return '+' + phone if phone[:3] == '234' else phone

    def hexDecimalColor(self, unique_list):
        res = "#%06x" % random.randint(0, 0xFFFFFF)
        result = res.upper() if res not in unique_list else self.hexDecimalColor(unique_list)
        return result

    def action_atila_export_and_download(self):
        attachment = self.env['ir.attachment']
        labobj = self.env['oeh.medical.lab.test']
        ids = self.env.context.get('active_ids', [])
        hexDecimalColorsList = []
        headers = ['SAMPLE ID #', 'COLOR', 'SAMPLE NAME',
            'SAMPLING TIME', 'SUBMITTING DATE']
        style0 = xlwt.easyxf(
            'font: name Times New Roman, color-index red, bold on', num_format_str='#,##0.00')
        style1 = xlwt.easyxf(num_format_str='DD-MMM-YYYY')
        wb = xlwt.Workbook()
        ws = wb.add_sheet('ATILA LAB TEST(S)')
        if ids:
            colh = 0
            for head in headers:
                ws.write(0, colh, head)
                colh += 1
            row = 1
            for counter, recs in enumerate(ids, 1):
                records = labobj.browse([recs])
                col = 0
                color_num = self.hexDecimalColor(hexDecimalColorsList)
                sample_name = records.name
                sample_collection_date = records.sample_collection_date.strftime(
                    "%Y-%m-%d %H:%M:%S") if records.sample_collection_date else ''
                exported_date = datetime.strftime(
                    datetime.now(), ("%Y-%m-%d %H:%M:%S"))
                ws.write(row, col, counter)
                ws.write(row, col + 1, color_num, style1)
                ws.write(row, col + 2, sample_name)
                ws.write(row, col + 3, sample_collection_date)
                ws.write(row, col + 4, exported_date)
                row += 1
                hexDecimalColorsList.append(color_num)
            fp = io.BytesIO()
            wb.save(fp)
            filename = "ATILA LAB TEXT GENERATED ON {}.xls".format(
                fields.Date.today(), style0)
            excel_file_binary = base64.encodestring(fp.getvalue())
            fp.close()
            # create attachment to print from
            attach_id = attachment.create({
                'name': filename,
                'datas': excel_file_binary,
                    'mimetype': "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    'res_id': 0,
                    'description': "Exported Atila lab tests created on {}".format(fields.Datetime.now())
            })
            auto_download_url = '/web/content/{0}/{1}?download=true'.format(
                attach_id.id, filename)
            return {
                'type': 'ir.actions.act_url',
                'url': auto_download_url,  # eg 'baseurl/web/content/2348/ATILA FILE?download=true',
                            'target': 'new',
                            'nodestroy': False,
            }
        else:
            raise ValidationError('No Labtest to Export')

    def _determine_age_unit(self, age_value):
        """This was used to arrange and get the unit of age as required by the PANABIOS
        Sample template"""
        res = 'Years'
        # eg . 34 years 233 days ==> ['34', 'years', '233', days']
        age_item = age_value.split(' ')
        if len(age_item) == 4:
            years, days = int(age_item[0]), int(age_item[2])
            if years > 0:
                res = "Years"
            else:
                if days > 29:
                    res = "Months"
                else:
                    res = "Days"
        return res

    def date_converter(self, date_str):
        if date_str:
            # e.g expected format 12/03/2029 01:09:23
            date_format = datetime.strftime(date_str, ("%m/%d/%Y %H:%M:%S"))
            date_res = date_format.split(' ')  # e.g ['12/03/2029', '01:09:23']
            data = date_res[0].split('/')  # e.g ['12', '03', '2029']
            if len(data) > 2:
                sm_days, sm_month, sm_yr = data[1], data[0], data[2]
                # e.g FORMAT FOR PANABIOS 03/12/2029
                result = '{}/{}/{}'.format(sm_days, sm_month, sm_yr)
            else:
                result = ""
            return result

    def action_panabios_export_and_download(self):
        attachment = self.env['ir.attachment']
        labtest = self.env['oeh.medical.lab.test']
        labtest_ids = self.env.context.get('active_ids', [])
        headers = ['REASON FOR TESTING', 'CASE ID', 'TYPE OF CASE (INITIAL/REPEAT)', 'SAMPLE NUMBER', 'NAME',  # 0 - 4
                   'ID/PASSPORT NUMBER', 'AGE/DOB', 'AGE UNIT (DAYS/MONTHS/YEARS)', 'GENDER (M/F)', 'PHONE NUMBER',
                   'OCCUPATION', 'NATIONALITY', 'REGION OF RESIDENCE', 'DISTRICT OF RESIDENCE', 'TOWN/VILLAGE OF RESIDENCE',
                   'WARD', 'REGION OF DIAGNOSIS', 'HAS TRAVEL HISTORY(LAST 14 DAYS) Y/N', 'TRAVEL FROM', 'CONTACT WITH CASE Y/N',
                   'CONFIRMED CASE NAME', 'QUARANTINE FACILITY/HOSPITAL/HOMESTEAD', 'HAVE SYMPTOMS Y/N', 'DATE OF ONSET OF SYMPTOMS',
                   'SYMPTOMS SHOWN (COUGH;FEVER;ETC)', 'SAMPLE TYPE (NP SWAB, OP SWAB, SERUM SPUTUM ETC)',
                   'DATE OF SAMPLE COLLECTION (DD/MM/YYYY)', 'DATE SAMPLE RECEIVED IN THE LAB(DD/MM/YYYY)', 'RESULT',
                   'LAB CONFIRMATION DATE(DD/MM/YYYY)', 'EMAIL ADDRESS', 'VACCINATION STATUS Y/N', 'DOSAGE C/NC'
                   ]
        style0 = xlwt.easyxf(
            'font: name Times New Roman, color-index red, bold on', num_format_str='#,##0.00')
        style1 = xlwt.easyxf(num_format_str='DD-MMM-YYYY')
        wb = xlwt.Workbook()
        ws = wb.add_sheet('PANABIOS EXPORTED LAB TEST(S)')
        if labtest_ids:
            exported_date = datetime.strftime(
                datetime.now(), ("%Y-%m-%d %H:%M:%S"))
            name_header = "COVID-19 RESULTS SUBMISSION FORM"
            col_4_msg = "Version 3 Effective :  December 2020 Export on: {}".format(
                exported_date)
            ws.write(0, 1, name_header)
            ws.write(0, 2, "Note: All headers in Red are required to be filled")
            ws.write(0, 3, col_4_msg)
            colh = 0
            for head in headers:
                ws.write(1, colh, head)
                colh += 1
            row = 2
            for recs in labtest_ids:
                records = labtest.browse([recs])
                state = records.patient.state_id.name
                reasonfortest = 2
                caseid = records.name
                typeofcase = "Initial"
                sample_num = records.name
                name_patient = records.patient.name,
                id_passport = records.patient.passport_no
                age_dob = str(
                    records.patient.age_int) if records.patient.age_int else records.patient.age
                age_unit = self._determine_age_unit(
                    records.patient.age) if records.patient.age else 'Years'
                age_unit = age_unit
                gender = 'M' if records.patient.gender == 'Male' else 'F'
                phone_number = records.patient.phone or records.patient.mobile
                occupation = ""
                nationality = records.patient.country_id.name or 'Nigeria'
                region_residence = '{} State'.format(
                    state) if state else 'Federal Capital Territory'
                district_of_residence = records.patient.city
                town_village = records.patient.street or records.patient.street2
                ward = records.patient.ward or records.patient.lga
                region_of_diagnosis = '{} State'.format(
                    state) if state else 'Federal Capital Territory'
                have_travel_history = 'No'
                travel_from = records.cif_ref.depature_country
                contact_with_case = ""
                confirm_case_name = ""
                quarantine_facility = "EHA CLINICS LTD"
                have_symptom = "No"
                date_of_onset_symptom = ""
                symptom_shown = ""
                sample_type = "NP Swab"
                sample_result_date = self.date_converter(
                    records.sample_collection_date)
                date_of_collection = sample_result_date
                date_sample_recieved = sample_result_date
                result_line = records.mapped('lab_test_criteria').filtered(
                    lambda x: x.sequence == 6)
                result_val = result_line[0].result if result_line else ''
                result = 'Negative' if result_val == 'Negative' else 'Positive'
                result_date = result_line[0].write_date if result_line else False
                result_confirm_date = self.date_converter(result_date)
                email = records.patient.email or records.patient.secondary_email
                vaccination_status = 'N'
                dosage = 'NC'
                col = 0

                ws.write(row, col, reasonfortest)
                ws.write(row, col + 1, caseid)
                ws.write(row, col + 2, typeofcase)
                ws.write(row, col + 3, sample_num)
                ws.write(row, col + 4, name_patient)

                ws.write(row, col + 5, id_passport)
                ws.write(row, col + 6, age_dob)
                ws.write(row, col + 7, age_unit)
                ws.write(row, col + 8, gender)

                ws.write(row, col + 9, phone_number)
                ws.write(row, col + 10, occupation)
                ws.write(row, col + 11, nationality)
                ws.write(row, col + 12, region_residence)

                ws.write(row, col + 13, district_of_residence)
                ws.write(row, col + 14, town_village)
                ws.write(row, col + 15, ward)
                ws.write(row, col + 16, region_of_diagnosis)

                ws.write(row, col + 17, have_travel_history)
                ws.write(row, col + 18, travel_from)
                ws.write(row, col + 19, contact_with_case)
                ws.write(row, col + 20, confirm_case_name)

                ws.write(row, col + 21, quarantine_facility)
                ws.write(row, col + 22, have_symptom)
                ws.write(row, col + 23, date_of_onset_symptom)
                ws.write(row, col + 24, symptom_shown)

                ws.write(row, col + 25, sample_type)
                ws.write(row, col + 26, date_of_collection)
                ws.write(row, col + 27, date_sample_recieved)
                ws.write(row, col + 28, result)
                ws.write(row, col + 29, result_confirm_date)
                ws.write(row, col + 30, email)
                ws.write(row, col + 31, vaccination_status)
                ws.write(row, col + 32, dosage)
                row += 1
            fp = io.BytesIO()
            wb.save(fp)
            filename = "{}".format('export.xlsx')
            excel_file_binary = base64.encodestring(fp.getvalue())
            fp.close()
            # create attachment to print from
            attach_id = attachment.create({
                'name': filename,
                'datas': excel_file_binary,
                    'mimetype': "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    'res_id': 0,
                    'description': "Exported PANABIOS created on {}".format(fields.Datetime.now())
            })
            auto_download_url = '/web/content/{0}/{1}?download=true'.format(
                attach_id.id, filename)
            return {
                'type': 'ir.actions.act_url',
                'url': auto_download_url,  # eg 'baseurl/web/content/2348/ATILA FILE?download=true',
                            'target': 'new',
                            'nodestroy': False,
            }
        else:
            raise ValidationError('No Labtest to Export')

    # def action_ncdc_labtest_sync(self):
    #     labtest_ids = self.env.context.get('active_ids')
    #     error_msg = ["The following Failed to sync"]
    #     success_msg = ["The following successfully synced to NCDC Portal"]
    #     for labtest_id in labtest_ids:
    #         try:
    #             record = self.browse([labtest_id])
    #             if record.test_type.allow_ncdc_sync:
    #                 ncdc_username = self.env['ir.config_parameter'].sudo(
    #                 ).get_param('eha_connector.ncdc_login_username')
    #                 ncdc_password = self.env['ir.config_parameter'].sudo(
    #                 ).get_param('eha_connector.ncdc_login_password')
    #                 result_interpretation = record.mapped('lab_test_criteria').filtered(
    #                     lambda name: name.name.startswith('Result Interpretation'))
    #                 payload = {"test_id": record.ncdc_test_id if record.ncdc_test_id else 0,
    #                            "passport_no" : record.patient.passport_no if record.patient.passport_no else None,
    #                             "first_name": record.patient.firstname,
    #                             "last_name": record.patient.lastname,
    #                             "other_names": record.patient.lastname2 if record.patient.lastname2 else None,
    #                             "cert_no": record.ncdc_cert_number,
    #                             "result_status": result_interpretation[0].result if result_interpretation else '',
    #                             "sampling_date": convert_date_to_iso(fields.Datetime.to_string(record.sample_collection_date)) if record.sample_collection_date else convert_date_to_iso(fields.Datetime.to_string(record.date_requested)),
    #                             "sampling_time": convert_time(tolocale_time(record.sample_collection_date).split(' ')[1] if record.sample_collection_date else tolocale_time(record.date_requested).split(' ')[1]),
    #                             "test_name": record.test_type.name,
    #                             "methodology": "Real-Time PCR" if "RDT" not in str(record.test_type.code).split(" ") else "Rapid Diagnostic Test",
    #                             "sample_type": "Nasopharyngeal Swab",
    #                             "test_purpose": "Other Reasons" if record.cif_ref else "Travel Requirement",
    #                             "gender": record.patient.sex,
    #                             "age": ' '.join(str(record.patient.age).split(' ')[:2]),
    #                             "email": record.patient.email if record.patient.email else record.patient.secondary_email,
    #                             "phone": record.patient.phone if record.patient.phone else record.patient.mobile,
    #                             "access_key": "{}&{}".format(ncdc_username, ncdc_password)
    #                            }

    #                 res = requests.post(
    #                     'https://rv.ncdc.gov.ng/Verify/PushResult', data=payload, timeout=60)
    #                 res_json = res.json()

    #                 values = {
    #                     "labtest_no": record.name,
    #                     "response_code": res.status_code,
    #                         "response_message": res_json.get("feedback")
    #                 }

    #                 # 'feedback': 'Certificate Number Already Exists'
    #                 if res_json.get("is_success") or res_json.get('feedback', '').lower() == "certificate number already exists":
    #                     _logger.info("[*] Report push status: Success")
    #                     values["is_success"] = True
    #                     record.update(
    #                         {"ncdc_sent_status": True, "ncdc_test_id": res_json.get("test_id")})
    #                     success_msg.append(
    #                         f"Labtest successfully synced ==>. {record.name}")

    #                 else:
    #                     _logger.info(
    #                         "[*] Report push status: Failed %s" % res_json)
    #                     error_msg.append(f"Error. {res_json}")
    #                 log_instance = self.env['ncdc.log'].sudo().search(
    #                     [('labtest_no', '=', record.name)])
    #                 if log_instance:
    #                     values["date_attempted"] = datetime.now()
    #                     log_instance.sudo().write(values)
    #                 else:
    #                     self.env['ncdc.log'].sudo().create(values)
    #                 success_msg.append(f"Labtest No. {record.name}")

    #             else:
    #                 error_msg.append(
    #                     f"Labtest No. {record.name} Not allowed to be synced")
    #         except Exception as ex:
    #             _logger.exception(ex)
    #             error_msg.append(f" NCDC Upload Error Occured:. {ex}")
    #             _logger.info("[*] NCDC Batch Sync Error Occured! %s" % ex)
    #     errs = error_msg + success_msg
    #     message = '\n'.join(errs)
    #     return self.confirm_notification(message)


class OeHealthLabTestTypesExtension(models.Model):
    _inherit = 'oeh.medical.labtest.types'
    _description = 'Lab Test Types Extension'

    allow_ncdc_sync = fields.Boolean('Allow NCDC syncing', help="Allow NCDC syncing")
    allow_panabios_sync = fields.Boolean('Allow Panabios syncing', help="Allow Panabios syncing")
    is_covid_19 = fields.Boolean('Is Covid 19 Test', default=True)
    is_covid_pcr = fields.Boolean('Is Covid 19 PCR Test')
    is_covid_antigen = fields.Boolean('Is Covid 19 Antigen Test')
    active = fields.Boolean(string="Active", default=True)


class OehaLabReasonModel(models.Model):
    _name = "oeha.lab.reason.model"
    _description = "Lab test Reason Model"

    name = fields.Char(string="Name")
    related_partner_tag = fields.Many2many(
        'res.partner.category', string='Related Tags')
    partner_reference_line = fields.One2many('oeha.partner.reference.line', 'lab_reason_id',
                                             string='Partner Reference Line')


class OehaPartnerReferenceLine(models.Model):
    _name = "oeha.partner.reference.line"
    _description = "Reason Reference Line"

    lab_reason_id = fields.Many2one("oeha.lab.reason.model")
    partner_id = fields.Many2one("res.partner", string="Partner")
    related_cif_ids = fields.Many2many(
        'oeha.covid19.cif', string='Related CIF IDs')


class OehaTestTypeCategory(models.Model):
    _name = "oeha.test_type.category"
    _description = "Model for test type category"
