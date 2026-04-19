from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, RedirectWarning
from datetime import datetime
# from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.parser import parse
import re
from odoo.addons.phone_validation.tools import phone_validation


class OehealthMedicalHistory(models.Model):
    _name = "oeh.medical.history"
    _description = "oeh.medical.history"
    
    patient_id = fields.Many2one('oeh.medical.patient', string="Patient")
    # Surgery
    type_of_surgery = fields.Text('Surgery Type')
    hospital = fields.Char('Hospital')
    outcome_of_surgery = fields.Text('Outcome of Surgery')
    date_of_surgery = fields.Date('Date of Surgery')
    migrated_medical_history_to_emr = fields.Boolean(
        string='Migrated Surgical history to EMR', copy=False)
    migrated_medical_history_to_emr = fields.Boolean(
        string='Migrated Medical history to EMR', copy=False)
    
    # Obstetrics
    pregnancy_date = fields.Date('Pregnancy Date')
    mode_of_delivery = fields.Selection([
        ('svd', 'SVD'),
        ('vaccum_delivery', 'Vaccum Delivery'),
        ('EMCS', 'EMCS'),
        ('ELCS', 'ELCS'),
    ],
        'Mode of delivery')
    child_sex = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ],
        'Child Sex')
    deseased = fields.Selection([
        ('dead', 'Dead'),
        ('alive', 'Alive'),
    ],
        'Deseased')

    birth_date = fields.Date('Birth Date')
    pregnancy_induce_complications = fields.Text(
        'Complications', help='Pregnancy Induced Complications')
    delivery_weeks = fields.Integer(string='Weeks at delivery', default=1)

    previous_miscarriages = fields.Selection([
        ('yes', 'yes'),
        ('no', 'No'),
    ],
        'Any previous miscarriages or voluntary terminations')
    gestational_age = fields.Integer(string='Gestational age', default=0)
    has_miscarriage = fields.Selection([
        ('Voluntary', 'Voluntary'),
        ('Involuntary', 'Involuntary'),
    ],
        'Miscarriage')

    mode_of_termination = fields.Selection([
        ('Medication ', 'Medication'),
        ('manual_vacumm', 'Manual Vacuum Aspiration'),
        ('dilatation', 'Dilatation and Curettage'),
    ],
        'Mode of Termination')

    location_of_miscarriage = fields.Selection([
        ('Health Centre', 'Health Centre'),
        ('Hospital', 'Hospital'),
        ('Other', 'Other'),
    ],
        'Location of Miscarriage')

    specify_other_miscarriage_location = fields.Text('Specify Location')
    is_post_abortal = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ],
        'Post abortal sequelae')
    specify_other_post_abortal = fields.Text(
        'Specify other Post abortal sequelae')

    # Use to determine the type of system to be used in tab display
    system_type = fields.Selection([
        ('obstetrics', 'Obstetrics'),
        ('surgical', 'Surgical'),
    ], 'System type')


