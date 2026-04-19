# models/res_partner.py
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_number = fields.Integer(string='Number')

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    pharmacy_history_ids = fields.One2many('res.patient.pharmacy.history', 'patient_id', string='Pharmacy History')
    patient_no = fields.Char(string='Patient No', readonly=True,)
    gender = fields.Selection([('Male', 'Male'),('Female', 'Female'),('Other', 'Other')], string='Gender')
    # date_of_registration = fields.Char(string='Registration Date')
    first_name = fields.Char(string='First Name', required= True)
    middle_name = fields.Char(string='Middle Name',required= True)
    last_name = fields.Char(string='Last Name',required= True)
    date_of_registration = fields.Datetime(string='Registration Date',default= fields.Datetime.now,required= True)
    dob = fields.Date(string='Date of Birth')
    age = fields.Char(string='Age', compute="compute_dob", store=False)
    
    next_of_kin_ids = fields.One2many(
        'res.partner',
        'parent_id',      # child contacts point to patient
        string='Next of Kin',
        domain=[('type', '=', 'other')]  # only show "other" type contacts
    )
    relationship = fields.Selection([
        ('father','Father'),
        ('mother','Mother'),
        ('spouse','Spouse'),
        ('guardian','Guardian'),
        ('other','Other')
    ], string='Relationship')
    name = fields.Char(
          compute='_compute_full_name', store=True,readonly=False)
    # company_id = fields.Many2one('res.company', string='Company', )
    
    # company = fields.Many2one('res.company', string='Company')
    

    
    is_patient = fields.Boolean(string='Is Patient')
    is_staff = fields.Boolean(string='Is Staff', store=False)
    # required if is_staff
    related_employee_number = fields.Char(string='Employee No', store=True)

    # staff_id=fields.Char(string='Staff Number(Staff Only)')

    blood_group = fields.Selection(
        selection=[
            ('a_pos', 'A+'),
            ('a_neg', 'A-'),
            ('b_pos', 'B+'),
            ('b_neg', 'B-'),
            ('ab_pos', 'AB+'),
            ('ab_neg', 'AB-'),
            ('o_pos', 'O+'),
            ('o_neg', 'O-'),
        ],
        string="Blood Group",
        required=False,
        help="Select the blood group of the person",
    )
    genotype = fields.Selection(
        selection=[
            ('aa', 'AA'),
            ('as', 'AS'),
            ('ss', 'SS'),
            ('ac', 'AC'),
            ('sc', 'SC'),
        ],
        string="Genotype",
        required=False,
        help="Select the genotype of the person",
    )

    prescription_count = fields.Integer(compute='_compute_prescription_count')
    # last_visit_date = fields.Datetime(compute='_compute_last_visit_date', store=True)
    last_visit_date = fields.Datetime(string='Last Visit Date', default=fields.Datetime.now)
    allergy_ids = fields.Many2many('pharmacy.allergy', string='Allergies')
    chronic_condition_ids = fields.Many2many('pharmacy.chronic.condition', string='Chronic Conditions')
    patient_history_ids = fields.One2many('patient.medical.history', 'patient_id', string='Medical History')
    patient_evaluation_ids = fields.One2many('patient.medical.evaluation', 'patient_id', string='Medical Evaluation')
    patient_prescription_ids = fields.One2many('res.patient.pharmacy.history', 'patient_id', string='Phrm Prescription')
    patient_evaluation_count=fields.Integer(
         compute='_compute_total_evaluations_count'
    )
    patient_prescription_count=fields.Integer(
         compute='_compute_total_prescription_count'
    )
    
    @api.onchange('related_employee_number')
    def onchange_related_employee_number(self):
        for user in self:
            employee = self.env['hr.employee'].search(
                [('employee_number', '=', user.related_employee_number)],
                limit=1
            )
            if not employee:
                raise ValidationError(f"System could not find any employee related to {user.related_employee_number}")

    def get_default_name(self, vals):
        return self.env["ir.sequence"].next_by_code("patient.code") or "/"

    @api.model
    def create(self, vals):
        # if vals.get("patient_no", "/") == "/":
        vals["patient_no"] = self.get_default_name(vals)
 
        return super().create(vals)

    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_full_name(self):
        for rec in self:
            parts = [rec.last_name or '', rec.first_name or '', rec.middle_name or '']
            rec.name = ' '.join([p for p in parts if p])
    
    @api.depends('name')
    def get_employee_number(self):
        '''used to relate the contact with existing employee'''
        for rec in self:
            related_employee_id = self.env['hr.employee'].search([('partner_id', '=', rec.id)], limit=1)
            if related_employee_id:
                rec.related_employee_number = related_employee_id.employee_number
            else:
                rec.related_employee_number = False 

    @api.depends('dob')
    def compute_dob(self):
        for rec in self:
            if rec.dob:
                today = fields.Date.today()
                diff = relativedelta(today, rec.dob)
                years = diff.years
                days = diff.days

                rec.age = f"{years} Years {days} Days"
            else:
                rec.age = False

    @api.depends('pharmacy_history_ids')
    def _compute_prescription_count(self):
        for rec in self:
            rec.prescription_count = len(rec.pharmacy_history_ids)
    
    @api.depends('pharmacy_history_ids.date')
    def _compute_last_visit_date(self):
        for rec in self:
            if rec.pharmacy_history_ids:
                rec.last_visit_date = max(rec.pharmacy_history_ids.mapped('date'))
            else:
                rec.last_visit_date = False

    @api.depends('patient_evaluation_ids')
    def _compute_total_evaluations_count(self):
        for patient in self:
            patient.patient_evaluation_count = len(patient.patient_evaluation_ids)

    @api.depends('patient_prescription_ids')
    def _compute_total_prescription_count(self):
        for patient in self:
            patient.patient_prescription_count = len(patient.patient_prescription_ids)

    def action_view_evaluation(self):
        views = self.env.ref("careone_health.view_patient_medical_evaluation_form").id
        return { 
            "name": "Patient's Evaluation",
            "type": "ir.actions.act_window",
            "res_model": "patient.medical.evaluation",
            "view_type": "form",
            "view_form": "form",
            "views": [(views, 'form')],
            "target": "new",
            "context": {
                "default_patient_id": self.id,
                "default_purpose": "doctor_evaluation",
            }
        }
    def action_view_prescription(self):
        views = self.env.ref("careone_health.view_res_patient_pharmacy_history_form").id
        return { 
            "name": "Patient's Prescription",
            "type": "ir.actions.act_window",
            "res_model": "res.patient.pharmacy.history",
            "view_type": "form",
            "view_form": "form",
            "views": [(views, 'form')],
            "target": "new",
            "context": {
                "default_patient_id": self.id,
                "default_purpose": "doctor_evaluation",
            }
        }
    
    
    