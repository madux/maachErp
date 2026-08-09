from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import ValidationError
from odoo import http


class PMSJobCategory(models.Model):
    _name = "pms.category"
    _description= "PMS Template category based on job roles"
    _inherit = "mail.thread"

    name = fields.Char(
        string="Name", 
        required=True)
    
    category = fields.Many2one('hr.level.category', string="Category")
    sequence = fields.Char(
        string="Sequence")
        
    kra_weighted_score = fields.Integer(
        string='Key Result Area Section - Weight (%)', 
        required=True,
        )
    fc_weighted_score = fields.Integer(
        string='Functional Competency Section Weight (%)', 
        required=True,
        )
    lc_weighted_score = fields.Integer(
        string='Leadership Competency Section Weight (%)', 
        required=True,
        )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancel', 'Cancel'),
        ], string="Status", default = "draft", readonly=True)
    publish_to_employees = fields.Selection([
        ('Employees', 'Employees'),
        ('Department', 'Department'),
        ], string="Publish To", default = "Employees", readonly=False)
    
    pms_year_id = fields.Many2one(
        'pms.year', string="Period")
    allow_mid_year_review = fields.Boolean(string="Allow Mid year review",
                                           help="Allow the appraisee to start Mid year review")
    allow_annual_review_submission = fields.Boolean(
        string="Allow Full Appraisal", 
        help="Allow the appraisee to start Full Appraisal")
    type_of_pms = fields.Selection([
        ('gs', 'Goal Setting'),
        ('hyr', 'Mid year review'),
        ('fyr', 'Full Appraisal'),
        ], string="Type of PMS", default = "gs", 
        copy=True)
    date_from = fields.Date(
        string="Date From", 
        readonly=False, 
        store=True)
    date_end = fields.Date(
        string="Date End", 
        readonly=False,
        store=True
        )
    deadline = fields.Date(
        string="Deadline Date", 
        store=True)
    
    online_deadline_date = fields.Date(
        string="Online Deadline Date", 
        store=True)

    published_date = fields.Date(
        string="Published date", 
        readonly=True, 
        store=True)
    
    loaded_via_data = fields.Boolean(
        string="Loaded via data", 
        readonly=True, 
        default=False, 
        store=True)

    job_role_ids = fields.Many2many(
        'hr.job', 
        string="Job role"
        )
    section_ids = fields.Many2many(
        'pms.section',
        'pms_section_category_rel',
        'category_id',
        'section_id',
        string="Sections"
    )
    missing_employee_ids = fields.Many2many(
        'hr.employee',
        'hr_employee_missing_rel',
        'pms_id',
        'employee_id',
        string="Missing Employees"
    )
    pms_department_ids = fields.Many2many(
        'pms.department', 
        'pms_department_category_rel', 
        'department_id', 
        'category_id',
        string="PMS Department ID")

    active = fields.Boolean(
        string="Active", 
        readonly=True, 
        default=True, 
        store=True)
    
    @api.onchange('category')
    def onchange_category(self):
        if self.category:
            job_role_ids = self.category.job_role_ids
            self.job_role_ids = job_role_ids

    # @api.constrains('category')
    # def check_category(self):
    #     exists = self.env['pms.category'].search([
    #         ('category', '=', self.category.id), 
    #         ('pms_year_id', '=', self.pms_year_id.id)
    #         ])
    #     if len(exists) > 1:
    #         raise ValidationError(f'You have already created a template with PMS category and same period using {self.category}')

    @api.constrains('job_role_ids')
    def _check_lines(self):
        kra_types = self.mapped('section_ids').filtered(lambda se: se.type_of_section in ['KRA'])
        fc_types = self.mapped('section_ids').filtered(lambda se: se.type_of_section in ['FC'])
        lc_types = self.mapped('section_ids').filtered(lambda se: se.type_of_section in ['LC'])
        if not self.loaded_via_data and not self.mapped('job_role_ids') and not any([kra_types,fc_types,lc_types]):
            raise ValidationError('You must assign at least one job role')
        
    @api.constrains('kra_weighted_score', 'fc_weighted_score', 'lc_weighted_score')
    def check_weights(self):
        weight_total = self.kra_weighted_score + self.fc_weighted_score + self.lc_weighted_score
        if weight_total != 100:
            raise ValidationError("Total of KRA, LC and FC must sum up to 100%")

    @api.onchange('pms_year_id')
    def onchange_year_id(self):
        '''Gets the periodic date interval from the settings'''
        if self.pms_year_id:
            self.date_from = self.pms_year_id.date_from
            self.date_end = self.pms_year_id.date_end
        else:
            self.date_from = False
            self.date_end = False

    def action_notify(self, subject, msg, email_to, email_cc):
        email_from = self.env.user.email
        email_ccs = list(filter(bool, email_cc))
        reciepients = (','.join(items for items in email_ccs)) if email_ccs else False
        mail_data = {
                'email_from': f'"LAYER3" <notifications@layer3.com.ng>',
                'subject': subject,
                'email_to': email_to,
                'reply_to': email_from,
                'email_cc': reciepients,
                'body_html': msg,
                # 'state': 'sent'
            }
        mail_id = self.env['mail.mail'].sudo().create(mail_data)
        # mail_id.action_send_and_close()
        # self.env['mail.mail'].sudo().send(mail_id)
        # self.message_post(body=msg)
    
    def get_url(self, id, name):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_id = self.env.ref('hr_pms.action_pms_category_view')
        base_url += f'/odoo/action-{action_id.id}/{id}'
        # base_url += '/web#id=%d&view_type=form&model=%s' % (id, name)
        return "<a href={}> </b>Click<a/>. ".format(base_url)

    test_employee_id = fields.Many2one('hr.employee', string = "Test employee")
    def test_send_mail_notification(self):
        if not self.test_employee_id:
            raise ValidationError("Please select employee for test")
        self.action_notify('TEST SUBJECT', "message for testing", self.test_employee_id.work_email, [])

    def action_resend_mail(self):
        for dept in self.pms_department_ids:
            related_appraisals = self.env['pms.appraisee'].search([
                    ('pms_department_id', '=', dept.id),('active', '=', True)
                    ])
            for rec in related_appraisals:
                if rec.employee_id:
                    msg = """Dear {}, <br/> 
                        I wish to notify you that an appraisal was sent to you.\
                        <br/>Kindly {} to review <br/>\
                        Yours Faithfully<br/>{}<br/>HR Department ({})""".format(
                            rec.employee_id.name,
                            rec.get_url(rec.id, rec._name),
                            self.env.user.name,
                            "HR Department",
                            )
                    rec.action_notify(
                        'Employee Appraisal Notification',
                        msg,
                        rec.employee_id.work_email,
                        [],
                        ) 
                    
    def send_mail_notification(self, pms_department_obj):
        subject = "Appraisal Notification"
        department_manager = pms_department_obj.department_id.manager_id
        if department_manager:
            email_to = department_manager.work_email
            email_cc = [] #[rec.work_email for rec in self.approver_ids]
            msg = """Dear {}, <br/>
                I wish to notify you that an appraisal template with description, {} \
                has been initialized. You may proceed with publishing it out \
                to staff under your department (Unit).<br/>\
                <br/>Kindly {} to review <br/>\
                Yours Faithfully<br/>{}<br/>HR Department ({})""".format(
                department_manager.name,
                self.name, 
                self.get_url(pms_department_obj.id, pms_department_obj._name),
                self.env.user.name,
                self.env.user.company_id.name,
                )
            self.action_notify(subject, msg, email_to, email_cc)
        else:
            # raise ValidationError(
            #     """
            #     There is no work email address found for the
            #     department manager- {}:""".format(
            #     pms_department_obj.department_id.name)
            # )
            pass
        
    def check_job_role_without_department(self):
        jr = self.mapped('job_role_ids').filtered(
            lambda jr: not jr.department_id)
        if jr:
            raise ValidationError(
                """
                    Please ensure all the selected job roles has departments setup
                """
                )

    def button_send_missing_appraisal(self):
        PMS_Appraisee = self.env['pms.appraisee']
        if not self.missing_employee_ids:
            raise ValidationError("Please employee to send to")
        # check if the employee record has been generated before 
        for emp in self.missing_employee_ids:
            level_type_id = self.env.ref('hr_pms.hr_level_jcategory_jm') if emp.level_id.name == "Entry-Level" else self.env.ref('hr_pms.hr_level_jcategory_jm_two') if emp.level_id.name == 'Intermidate' else self.env.ref('hr_pms.hr_level_jcategory_mm') if emp.level_id.name == 'Advanced' else self.env.ref('hr_pms.hr_level_jcategory_sm') if emp.level_id.name == 'Expert' else False
            level_type_id = level_type_id.id if level_type_id else False
            department_pms_ref = self.mapped('pms_department_ids').filtered(
            lambda s: s.department_id.id == emp.department_id.id and s.hr_category_id.category.id == level_type_id)

            appraisal_existing = self.env['pms.appraisee'].search(
            [('employee_id', '=', emp.id),
            '|', ('template_category_id', '=', self.id), ('pms_department_id', '=', department_pms_ref.id)], limit=1)
            # level_type_name = 'JM' if categ_name == 'Junior Management' else 'MM' if categ_name == 'Middle Management' else 'SM' 
            if appraisal_existing:
                raise ValidationError(f"An appraisal record has already been generated for {emp.name}")
            if not department_pms_ref:
                raise ValidationError(f"""
                System cannot find any match for {emp.name} department: {emp.department_id.name} {emp.department_id.id} linked to this template,
                 check if there has been template published for this department
                  under department tab. {emp.name} has level as {level_type_id and level_type_id.category} {level_type_id}""")
            
            if not emp.job_id:
                raise ValidationError(f"""
                 Employee : {emp.name} does not have designation or job id
                 """)
            appraises = []
            pms_appraisee = PMS_Appraisee.create({
                'name': 'GOAL SETTING:' if self.type_of_pms == 'gs' else 'APPRAISAL:'+ self.name + emp.name, 
                'department_id': emp.department_id.id, 
                'employee_id': emp.id, 
                'pms_department_id': department_pms_ref[0].id,
                'template_category_id': self.id,
                'pms_year_id': self.pms_year_id.id,
                'type_of_pms': self.type_of_pms,
                'state': 'goal_setting_draft' if self.type_of_pms in ['gs', 'hyr'] else 'draft',
                'date_from': self.pms_year_id.date_from,
                'date_end': self.pms_year_id.date_end,
                'deadline': self.deadline,
            }) 
            appraises.append(pms_appraisee)
            kra_pms_department_section = self.mapped('section_ids').filtered(
                lambda res: res.type_of_section == "KRA")
            if kra_pms_department_section:
                kra_section = kra_pms_department_section[0]
                kra_section_lines = kra_section.section_line_ids
                pms_appraisee.write({
                    'kra_section_line_ids': [(0, 0, {
                                                'kra_section_id': pms_appraisee.id,
                                                'name': secline.name,
                                                'is_required': secline.is_required,
                                                # 'section_avg_scale': kra_section.section_id.section_avg_scale,
                                                'section_avg_scale': kra_section.section_avg_scale,
                                                'weightage': 0,
                                                'administrative_supervisor_rating': 0,
                                                'functional_supervisor_rating': 0,
                                                'self_rating': 0,
                                                }) for secline in kra_section_lines] 
                })
            fc_pms_department_section = self.mapped('section_ids').filtered(
                lambda res: res.type_of_section == "FC")
            if fc_pms_department_section:
                fc_section = fc_pms_department_section[0]
                fc_section_lines = fc_section.section_line_ids
                if fc_section_lines:
                    pms_appraisee.write({
                        'fc_section_line_ids': [(0, 0, {
                                                    'fc_section_id': pms_appraisee.id,
                                                    'name': sec.name,
                                                    'is_required': sec.is_required,
                                                    'weightage': fc_section.input_weightage,
                                                    # 'section_avg_scale': fc_section.section_id.section_avg_scale,
                                                    'section_avg_scale': fc_section.section_avg_scale,
                                                    'administrative_supervisor_rating': 0,
                                                    'functional_supervisor_rating': 0,
                                                    'reviewer_rating': 0,
                                                    }) for sec in fc_section_lines] 
                    })
                else:
                    pms_appraisee.write({
                        'fc_section_line_ids': [(0, 0, {
                                                    'fc_section_id': pms_appraisee.id,
                                                    'name': 'Functional Competency',
                                                    'is_required': False,
                                                    'weightage': fc_section.input_weightage,
                                                    # 'section_avg_scale': fc_section.section_id.section_avg_scale,
                                                    'section_avg_scale': fc_section.section_avg_scale,
                                                    'administrative_supervisor_rating': 0,
                                                    'functional_supervisor_rating': 0,
                                                    'reviewer_rating': 0,
                                                    })] 
                    })


            lc_pms_department_section = self.mapped('section_ids').filtered(
                lambda res: res.type_of_section == "LC")
            if lc_pms_department_section:
                lc_section = lc_pms_department_section[0]
                lc_section_lines = lc_section.section_line_ids
                pms_appraisee.write({
                    'lc_section_line_ids': [(0, 0, {
                                                'lc_section_id': pms_appraisee.id,
                                                'name': secline.name,
                                                'is_required': secline.is_required,
                                                # 'section_avg_scale': lc_section.section_id.section_avg_scale,
                                                'section_avg_scale': lc_section.section_avg_scale,
                                                'weightage': lc_section.input_weightage,
                                                'administrative_supervisor_rating': 0,
                                                'functional_supervisor_rating': 0,
                                                'section_line_id': secline.id,
                                                'kba_descriptions': '\n'.join([kbline.name for kbline in secline.kba_description_ids]),
                                                }) for secline in lc_section_lines] 
                })
            # current_assessment
            self.env['pms.department'].get_current_assessment_lines(pms_appraisee)
            # potential_assessment
            self.env['pms.department'].get_potential_assessment_lines(pms_appraisee)
            email_items = [
                emp.administrative_supervisor_id.work_email,
                emp.reviewer_id.work_email,
                emp.parent_id.work_email,
            ]
            self.env['pms.department'].action_notify(emp, pms_appraisee, emp.work_email, email_items)
            return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Notification',
                        'message': f'Appraisal record has been created ',
                        'type': 'success',
                        'sticky': True,
                    }
                }

    def button_publish(self):
        cancelled_pms_department_ids = self.mapped('pms_department_ids').filtered(
            lambda s: s.state == 'cancel')
        if cancelled_pms_department_ids:
            self.pms_department_ids = [(3, rec.id) for rec in cancelled_pms_department_ids]
        #########
        if self.job_role_ids and self.section_ids:
            self.check_job_role_without_department()
            # filters set of departments to forward generate
            department_ids = set([depart.department_id.id for depart in self.job_role_ids])
            Pms_Department = self.env['pms.department']
            # raise ValidationError(self.section_ids[1].input_weightage)
            if department_ids:
                # create pms.department record
                for dep in department_ids:
                    department_id = self.env['hr.department'].browse([dep])
                    pms_department = Pms_Department.create({
                        'name': self.name,
                        'department_id': department_id.id,
                        'department_manager_id': department_id.manager_id.id,
                        'pms_year_id': self.pms_year_id.id,
                        'type_of_pms': self.type_of_pms,
                        'date_from': self.pms_year_id.date_from,
                        'date_end': self.pms_year_id.date_end,
                        'deadline': self.deadline,
                        'state': 'review',
                        'hr_category_id': self.id,
                        'section_line_ids': [(0, 0, {
                            # creating pms.department.section
                            'section_id': sec.id,
                            'dep_input_weightage': sec.input_weightage,
                            'name': sec.name,
                            'max_line_number': sec.max_line_number,
                            'min_line_number': sec.min_line_number,
                            'type_of_section': sec.type_of_section,
                            'pms_category_id': self.id,
                            # 'weighted_score': sec.weighted_score,
                            'section_avg_scale': sec.section_avg_scale,
                            # creating pms.department.section.line
                            'section_line_ids': [(0, 0, {
                                'name': sec_line.name,
                                'section_line_id': sec_line.id,
                                'section_id': sec.id,
                                'is_required': sec_line.is_required,
                                'description': sec_line.description,
                                'kba_description_ids': [(0, 0, {
                                    'name': kba.name,
                                }) for kba in sec_line.kba_description_ids],
                            }) for sec_line in sec.section_line_ids]
                        }) for sec in self.section_ids],
                        
                    })
                    # if publish_to_employees is set to YES: 
                    if self.publish_to_employees == 'Employees':
                        pms_department.button_publish()
                        
                    # for sec in self.section_ids:
                    #     vals = {
                    #         'pms_department_id': pms_department.id,
                    #         'section_id': sec.id,
                    #         'input_weightage': sec.input_weightage,
                    #         'name': sec.name + 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                    #         'max_line_number': sec.max_line_number,
                    #         'type_of_section': sec.type_of_section,
                    #         'pms_category_id': self.id,
                    #         # 'weighted_score': sec.weighted_score,
                    #         'section_avg_scale': sec.section_avg_scale,
                    #     }
                    #     pms_dep_section_id = self.env['pms.department.section'].create(vals)
                    #     for sec_line in sec.mapped('section_line_ids'):
                    #         vals = {
                    #             'pms_department_section_id': pms_dep_section_id.id,
                    #             'name': sec_line.name + 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                    #             'section_id': sec.id,
                    #             'is_required': sec_line.is_required,
                    #             'description': sec_line.description,
                    #         }
                    #         self.env['pms.department.section.line'].create(vals)

                    # after generating the record, send notification email
                    self.write({
                        'pms_department_ids': [(4, pms_department.id)], 
                        })
                    self.send_mail_notification(pms_department)
            self.write({
                'state':'published',
                'published_date': fields.Date.today(),
            })
        else:
            raise ValidationError('Please add sections and job roles')
    
    def _message_post(self, template):
        """Wrapper method for message_post_with_template
        Args:
            template (str): email template
        """
        if template:
            ir_model_data = self.env['ir.model.data']
            # template_id = ir_model_data.get_object_reference('hr_pms', template)[1]
            template_id = self.env.ref(f'hr_pms.{template}')
            self.message_post_with_template(
                template_id, composition_mode='comment',
                model='{}'.format(self._name), res_id=self.id,
                email_layout_xmlid='mail.mail_notification_light',
            )
     
    def button_cancel(self):
        for rec in self.mapped('pms_department_ids'): #.filtered(
            # lambda s: s.state in ['draft', 'review']):
            rec.write({'active': False, 'state': 'cancel'})
            rec.button_cancel()
        self.write({
                'state':'cancel'
            })
    
    def button_republish(self):
        for rec in self.env['pms.department'].search([('active', '=', False), ('hr_category_id', '=', self.id)]):
            rec.write({'active': True, 'state': 'review'})
            rec.button_undo_cancel()

        self.write({
                'state':'published'
            })
        
    def button_set_to_draft(self):
        self.write({
                'state':'draft'
            })