class OeHealthPatientExtension(models.Model):
    _name = 'oeh.medical.patient'
    _description = 'Patient Management'
    _inherit = ['oeh.medical.patient', 'mail.thread', 'mail.activity.mixin']

    UPDATE_SRC = [
        ("odoo", "Odoo"),
        ("aether", "Aether")
    ]
    vaccination_status = fields.Selection(
        [
            ('Unvaccinated', 'Unvaccinated'),
            ('Fully Vaccinated', 'Fully Vaccinated'),
            ('Partially Vaccinated', 'Partially Vaccinated'),
        ],
        default='',
    )
    state = fields.Selection(
        [
            ('outpatient', 'OutPatient'),
            ('inpatient', 'InPatient'),
        ],
        default='outpatient',
    )
    plan_id = fields.Many2one(
        'sale.subscription.plan', string="Subscription Plan", compute="_compute_active_subscription")
    # Gynaecology
    patient_id = fields.Many2one('oeh.medical.patient')
    gynaecology_last_menses = fields.Date(string="Last menses")
    gynaecology_amenorrhea = fields.Selection([
        ('primary', 'primary'),
        ('secondary', 'secondary')],
        'Gynaecology: Amenorrhea')
    gynaecology_dysmenorrhea = fields.Boolean(
        string="Gynaecology: Dysmenorrhea")
    gynaecology_menorrhagia = fields.Boolean(string="Gynaecology: Menorrhagia")
    gynaecology_metromenorrhagia = fields.Boolean(string="Metromenorrhagia")
    gynaecology_infertility = fields.Selection([
        ('primary', 'primary'),
        ('secondary', 'secondary')],
        'Infertility')
    gynaecology_subfertility = fields.Boolean(string="Subfertility")
    family_history_condition = fields.Text(string="Condition")
    obstetrics_history_ids = fields.One2many(
        'oeh.medical.history', 'patient_id', string="Obstetrics History", store=True)
    surgical_history_ids = fields.One2many(
        'oeh.medical.history', 'patient_id', string="Surgical History", store=True)
    blood_diaries_count = fields.Integer(
        compute="_compute_blood_diaries_count", string="Diaries")
    # Past medical history
    past_medical_history_sickle_cell = fields.Boolean(string="Sickle cell")
    past_medical_history_diabetes = fields.Boolean(string="Diabetes")
    past_medical_history_hypertension = fields.Boolean(string="Hypertension")
    past_medical_history_epilepsy = fields.Boolean(string="Epilepsy")
    past_medical_history_dyslipidemia = fields.Boolean(string="Dyslipidemia")
    past_medical_history_tia = fields.Boolean(string="TIA")
    past_medical_history_stroke = fields.Boolean(string="Stroke")
    past_medical_history_myocardial_infarction = fields.Boolean(
        string="Myocardial Infarction")
    past_medical_history_dvt = fields.Boolean(string="DVT")
    past_medical_history_surgeries = fields.Text(string="Surgeries")
    past_medical_history_asthma = fields.Boolean(string="Asthma")
    other_medical_history = fields.Text(string="Other Medical History")
    past_medical_history_copd = fields.Boolean(string="COPD")
    past_medical_history_immunization = fields.Selection([('fully', 'fully'), ('not up-to-date', 'not up-to-date'),
                                                          ('unimmunized', 'unimmunized')], 'Immunization')
    past_medical_history_developmental_milestones = fields.Selection([('normal', 'normal'), ('delayed', 'delayed')],
                                                                     'Developmental milestones')

    blood_pressure_diary_ids = fields.One2many('oeh.medical.blood.pressure.diary', 'patient_id',
                                               string="Blood pressure Diary")
    # firebase sync
    data_sync_hash = fields.Char(help='Technical Field used to trigger data sync when patient medical record is updated.'
                                 'This has value will be update anytime eval, labtest, prescriptioin is created or updated ')

    # inherited fields
    phone = fields.Char(string="Primary Phone Number")
    mobile = fields.Char(string="Mobile")
    secondary_email = fields.Char(string="Secondary Email")

    # additional fields
    next_of_kin = fields.Char(string="Next of kin")
    next_of_kin_contact = fields.Char(string="Next of kin contact number")
    children = fields.Many2many(
        'res.partner', string="Children", domain="[('is_patient', '=', True)]",)
    # added as part of COVID-19 requirements
    lga = fields.Char(string="LGA")
    ward = fields.Char(string="LGA Ward")
    passport_no = fields.Char(
        'Passport Number', help='International passport no for customers buying online covid-19 test for travel')
    passport_issuing_country = fields.Char('Issuing Country')
    is_inbound_tester = fields.Boolean(string="Inbound Tester", default=False)

    is_outbound_tester = fields.Boolean(
        string="Outbound Tester", default=False)
    epid_number = fields.Char(
        'EPID Number', help='NCDC number for covid 19 Patients')

    YES_NO = [('Yes', 'Yes'), ('No', 'No')]

    evaluation_count = fields.Integer(
        compute="_evaluation_count", string="Evaluations")
    program_ids = fields.Many2many(
        'oeha.medical.program', string="Associated Programs")
    patient_age_year = fields.Integer(string="Age (Year)", default=0)
    last_evaluation_id = fields.Many2one(
        'oeh.medical.evaluation', string='Last Evaluation ID', compute="_get_last_evaluation_id")
    medication_allergies_ids = fields.One2many('oeha.evaluation.medication.allergies',
                                               related='last_evaluation_id.medication_allergies_ids')
    currentmedications = fields.One2many(
        'oeha.currentmedication', related='last_evaluation_id.currentmedications')
    other_medications = fields.Text(
        string="Other medications", related='last_evaluation_id.other_medications')

    national_identity_number = fields.Char(
        'National Identity Number', help="The Nigerian national assigned number for the person")
    count_male = fields.Integer(
        'Males count')
    count_female = fields.Integer(
        'Females count')
    evaluation_count = fields.Integer(
        'Evaluation Count', compute="get_patient_evaluation", store=True)
    age_int = fields.Integer(compute="patient_age_int",
                             store=True, string='Age', readonly=False)
    age_range = fields.Char('Age Range', store=True, compute="patient_age_int")
    company_id = fields.Many2one('res.company', 'Company', default=(
        lambda self: self.env.user.company_id.id))
    flag = fields.Boolean('Flag')

    # Healthmate Fields
    healthmate_is_registered_user = fields.Boolean(string="Is App User?")
    healthmate_registration_date = fields.Datetime("Registration Date")
    update_source = fields.Selection(UPDATE_SRC, default="odoo", index=True)
    is_synced_to_firebase = fields.Boolean(
        'Is synced to FB?', help="Flag that indicates if a patient record has synced to Firebase")
    patient_tag_ids = fields.Many2many(string='Tags', comodel_name='res.partner.category', related = "partner_id.category_id")


