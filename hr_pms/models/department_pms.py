from datetime import datetime, timedelta
import time
import base64
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo import http
import logging
from lxml import etree

_logger = logging.getLogger(__name__)


class PMS_Department_SectionLine(models.Model):
    _name = "pms.department.section.line"
    _inherit = "pms.section.line"
    _description= "Department Section lines"

    pms_department_section_id = fields.Many2one(
        'pms.department.section', 
        string="PMS Department section ID"
        )
    section_line_id = fields.Many2one(
        'pms.section.line', 
        string="Attributes"
        )
    kba_description_ids = fields.One2many(
        'kba.descriptions',
        'pms_section_line_id',
        string="KBA Description",) 

class PMS_Department_Section(models.Model):
    _name = "pms.department.section"
    _inherit = "pms.section"
    _description= "Department Sections"

    name = fields.Char(
        string="Description", 
        required=True)
    dep_input_weightage = fields.Float(
        string="Weightage",
        )
    
    pms_department_id = fields.Many2one(
        'pms.department', 
        string="PMS Department ID"
        )
    section_line_ids = fields.One2many(
        "pms.department.section.line",
        "pms_department_section_id",
        string="Department Section Lines"
    )
    section_id = fields.Many2one(
        'pms.section', 
        string="Section ID"
        )
    
    @api.onchange('min_line_number', 'max_line_number')
    def onchange_min_max_limit(self):
        if self.min_line_number > self.max_line_number:
            self.max_line_number = 7
            self.min_line_number = 5
            message = {
                'title': 'Invalid',
                'message': 'Minimum limit must not be greater than Maximum limit'
            }
            return {'warning': message}

class PMSDepartment(models.Model):
    _name = "pms.department"
    _description= "Department PMS to hold templates sent by HR  team for Appraisal conduct."
    _inherit = ['mail.thread']

    department_id = fields.Many2one(
        'hr.department', 
        string="Department ID"
        )
    
    hr_category_id = fields.Many2one(
        'pms.category', 
        string="Job category ID",
        required=True
        )
    sequence = fields.Char(
        string="Sequence")
    
    name = fields.Char(
        string="Description"
        )
    
    department_manager_id = fields.Many2one(
        'hr.employee', 
        string="Manager"
        )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Review'),
        ('published', 'Published'),
        ('cancel', 'Cancel'),
        ], string="Status", default = "draft", readonly=True)
    pms_year_id = fields.Many2one(
        'pms.year', 
        string="Period"
        )
    date_from = fields.Date(
        string="Date From", 
        readonly=True, 
        store=True)
    date_end = fields.Date(
        string="Date End", 
        readonly=True,
        store=True
        )
    deadline = fields.Date(
        string="Deadline Date", 
        readonly=True,
        store=True)

    is_department_head = fields.Boolean(
        'Is department Head',
        help="Determines if the user is a department head",
        store=True,
        # compute="check_department_head"
        )
    section_line_ids = fields.One2many(
        "pms.department.section",
        "pms_department_id",
        string="Department Section Lines"
    )
    type_of_pms = fields.Selection([
        ('gs', 'Goal Setting'),
        ('hyr', 'Mid year review'),
        ('fyr', 'Full Appraisal'),
        ], string="Type of PMS", default = "gs", 
        copy=True)
    active = fields.Boolean(
        string="Active", 
        readonly=True, 
        default=True, 
        store=True)

    @api.onchange('department_id')
    def onchange_department_id(self):
        if self.department_id:
            self.department_manager_id = self.department_id.parent_id.id
     
    def get_current_assessment_lines(self, appraisee): 
        vals = [
            'Administrative Appraiser',
            'Functional Appraiser',
            'Functional Reviewer',
            ]
        appraisee.sudo().write({
            'current_assessment_section_line_ids': [(0, 0, {
                'name': value,
                'state': 'admin_rating' if value == 'Administrative Appraiser' else 'functional_rating' if value == 'Functional Appraiser' else 'reviewer_rating', 
                # 'desc': value.desc,
                # 'weightage': 100/len(vals), # divided the num of lines to get 100% eg. 100/4
                'current_assessment_section_id': appraisee.id
                }) for value in vals]
        })
    
    def get_potential_assessment_lines(self, appraisee):
        vals = [
            'Administrative Appraiser',
            'Functional Appraiser',
            'Functional Reviewer',
            ]
    
        appraisee.sudo().write({
            'potential_assessment_section_line_ids': [(0, 0, {
                'name': value, 
                'state': 'admin_rating' if value == 'Administrative Appraiser' else 'functional_rating' if value == 'Functional Appraiser' else 'reviewer_rating', 
                # 'desc': value.desc,
                # 'weightage': 100/len(vals), # divided the num of lines to get 100% eg. 100/4
                'potential_section_id': appraisee.id
                }) for value in vals]
        })

    def get_url(self, id, name):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_id = self.env.ref('hr_pms.action_pms_department_view_id')
        base_url += f'/odoo/action-{action_id.id}/{id}'
        # base_url += '/web#id=%d&view_type=form&model=%s' % (id, name)
        return "<a href={}> </b>Click<a/>. ".format(base_url) 

    def action_notify(self, employee, rec, email_to, email_cc):
        email_from = self.env.user.email
        subject = "Employee Appraisal Notification"
        msg = """Dear {}, <br/> 
        I wish to notify you that your appraisal with description {} <br/>\
        for the period {} has been generated.<br/>\
        <br/>Kindly {} to review <br/>\
        Yours Faithfully<br/>{}<br/>HR Department ({})""".format(
            employee.name,
            self.name,
            self.pms_year_id.name,
            self.get_url(rec.id, rec._name),
            self.env.user.name,
            self.department_id.name,
            )
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
        # self.env['mail.mail'].sudo().send(mail_id)
        # mail_id.action_send_and_close()
    test_employee_id = fields.Many2one('hr.employee', string = "Test employee")
    def test_action_notify(self):
        if not self.test_employee_id:
            raise ValidationError("ERROR: please select test employee id")
        email_from = self.env.user.email
        subject = "TEST Employee Appraisal Notification"
        msg = """Dear {}, <br/> 
        I wish to notify you that your appraisal with description {} <br/>\
        for the period {} has been generated.<br/>\
        <br/>Kindly {} to review <br/>\
        Yours Faithfully<br/>{}<br/>HR Department ({})""".format(
            self.test_employee_id.name,
            self.name,
            self.pms_year_id.name,
            self.get_url(rec.id, rec._name),
            self.env.user.name,
            self.department_id.name,
            )
        email_ccs = list(filter(bool, email_cc))
        reciepients = (','.join(items for items in email_ccs)) if email_ccs else False
        mail_data = {
                'email_from': f'"LAYER3" <notifications@layer3.com.ng>', 
                'subject': subject,
                'email_to': self.test_employee_id.work_email,
                'reply_to': email_from,
                # 'email_cc': reciepients,
                'body_html': msg,
                # 'state': 'sent'
            }
        mail_id = self.env['mail.mail'].sudo().create(mail_data)
        # self.env['mail.mail'].sudo().send(mail_id)
        # mail_id.action_send_and_close()
    # TODO Add publish button with security as PMS Officer,
    # Ensure all the appraisals sent to employees will be activated or published
    def button_publish(self):
        '''Publishing the records to employees of the department'''
        if not self.section_line_ids:
            raise ValidationError(
                """Please ensure section line is added"""
            )
        Employee = self.env['hr.employee']
        PMS_Appraisee = self.env['pms.appraisee']
        job_position_ids = self.hr_category_id.mapped('job_role_ids').filtered(
            lambda se: se.department_id.id == self.department_id.id)
        appraises = []
        categ_name = self.hr_category_id.category.category
        # THIS IS TO PREVENT DUPLICATE APPRAISAL
        level_type_name = 'Entry-Level' if categ_name in ['Junior Management', 'Junior_Management_two'] else 'Intermidate' if categ_name in ['Junior_Management_two'] else 'MM' if categ_name == 'Advanced' else 'Expert' 
        for jb in job_position_ids:
            employees = Employee.search([
                ('job_id', '=', jb.id),
                # ('department_id', '=', jb.department_id.id),
                ('level_id.name', '=', level_type_name)
                ])
            if employees:
                for emp in employees:
                    pms_appraisee = PMS_Appraisee.create({
                        'name': 'GOAL SETTING:' if self.type_of_pms == 'gs' else 'APPRAISAL:'+ self.name + emp.name, 
                        'department_id': emp.department_id.id, 
                        'employee_id': emp.id, 
                        'pms_department_id': self.id,
                        'template_category_id': self.hr_category_id.id,
                        'pms_year_id': self.pms_year_id.id,
                        'type_of_pms': self.type_of_pms,
                        'state': 'goal_setting_draft' if self.type_of_pms in ['gs', 'hyr'] else 'draft',
                        'date_from': self.pms_year_id.date_from,
                        'date_end': self.pms_year_id.date_end,
                        'deadline': self.deadline,
                    }) 
                    appraises.append(pms_appraisee)
                    kra_pms_department_section = self.mapped('section_line_ids').filtered(
                        lambda res: res.type_of_section == "KRA")
                    if kra_pms_department_section:
                        kra_section = kra_pms_department_section[0]
                        kra_section_lines = kra_section.section_line_ids
                        # raise ValidationError(f"Thee scale is {kra_section.section_avg_scale}")
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
                    fc_pms_department_section = self.mapped('section_line_ids').filtered(
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
                                                            'weightage': fc_section.section_id.input_weightage,
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
                                                            'weightage': fc_section.section_id.input_weightage,
                                                            # 'section_avg_scale': fc_section.section_id.section_avg_scale,
                                                            'section_avg_scale': fc_section.section_avg_scale,
                                                            'administrative_supervisor_rating': 0,
                                                            'functional_supervisor_rating': 0,
                                                            'reviewer_rating': 0,
                                                            })] 
                            })


                    lc_pms_department_section = self.mapped('section_line_ids').filtered(
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
                                                        'weightage': lc_section.section_id.input_weightage,
                                                        'administrative_supervisor_rating': 0,
                                                        'functional_supervisor_rating': 0,
                                                        'section_line_id': secline.section_line_id.id,
                                                        'kba_descriptions': '\n'.join([kbline.name for kbline in secline.kba_description_ids]),
                                                        }) for secline in lc_section_lines] 
                        })
                    # current_assessment
                    self.get_current_assessment_lines(pms_appraisee)
                    # potential_assessment
                    self.get_potential_assessment_lines(pms_appraisee)
                    email_items = [
                        emp.administrative_supervisor_id.work_email,
                        emp.reviewer_id.work_email,
                        emp.parent_id.work_email,
                    ]
                    self.action_notify(emp, pms_appraisee, emp.work_email, email_items)
            # else:
            #     raise ValidationError(f'System does not have employees under the cateogry - {level_type_name}  and roles {jb.name}')
        # raise ValidationError(appraises)
        self.write({
            'state':'published'
        })
    
    def button_cancel(self):
        for rec in self:
            related_appraisals = self.env['pms.appraisee'].search([
                ('pms_department_id', '=', rec.id),('active', '=', True)
                ])
            for app in related_appraisals:
                app.write({'active': False})
            rec.write({
                'state':'cancel'
            })
    
    def button_undo_cancel(self):
        for rec in self:
            related_appraisals = self.env['pms.appraisee'].search([
                ('pms_department_id', '=', rec.id),('active', '=', False)
                ])
            for app in related_appraisals:
                app.write({'active': True, 'state': 'goal_setting_draft' if self.type_of_pms in ['gs', 'hyr'] else 'draft',
})
            rec.write({
                'state':'published'
            })

    def button_set_to_draft(self):
        self.write({
                'state':'draft'
            })
        
    def action_mass_publish(self): 
        rec_ids = self.env.context.get('active_ids', []) 
        for rec in rec_ids:
            record = self.env['pms.department'].browse([rec])
            record.button_publish()

    def button_mass_cancel(self):
        rec_ids = self.env.context.get('active_ids', []) 
        for rec in rec_ids:
            record = self.env['pms.department'].browse([rec])
            record.button_cancel()
            record.button_set_to_draft()