# --------------------------------------------
# Compute Methods
# --------------------TODOMIGRATION: UNCOMMENT METHOD IF eha_membership_ is installed------------------------
    # @api.onchange("partner_id")
    # def _get_patient_tags(self):
    #     partner = self.env['eha.membership.beneficiaries'].sudo().search([('partner_id', '=', self.partner_id.id)])
    #     for rec in partner:
    #         self.patient_tag_ids.ids = rec.category_id.ids

    @api.depends('evaluation_ids')
    def get_patient_evaluation(self):
        for rec in self:
            if rec:
                evaluation = self.env['oeh.medical.evaluation'].search_count(
                    [('patient', '=', rec.id)])
                rec.evaluation_count = int(evaluation)

    @api.depends('dob')
    def patient_age_int(self):
        for rec in self:
            if rec.dob:
                now = datetime.now()
                dob = datetime.strptime(
                    rec.dob.strftime('%Y-%m-%d'), '%Y-%m-%d')
                delta = now - dob
                years_months_days = delta.days // 365
                age_value = int(years_months_days)
                rec.age_int = years_months_days

                if age_value in range(0, 4):
                    rec.update({'age_range': '0 - 3 years'})

                elif age_value in range(3, 6):
                    rec.update({'age_range': '3 - 5 years'})

                elif age_value in range(6, 16):
                    rec.update({'age_range': '6 - 15 years'})

                elif age_value in range(16, 26):
                    rec.update({'age_range': '16 - 25 years'})

                elif age_value in range(22, 36):
                    rec.update({'age_range': '22 - 35 years'})

                elif age_value in range(35, 56):
                    rec.update({'age_range': '35 - 55 years'})

                elif age_value in range(55, 300):
                    rec.update({'age_range': '55 and Above years'})


# --------------------------------------------
# Onchange methods and Constraints
# --------------------------------------------


    @api.constrains('dob', 'phone')
    def constrain_validator(self):
        for patient in self:
            if patient.dob:
                dob = datetime.strptime(
                    patient.dob.strftime("%Y-%m-%d"), '%Y-%m-%d')
                if dob > datetime.now():
                    raise UserError("Date of birth cannot be in the future")

    @api.onchange('phone', 'mobile')
    def _onchange_phone(self):
        if self.country_id:
            country_code = self.country_id.code or ''
            if self.phone and country_code:
                formatted_phone = phone_validation.phone_format(
                    self.phone, country_code, country_phone_code=None)
                patient = self.env['oeh.medical.patient'].search(
                    [('phone', '=ilike', formatted_phone)], limit=1)
                if patient:
                    raise ValidationError('A Patient with same phone number already exists\n \
                            Kindly use the secondary phone number')
                self.phone = formatted_phone
            if self.mobile and not self.is_inbound_tester:
                formatted_mobile = phone_validation.phone_format(
                    self.mobile, country_code, country_phone_code=None)
                self.mobile = formatted_mobile

    @api.onchange('country_id')
    def _onchange_country(self):
        if self.country_id:
            self.phone = False
            self.mobile = False

    @api.onchange('dob')
    def _onchange_dob(self):
        now = datetime.now()
        if self.dob:
            dob = datetime.strptime(self.dob.strftime('%Y-%m-%d'), '%Y-%m-%d')
            diff = now - dob
            self.patient_age_year = int(diff.days // 365)
        else:
            self.patient_age_year = 0

    @api.onchange('phone')
    def _validate_phone(self):
        if self.phone:
            for rec in self:
                partner = self.env['res.partner'].search(
                    [('phone', '=', rec.phone)], limit=1)
                if partner:
                    text = "A customer [%s] with phone no [%s] already exists. \n \
                    Please go to the contact module -> search contact by phone and convert the customer to a patient" % (partner.name, rec.phone)
                    action = self.env.ref('contacts.action_contacts')
                    raise RedirectWarning(
                        text, action.id, _("Go to contact module"))

    @api.onchange('email')
    def _onchange_email(self):
        if self.email:
            for rec in self:
                email = self.env['oeh.medical.patient'].search(
                    [('email', '=', rec.email)], limit=1)
                if email:
                    raise ValidationError("Patient with same email already exists \n \
                    Kindly provide a secondary email")


# --------------------------------------------
# ORM methods Override
# --------------------------------------------


    @api.model
    def create(self, vals):
        # override the create model to check if a user is a CHN nurse
        user = self.env['res.users'].browse(self.env.uid)

        if user.has_group('oehealth_extension.group_oeh_medical_chp_nurse'):
            vals['program_ids'] = [[6, 0, [p.id for p in user.program_ids]]]

        health_patient = super(OeHealthPatientExtension, self).create(vals)
        self.clear_caches()
        return health_patient

    def write(self, vals):
        if not vals.get('is_synced_to_firebase'):
            vals['is_synced_to_firebase'] = False
        return super(OeHealthPatientExtension, self).write(vals)

    def name_get(self):
        res = []
        for record in self.with_context(prefetch_fields=False):
            record_name = record.name
            record_identification = record.identification_code
            record_name = _('%(name)s (%(extra)s)') % {
                'name': record_name,
                'extra': record_identification,
            }
            res.append((record.id, record_name))
        return res


# --------------------------------------------
# Action method and business rules
# --------------------------------------------


    def _evaluation_count(self):
        # counts all evaluations belonging to patient
        oe_evaluation = self.env['oeh.medical.evaluation']
        for adm in self:
            domain = [('patient', '=', adm.id)]
            evaluation_ids = oe_evaluation.search(domain)
            evaluations = oe_evaluation.browse(evaluation_ids)
            evaluations_count = 0
            for ad in evaluations:
                evaluations_count += 1
            adm.evaluation_count = evaluations_count
        return True

    def _compute_blood_diaries_count(self):
        for rec in self:
            blood_diary = self.env['oeh.medical.blood.pressure.diary'].search_count(
                [('patient_id', '=', rec.id)])
            rec.blood_diaries_count = int(blood_diary)

    def phone_formatter(self, country_id, phone):
        country_ref = self.env['res.country'].browse([country_id])
        country_code = country_ref.code if country_ref else ''
        formatted_phone = phone_validation.phone_format(
            phone, country_code, country_phone_code=None)
        return formatted_phone

    def record_evaluation_covid(self):
        views = self.env.ref("oehealth.oeh_medical_evaluation_view").id
        triage = self.env.ref(
            "oehealth_extension.oeha_template_convid_triage").id

        return {
            "name": "Patient's Evaluation",
            "type": "ir.actions.act_window",
            "res_model": "oeh.medical.evaluation",
            "view_type": "form",
            "view_form": "form",
            "views": [(views, 'form')],
            "target": "curent",
            "context": {"default_chief_complaint": "COVID-19 concerns",
                        "default_evaluation_type": "New Complaint",
                        "default_template_id": triage,
                        "default_is_convid": True,
                        },
        }

    def action_view_blood_pressure_diaries(self):
        tree_view_id = self.env.ref(
            "oehealth_extension.view_oeh_medical_blood_pressure_diary_tree").id
        graph_view_id = self.env.ref(
            "oehealth_extension.view_oeh_medical_blood_pressure_diary_graph").id
        return {
            "name": "Patient's Blood Diaries",
            "type": "ir.actions.act_window",
            "res_model": "oeh.medical.blood.pressure.diary",
            "view_type": "form",
            "view_form": "tree",
            "view_mode": "tree,graph",
            "views": [(tree_view_id, 'tree'), (graph_view_id, 'graph')],
            "target": "curent",
            "context": {"default_patient_id": self.id,
                        },
            "domain": [('id', 'in', self.blood_pressure_diary_ids.ids)],

        }

    def _get_last_evaluation_id(self):
        for patient in self:
            if patient.evaluation_ids:
                last_evaluation = patient.evaluation_ids.sorted('id')[-1]
                patient.last_evaluation_id = last_evaluation.id
            else:
                patient.last_evaluation_id = False

    @api.model
    def find_patient_by_phone_dob(self, phone, dob):
        """Search patient by phone and DOB. 

        Args:
            phone (str): Patient Phone  in international Format eg. +2348035279356
            dob (str): Patient dob in format Y-m-d eg. 2015-31-12

        Returns:
            [dict]: Dictionary contaning patient details
        """
        patient = self.env['oeh.medical.patient']
        patients = self._get_patients_by_phone_and_dob(phone, dob)
        patient = patients and patients[0] or patient
        return patient

    @api.model
    def _get_patients_by_phone_and_dob(self, phone, dob):
        """Search patient by phone and DOB. 

        Args:
            phone (str): Patient Phone  in international Format eg. +2348035279356
            dob (str): Patient dob in format Y-m-d eg. 2015-31-12

        Returns:
            [dict]: Dictionary contaning patient details
        """

        Patient = self.env['oeh.medical.patient']
        phone = re.sub(" ", "", phone)
        QUERY = "SELECT id, REPLACE(phone, ' ', '') phone, REPLACE(mobile, ' ', '') mobile FROM oeh_medical_patient "\
                "WHERE( REPLACE(mobile, ' ', '')='%s' OR REPLACE(phone, ' ', '')='%s') AND dob='%s' AND active = True ORDER BY create_date" % (
                    phone, phone, dob)
        self.env.cr.execute(QUERY)
        list_of_patients_dict = self.env.cr.dictfetchall()
        list_of_patient_ids = list(
            map(lambda x: x['id'], list_of_patients_dict))
        patients = Patient.browse(list_of_patient_ids)
        return patients
    
    def flag_patient(self): 
        return self.env['res.partner'].popup_notification(
            self.id, 
            "Flag", 
            "flagged", 
            "oeh.medical.patient")
        
    def unflag_patient(self):
        return self.env['res.partner'].popup_notification(
            self.id, 
            "UnFlag",
            "unflagged", 
            "oeh.medical.patient"
            )

    def return_post_action(self, reason, action):
        """methods that gets returned after the post from reason dialog"""
        if action in ['flagged']:
            self.flag = True
             
        elif action in ['unflagged']:
            self.flag = False
        context = {
            'reason': reason,
            'flag_type': action 
        }
        # using the same template bcos of future case where different template will
        # be used
        ir_model_data = self.env['ir.model.data']
        template_id = ir_model_data.get_object_reference(
            'eha_base_extension', 'misconduct_patient_mail_template')[1]         
        self.send_notification_email(template_id, context)

    def send_notification_email(self, with_template_id, context=False):
        if with_template_id:
            ctx = dict()
            ctx.update({
                    'default_model': 'oeh.medical.patient',
                    'default_res_id': self.id,
                    'default_use_template': bool(with_template_id),
                    'default_template_id': with_template_id,
                    'default_composition_mode': 'comment',
                })
            if context:
                ctx['flag_reason'] = context.get('reason', '')
                ctx['flag_type'] = context.get('flag_type', '')
            template_record = self.env['mail.template'].browse(with_template_id)
            template_record.with_context(ctx).send_mail(self.id, True)