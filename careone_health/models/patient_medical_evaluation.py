# models/res_patient_pharmacy_history.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


# models/evaluation.py
class PatientMedicalEvaluation(models.Model):
    _name = 'patient.medical.evaluation'
    _description = 'Patient History'
    
    FOLLOW_UP = [
        ('No follow up needed', 'No follow up needed'),
        ('Follow up in 1 day', 'Follow up in 1 day'),
        ('Follow up in 2-3 days', 'Follow up in 2-3 days'),
        ('Follow up in 1 week', 'Follow up in 1 week'),
        ('Follow up in 2 weeks', 'Follow up in 2 weeks'),
        ('Follow up in 1 month', 'Follow up in 1 month'),
        ('Follow up in 3 months', 'Follow up in 3 months'),
        ('Follow up as needed by patient', 'Follow up as needed by patient'),
    ]

    EVALUATION_TYPE = [
        ('New Complaint', 'New Complaint'),
        ('Follow Up', 'Follow Up'),
        ('Check Up', 'Check Up'),
        ('Telemedicine', 'Telemedicine'),
        ('Immunization', 'Immunization'),
        ('Antenatal', 'Antenatal'),
        ('Annual Health Checkup', 'Annual Health Checkup'),
        ('Family Planning', 'Family Planning'),
        ('Obstetrics', 'Obstetrics'),
        ('Gynaecology', 'Gynaecology'),
    ]

    EVALUATION_STATE = [
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    RESPIRATION_TYPE = [
        ('unlabored', 'Unlabored'),
        ('labored', 'Labored')
    ]

    ALLERGIES_SELECTION = [
        ('yes', 'Yes'),
        ('no', 'No')
    ]


    URGENCY_LEVEL = [
                    ('Normal', 'Normal'),
                    ('Urgent', 'Urgent'),
                    ('Medical Emergency', 'Medical Emergency'),
                ]

    PATIENT_STATUS = [
                ('Ambulatory', 'Ambulatory'),
                ('Outpatient', 'Outpatient'),
                ('Inpatient', 'Inpatient'),
                 ("New", "New"),
                ("Existing", "Existing")
            ]

    APPOINTMENT_STATUS = [
            ('Scheduled', 'Scheduled'),
            ('Completed', 'Completed'),
            ('Invoiced', 'Invoiced'),
        ]
    name = fields.Char(string='Evaluation No.', readonly=True)

    severity = fields.Selection([
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ], string='Severity')
    evaluation_type = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], string='Evaluation type')
    description = fields.Text(string='Chief Complaint')
    patient_id = fields.Many2one("res.partner", string="Patient ID")
    branch_id = fields.Many2one("multi.branch", string="Clinic Branch", default = lambda self: self.env.user.branch_id.id)
    prescription_document = fields.Many2one("ir.attachment", string="Prescription Document")
    pharmacy_prescription_line_ids = fields.One2many('res.patient.pharmacy.history', 'patient_evaluation_id', string='Prescriptions')
    age = fields.Char(related="patient_id.age")
    sex =  fields.Selection(related='patient_id.gender')
    evaluation_start_date = fields.Datetime(string='Evaluation Date', default=fields.Datetime.now, required=False, index=True)
    evaluation_end_date = fields.Datetime(string='Evalution End Date')
    chief_complaint = fields.Char(string='Chief Complaint', help='Chief Complaint')
    notes_complaint = fields.Text(string='Complaint details')
    hpi = fields.Text(string='HPI', help='History of present Illness')
    state = fields.Selection([('Draft','Draft'), ('Published', 'In progress'), ('Completed', 'Completed')], default='Draft')
    evaluation_no = fields.Char(string="Evaluation No.", readonly=True, copy=False)
    evaluation_duration = fields.Char(
        string="Duration",
        compute="_compute_duration",
        store=True,
        readonly=True
    )
    recommendation = fields.Text(string="Recommendation")
    disease  = fields.Text(string="Disease ")
    treatment_plan=fields.Text(string="Treatment_ Plan ")
    blood_group = fields.Selection(
        related='patient_id.blood_group',
        string="Blood Group",
        readonly=True,
        store=False  # True if you need to search/filter by it
    )
    genotype = fields.Selection(
        related='patient_id.genotype',
        string="Genotype",
        readonly=True,
        store=False
    )
    # company = fields.Many2one(
    #     'res.company', 
    #     related='patient_id.company', 
    #     string='Company', 
    #     store=True,  # optional but recommended
    #     readonly=True
    # )

    @api.depends('evaluation_start_date', 'evaluation_end_date')
    def _compute_duration(self):
        for record in self:
            if record.evaluation_start_date and record.evaluation_end_date and record.evaluation_end_date >= record.evaluation_start_date:
                delta = record.evaluation_end_date - record.evaluation_start_date
                total_seconds = int(delta.total_seconds())

                total_hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60

                record.evaluation_duration = f"{total_hours} Hours {minutes} Minutes"
            else:
                record.evaluation_duration = "0 Hours 0 Minutes"

    # def get_default_name(self):
    #     return self.env["ir.sequence"].next_by_code("patient.medical.evaluation") or "/"

    # @api.model
    # def create(self, vals):
    #     # if not vals.get("evaluation_no"):  # Only generate if not provided
    #     vals["evaluation_no"] = self.get_default_name()
    #     return super().create(vals)
    
    @api.model
    def create(self, vals):
     if vals.get('evaluation_no', 'New') == 'New':
        vals['evaluation_no'] = self.env['ir.sequence'].next_by_code(
            'patient.medical.evaluation') or 'New'
     return super(PatientMedicalEvaluation, self).create(vals)

    def set_to_progress(self):
        return self.write({'state': 'Published'})
    def set_to_draft(self):
        return self.write({'state': 'Draft'})

    def set_to_completed(self):
        return self.write({'state': 'Completed'})
    
    # def set_to_completed(self):
    #     return self.write({'state': 'Draft'})

    ###### admission workflow ######
    def action_admit(self):
        views = self.env.ref("careone_health.careone_admission_form_view").id
        return {
            "name": "Patient's Admission",
            "type": "ir.actions.act_window",
            "res_model": "patient.medical.admission",
            "view_type": "form",
            "view_form": "form",
            "views": [(views, 'form')],
            "target": "current",
            "context": {
                'default_patient_id': self.patient_id.id,
                'default_admittedby': self.care_provider.id,
                'default_initial_evaluation_id': self.id,
                'default_evaluation_ids': self.ids
            }
        }

    def action_discharge(self):
        '''Discharge a patient.
        Discharging a patient should set the room to dirty.
        '''
        views = self.env.ref("careone_health.careone_admission_form_view").id
        admission = self.env['patient.medical.admission'].search(
            [
                ('patient_id', '=', self.patient_id.id),
                ('state', '=', 'inpatient')
            ], order='id desc', limit=1
        )
        return {
            "name": "Patient's Admission",
            "type": "ir.actions.act_window",
            "res_model": "patient.medical.admission",
            "view_type": "form",
            "view_form": "form",
            "views": [(views, 'form')],
            "target": "current",
            "res_id": admission.id if admission else False,
        }


    @api.depends('patient_id')
    def _compute_admission_state(self):
        for rec in self:
            admission = self.env['patient.medical.admission'].search(
                [
                    ('patient_id', '=', rec.patient_id.id)
                ], order='id desc', limit=1
            )
            rec.admission_state = admission.state if admission else 'draft'
    
    ### EVALUATIONS
    purpose = fields.Selection(
        [
            ('doctor_evaluation', 'Doctor Evaluation'),
            ('nurse_assessment', 'Nurse Assessment'),
        ],
        default=lambda *a: 'doctor_evaluation',
        help='specifies the purpose of the evaluation. This field is only important for the admission workflow.\n'
             '* Nurse assesment: In the admission workflow, an evaluation can be used as a nurse assement.'
             ' A nurse will open a single evaluation for nurse assesment for the duration of the admission.'
             ' This gives her the ability to add multiple vital signs , notes etc'
             '* Doctor Evaluation: In the admission workflow, doctor can add multiple evaluations for a single'
             ' admission. In admission form view tabs, therefore, this fields helps us to seperate nurse assesment evals from'
             ' doctors eval'
    )
    admission_id = fields.Many2one(
        'patient.medical.admission',
        'Admission #',
    )
    admission_state = fields.Char(compute="_compute_admission_state", default='draft')
    

    ###### end admission workflow ######
    hdl = fields.Integer(string='Last HDL', help="Last HDL Cholesterol reading. It can be approximative")
    ldl = fields.Integer(string='Last LDL', help="Last LDL Cholesterol reading. It can be approximative")
    tag = fields.Integer(string='Last TAGs', help="Triacylglycerols (triglicerides) level. It can be approximative")
    systolic = fields.Integer(string='Systolic Pressure')
    diastolic = fields.Integer(string='Diastolic Pressure')
    bpm = fields.Integer(string='Heart Rate', help="Heart rate expressed in beats per minute")
    respiratory_rate = fields.Integer(string='Respiratory Rate', help="Respiratory rate expressed in breaths per minute")
    osat = fields.Integer(string='Oxygen Saturation', help="Oxygen Saturation (arterial).")
    malnutrition = fields.Boolean(string='Malnutrition', help="Check this box if the patient show signs of malnutrition. If not associated to a disease, please encode the correspondent disease on the patient disease history. For example, Moderate protein-energy malnutrition, E44.0 in ICD-10 encoding")
    dehydration = fields.Boolean(string='Dehydration', help="Check this box if the patient show signs of dehydration. If not associated to a disease, please encode the correspondent disease on the patient disease history. For example, Volume Depletion, E86 in ICD-10 encoding")
    temperature = fields.Float(string='Temperature (celsius)')
    weight = fields.Float(string='Weight (kg)')
    height = fields.Float(string='Height (cm)')
    bmi = fields.Float(string='Body Mass Index (BMI)')
    head_circumference = fields.Float(string='Head Circumference', help="Head circumference")
    abdominal_circ = fields.Float(string='Abdominal Circumference')
    edema = fields.Boolean(string='Edema', help="Please also encode the correspondent disease on the patient disease history. For example,  R60.1 in ICD-10 encoding")
    petechiae = fields.Boolean(string='Petechiae')
    hematoma = fields.Boolean(string='Hematomas')
    cyanosis = fields.Boolean(string='Cyanosis', help="If not associated to a disease, please encode it on the patient disease history. For example,  R23.0 in ICD-10 encoding")
    acropachy = fields.Boolean(string='Acropachy', help="Check if the patient shows acropachy / clubbing")
    nystagmus = fields.Boolean(string='Nystagmus', help="If not associated to a disease, please encode it on the patient disease history. For example,  H55 in ICD-10 encoding")
    miosis = fields.Boolean(string='Miosis', help="If not associated to a disease, please encode it on the patient disease history. For example,  H57.0 in ICD-10 encoding" )
    mydriasis = fields.Boolean(string='Mydriasis', help="If not associated to a disease, please encode it on the patient disease history. For example,  H57.0 in ICD-10 encoding")
    # cough = fields.Boolean(string='Cough', help="If not associated to a disease, please encode it on the patient disease history.")
    palpebral_ptosis = fields.Boolean(string='Palpebral Ptosis', help="If not associated to a disease, please encode it on the patient disease history")
    arritmia = fields.Boolean(string='Arritmias', help="If not associated to a disease, please encode it on the patient disease history")
    heart_murmurs = fields.Boolean(string='Heart Murmurs')
    heart_extra_sounds = fields.Boolean(string='Heart Extra Sounds', help="If not associated to a disease, please encode it on the patient disease history")
    jugular_engorgement = fields.Boolean(string='Tremor', help="If not associated to a disease, please encode it on the patient disease history")
    ascites = fields.Boolean(string='Ascites', help="If not associated to a disease, please encode it on the patient disease history")
    lung_adventitious_sounds = fields.Boolean(string='Lung Adventitious sounds', help="Crackles, wheezes, ronchus..")
    bronchophony = fields.Boolean(string='Bronchophony')
    increased_fremitus = fields.Boolean(string='Increased Fremitus')
    decreased_fremitus = fields.Boolean(string='Decreased Fremitus')
    jaundice = fields.Boolean(string='Jaundice', help="If not associated to a disease, please encode it on the patient disease history")
    lynphadenitis = fields.Boolean(string='Linphadenitis', help="If not associated to a disease, please encode it on the patient disease history")
    breast_lump = fields.Boolean(string='Breast Lumps')
    breast_asymmetry = fields.Boolean(string='Breast Asymmetry')
    nipple_inversion = fields.Boolean(string='Nipple Inversion')
    nipple_discharge = fields.Boolean(string='Nipple Discharge')
    peau_dorange = fields.Boolean(string='Peau d orange',help="Check if the patient has prominent pores in the skin of the breast" )
    gynecomastia = fields.Boolean(string='Gynecomastia')
    masses = fields.Boolean(string='Masses', help="Check when there are findings of masses / tumors / lumps")
    hypotonia = fields.Boolean(string='Hypotonia', help="Please also encode the correspondent disease on the patient disease history.")
    hypertonia = fields.Boolean(string='Hypertonia', help="Please also encode the correspondent disease on the patient disease history.")
    pressure_ulcers = fields.Boolean(string='Pressure Ulcers', help="Check when Decubitus / Pressure ulcers are present")
    goiter = fields.Boolean(string='Goiter')
    alopecia = fields.Boolean(string='Alopecia', help="Check when alopecia - including androgenic - is present")
    xerosis = fields.Boolean(string='Xerosis')
    erithema = fields.Boolean(string='Erithema', help="Please also encode the correspondent disease on the patient disease history.")
    loc = fields.Integer(string='Level of Consciousness', help="Level of Consciousness - on Glasgow Coma Scale :  1=coma - 15=normal")
    loc_eyes = fields.Integer(string='Level of Consciousness - Eyes', help="Eyes Response - Glasgow Coma Scale - 1 to 4", default=lambda *a: 4)
    loc_verbal = fields.Integer(string='Level of Consciousness - Verbal', help="Verbal Response - Glasgow Coma Scale - 1 to 5", default=lambda *a: 5)
    loc_motor = fields.Integer(string='Level of Consciousness - Motor', help="Motor Response - Glasgow Coma Scale - 1 to 6", default=lambda *a: 6)
    violent = fields.Boolean(string='Violent Behaviour', help="Check this box if the patient is agressive or violent at the moment")
    # mood = fields.Selection(MOOD, string='Mood', index=True)
    # indication = fields.Many2one('oeh.medical.pathology', string='Indication', help="Choose a disease for this medicament from the disease list. It can be an existing disease of the patient or a prophylactic.")
    indication = fields.Char(string='Indication', help="Choose a disease for this medicament from the disease list. It can be an existing disease of the patient or a prophylactic.")
    orientation = fields.Boolean(string='Orientation', help="Check this box if the patient is disoriented in time and/or space")
    memory = fields.Boolean(string='Memory', help="Check this box if the patient has problems in short or long term memory")
    knowledge_current_events = fields.Boolean(string='Knowledge of Current Events', help="Check this box if the patient can not respond to public notorious events")
    judgment = fields.Boolean(string='Jugdment', help="Check this box if the patient can not interpret basic scenario solutions")
    abstraction = fields.Boolean(string='Abstraction', help="Check this box if the patient presents abnormalities in abstract reasoning")
    vocabulary = fields.Boolean(string='Vocabulary', help="Check this box if the patient lacks basic intelectual capacity, when she/he can not describe elementary objects")
    calculation_ability = fields.Boolean(string='Calculation Ability',help="Check this box if the patient can not do simple arithmetic problems")
    object_recognition = fields.Boolean(string='Object Recognition', help="Check this box if the patient suffers from any sort of gnosia disorders, such as agnosia, prosopagnosia ...")
    praxis = fields.Boolean(string='Praxis', help="Check this box if the patient is unable to make voluntary movements")
    info_diagnosis = fields.Text(string='Presumptive Diagnosis')
    directions = fields.Text(string='Plan')
    # Family history
    family_history_condition = fields.Text(string="Family History Condition")

    patient_status = fields.Selection(PATIENT_STATUS, string="Patient Status")
    # dietary fields
    dietary_history = fields.Text(string="Dietary History")
    social_history = fields.Text(string="Social History")
    notes = fields.Text(string="Notes")
    # Nutrition
    diet = fields.Selection([('regular', 'Regular'), ('soft', 'Soft'), ('pureed', 'Pureed')], 'Nurse Assessment: Diet')
    recent_weight_change = fields.Boolean(string="Nurse Assessment: Recent weight Change")
    conditions_affecting_ecs = fields.Boolean(
        string="Nurse Assessment: Condition affecting eating, chewing and swallowing")
    mucous_membranes = fields.Selection([('moist', 'Moist'), ('dry', 'Dry')], 'Nurse Assessment: Mucous Membranes')

    # skin
    skin = fields.Selection([('normal', 'Normal'), ('pale', 'Pale'), ('red', 'Red'),
                             ('rash', 'Rash'), ('bruise', 'Bruise'), ('breakdown', 'Skinbreakdown')],
                            'Nurse Assessment: Skin')
    skin_intact = fields.Boolean(string="Nurse Assessment: Skin intact")
    special_care = fields.Boolean(string="Nurse Assessment: Special care required")
    wound_assessment = fields.Text(string='Nurse Assessment: Wound Assessment', required=False)

    # neuro
    level_of_consciousness = fields.Selection([('alert', 'Alert'), ('altered', 'Altered')],
                                              'Nurse Assessment: Level of consciousness')
    seizure_tremor_fainting = fields.Boolean(string="seizure/ tremor/fainting")
    difficulty_in_orientation = fields.Boolean(string="Nurse Assessment: Difficulty in orientation")
    sensation = fields.Selection([('intact', 'Intact'), ('diminished', 'Diminished'), ('absent', 'Absent')],
                                 'Intact/Diminished / Absent')
    memory_deficit = fields.Boolean(string="Nurse Assessment: Memory Deficit")
    impaired_decision_making = fields.Boolean(string="Nurse Assessment: Impaired decision making")
    sleep_aids = fields.Boolean(string="Nurse Assessment: Sleep aids")

    # pain / discomfort
    pain = fields.Boolean(string="Nurse Assessment: Discomfort/Pain")
    pain_score = fields.Selection([
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10')
    ], 'Nurse Assessment: Pain Score')
    location = fields.Char(string='Nurse Assessment: Pain/Discomfort Location')
    frequency = fields.Char(string='Nurse Assessment: Pain/Discomfort Frequency')
    duration = fields.Char(string='Nurse Assessment: Pain/Discomfort Duration')
    treatment = fields.Char(string='Nurse Assessment: Treatment (if any)')

    # respiration
    respirations = fields.Selection(RESPIRATION_TYPE, 'Nurse Assessment: Respirations')
    breath_sounds = fields.Selection([('clear', 'Clear'), ('wheezes', 'Wheezes'), ('crackles', 'Crackles')],
                                     'Nurse Assessment: Breath sounds')
    shorthess_of_breath = fields.Boolean(string="Nurse Assessment: Shortness of breath")
    shorthess_of_breath_trigger = fields.Text('Trigger: shorthess of breath')
    cough = fields.Boolean(string="Cough")
    cough_type = fields.Selection([('productive', 'Productive'), ('non_productive', 'Non Productive')],
                                  'Nurse Assessment: Productive / Non Productive')
    respiratory_treatment = fields.Selection([('none', 'None'), ('oxygen', 'Oxygen'),
                                              ('nebulizer', 'Nebulizer'), ('cpap', 'CPAP'), ('bipap', 'BIPAP')],
                                             'Respiratory Treatments')

    # cardiovascular / circulation
    history = fields.Selection([('normal', 'Normal'), ('arrythmia', 'Arrythmia'),
                                ('hypertension', 'Hypotension'), ('dizziness', 'Dizziness')],
                               'Nurse Assessment: History')
    pulse = fields.Selection([('regular', 'Regular'), ('irregular', 'Irregular')], 'Nurse Assessment: Pulse')
    explain_edema = fields.Text('Nurse Assessment: Explain edema if any')
    chest_pain = fields.Boolean(string="Nurse Assessment: Chest pain")
    explain_chest_pain = fields.Text('Nurse Assessment: Explain chest pain if any')

    # gastro intestinal
    gastrointestinal_bleeding = fields.Boolean(string="Nurse Assessment: Bleeding")
    gastrointestinal_diarrhea = fields.Boolean(string="Nurse Assessment: Gastro: Diarrhea")
    gastrointestinal_constipation = fields.Boolean(string="Nurse Assessment: Gastro: Constipation")
    gastrointestinal_vomiting = fields.Boolean(string="Nurse Assessment: Gastro: Vomiting")
    gastrointestinal_nausea = fields.Boolean(string="Nurse Assessment: Gastro: Nausea")
    gastrointestinal_gastrostomy = fields.Boolean(string="Nurse Assessment: Gastrostomy")
    gastrointestinal_enteral_tube = fields.Boolean(string="Nurse Assessment: Enteral tube")
    gastrointestinal_abdominal_pain = fields.Boolean(string="Nurse Assessment: Gastro: Abdominal Pain")

    change_in_appetite = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Nurse Assessment: Change in appetite')
    explain_change_in_appetite = fields.Text('Explain change in appetite')
    bowel_sounds = fields.Boolean(string="Gastro: Bowel sounds")
    bowel_movement = fields.Boolean(string="Bowel movement")

    # genitourinary
    bladder_control = fields.Selection([('full_control', 'Full Control'),
                                        ('incontinence', 'Incontinence')], 'Nurse Assessment: Bladder Control')
    bladder_frequency = fields.Char(string='Nurse Assessment: Frequency')
    blood_in_urine = fields.Boolean(string="Nurse Assessment: Blood in urine")
    difficulty_urinating = fields.Boolean(string="Nurse Assessment: Difficulty urinating")
    nocturnia = fields.Boolean(string="Nurse Assessment: Nocturnia")
    indwelling_catheter = fields.Boolean(string="Nurse Assessment: Indwelling catheter")

    # musculoskeletal
    mobility = fields.Selection([('normal', 'Normal'), ('impaired', 'Impaired')], 'Nurse Assessment: Mobility')
    assistive_devices = fields.Selection(
        [('walking_stick', 'Walking Stick'), ('wheelchair', 'Wheel Chair'), ('stretcher', 'Stretcher')],
        string="Assistive Devices")
    # assistive_devices = fields.Boolean(string="Assistive devices")
    range_of_motion = fields.Selection([('full', 'Full'), ('limited', 'Limited')], 'Range of motion')
    activities_of_daily = fields.Selection([('self', 'Self'), ('assist', 'Assit'),
                                            ('total', 'Total')], 'Activities of daily living')
    # sensory 
    vision = fields.Selection([('normal', 'Normal'), ('impaired', 'Impaired')], 'Nurse Assessment: Vision')
    corrective_device = fields.Char('Corrective device')
    hearing = fields.Selection([('normal', 'Normal'), ('impaired', 'Impaired')], 'Nurse Assessment: Hearing')
    hearing_aid = fields.Boolean(string="Nurse Assessment: Hearing Aid")

    # nursing assessment notes
    nursing_assessment_notes = fields.Text(string="Nurse Assesment: Notes")
    ####################################################################
    # current medications
    allergies = fields.Boolean('Allergies')
    allergies_selection = fields.Selection(ALLERGIES_SELECTION, 'Allergies to medicines')
    allergy_cause = fields.Text(string="Cause of Allergy")
    allergic_reaction_seen = fields.Text(string="Allergic reaction seen")
    current_medication = fields.Selection(ALLERGIES_SELECTION, 'Any current medications?', default='no')
    # currentmedications = fields.One2many('oeha.currentmedication', 'evaluation_id', string="Current Medications")
    other_medications = fields.Text(string="Other medications")
    other_allergies = fields.Selection(ALLERGIES_SELECTION, 'Other Allergies ')

    #######################################################################
    # Treatment sheet
    # treatments_administered = fields.One2many('oeha.treatmentmedication', 'evaluation_id',
    #                                           string="Medications Administered")
    # procedures_performed = fields.One2many('oeha.treatmentprocedure', 'evaluation_id',
    #                                        string="Treatments / Procedures Performed")
    # iv_procedures_performed = fields.One2many('oeha.ivprocedure', 'evaluation_id', string="IV Procedures Performed")
    # Discharge summary
    discharge_patient_name = fields.Char(string="Patient Name", related='patient_id.name')
    discharge_patient_id = fields.Char(string="Discharge Patient NO", related='patient_id.patient_no')
    patient_admission_date = fields.Datetime(string="Patient Evaluation Date", related='evaluation_start_date')
    patient_discharge_date = fields.Date('Discharge Date')
    care_provider = fields.Many2one('res.users', 'Care provider', default=lambda self: self.env.user)
    discharge_attending_physician = fields.Char(string="Attending Physician", related='care_provider.name')
    discharge_admission_diagnosis = fields.Char(string="Admission Diagnosis")
    # discharge_final_diagnoses = fields.Many2one('oeh.medical.pathology', string='Diagnoses')
    discharge_condition = fields.Text(string="Condition on discharge")
    discharge_final_diagnoses = fields.Text(string="Final Diagnoses")

    present_illness_history = fields.Text(string="History of present illness")
    # discharge_medications = fields.One2many('oeha.dischargemedication', 'evaluation_id', string="Discharge Medications")
    # discharge_procedures = fields.One2many('oeha.dischargeprocedure', 'evaluation_id',
    #                                        string="Discharge Treatments / Procedures Performed")
    discharge_instructions = fields.Text(string="Additional Instructions")
    discharge_completed_by = fields.Many2one('res.users', 'Completed By', default=lambda self: self.env.user)

    # Doctor Edit Function
    can_edit = fields.Boolean(string='Edit')

    # Evaluation addedndum
    evaluation_addendum = fields.Text(string="Evaluation addendum")

    # Vital Signs and Antropometry
    vital_signs_anthropometry_notes = fields.Text(string="Vital signs: Notes",
                                                  help="Vital signs and anthropometry notes")
    vitalsigns = fields.One2many('patient.vitalsigns', 'evaluation_id', string="Vital Signs")

    # Extended Visit Summary Tab fields
    follow_up = fields.Selection(FOLLOW_UP, string="Follow-Up")
    info_diagnosis_discharge = fields.Text(string="Information on Diagnosis", store=True,)
     
    # # added signs and symptoms fields
    # # general
    # general_symptom_fever = fields.Selection([('Intermittent', 'Intermittent'), ('continuous', 'continuous'),
    #                                           ('step-ladder', 'step-ladder'), ('high grade', 'High grade'),
    #                                           ('low grade', 'Low Grade')], 'General: Fever')
    # general_symptom_malaise = fields.Boolean(string="General: Malaise")
    # general_symptom_joint_ache = fields.Boolean(string="General: Joint Aches")
    # general_symptom_dizziness = fields.Boolean(string="General: Dizziness")
    # general_symptom_chills = fields.Boolean(string="General: Chills")
    # general_symptom_night_sweats = fields.Boolean(string="General: Night Sweats")
    # general_symptom_weight = fields.Selection([('gain', 'Gain'), ('loss', 'Loss')], 'General: Weight')
    # general_symptom_easy_fatigability = fields.Boolean(string="General: Easy Fatigability")
    # general_symptom_pain_site = fields.Char(string="Pain: Site")
    # general_symptom_pain_onset = fields.Date(string="Pain: Onset")
    # general_symptom_pain_character = fields.Char(string="Pain: Character")
    # general_symptom_pain_severity = fields.Char(string="Pain: Severity")
    # general_symptom_pain_radiation = fields.Char(string="Pain: Radiation")
    # general_symptom_pain_aggravating = fields.Char(string="Pain: Aggravating factors")
    # general_symptom_pain_relieving = fields.Char(string="Pain: Relieving factors")
    # general_symptom_pain_associated = fields.Char(string="Pain: Associated symptoms")
    # general_symptom_pain_possible_etiology = fields.Char(string="Pain: Possible etiology")

    # general_symptom_swelling_site = fields.Char(string="Swelling: Site")
    # general_symptom_swelling_progression = fields.Selection([('slow', 'Slow'), ('rapid', 'Rapid')],
    #                                                         'Swelling: Progression')
    # general_symptom_swelling_associated_pain = fields.Boolean(string="Swelling: Associated pain")
    # general_symptom_swelling_itchy = fields.Boolean(string="Swelling: Itchy")
    # general_symptom_swelling_associated_symptom = fields.Char(string="Swelling: Associated symptoms")
    # general_symptom_swelling_possible_etiology = fields.Char(string="Swelling: Possible etiology")
    # general_symptom_swelling_others = fields.Char(string="Swelling Others: Possible etiology")
    # general_symptom_swelling_left_breast_lump = fields.Boolean(string="Swelling: Left Breast Lump")
    # general_symptom_swelling_right_breast_lump = fields.Boolean(string="Swelling: Right Breast Lump")
    # general_symptom_swelling_rash = fields.Boolean(string="Swelling: Rash")
    # general_symptom_swelling_rash_others = fields.Boolean(string="Swelling: Others")

    # general_sign_unwell = fields.Boolean(string="General:Unwell")
    # general_sign_acutely_ill = fields.Boolean(string="General: Acutely ill-looking")
    # general_sign_chronically_ill = fields.Boolean(string="General: Chronically ill-looking")
    # general_sign_wasted = fields.Boolean(string="General: Wasted")
    # general_sign_stunted = fields.Boolean(string="General: Stunted")
    # general_sign_fluffy_hair = fields.Boolean(string="General: Fluffy hair")
    # general_sign_pallor = fields.Boolean(string="General: Pallor")
    # general_sign_jaundice = fields.Boolean(string="General: Jaundice")
    # general_sign_central_cyanosis = fields.Boolean(string="General: Central cyanosis")
    # general_sign_dehydration = fields.Selection([('mild', 'Mild'), ('moderate', 'Moderate'),
    #                                              ('severe', 'Severe')], 'General: Dehydration')
    # general_sign_digital_clubbing = fields.Boolean(string="General: Digital clubbing")
    # general_sign_peripheral_cyanosis = fields.Boolean(string="General: Peripheral cyanosis")
    # general_sign_simian_crease = fields.Boolean(string="General: Simian crease")
    # general_sign_peripheral_lymph_site = fields.Char(string="Lymp Site")
    # general_sign_peripheral_lymph_character = fields.Char(string="Lymp Character")
    # general_sign_peripheral_lymph_changes = fields.Char(string="Lymp Overlying skin changes")
    # general_sign_pedal_edema = fields.Selection([('pitting', 'Pitting'), ('non pitting', 'Non Pitting'),
    #                                              ], 'Pedal edema')
    # general_sign_rashes_location = fields.Char(string="Rashes Location")
    # general_sign_rashes_nature = fields.Char(string="Rashes Nature")
    # general_sign_swelling_site = fields.Char(string="Sign: Swelling Site")
    # general_sign_swelling_size = fields.Char(string="Sign: Swelling Size")
    # general_sign_swelling_consistency = fields.Char(string="Sign: SwellingConsistency")
    # general_sign_swelling_overlying_skin = fields.Char(string="Sign: Swelling Overlying skin changes")
    # general_sign_swelling_attached_to_skin = fields.Boolean(string="Sign: Swelling Attached to skin")
    # general_sign_swelling_attached_to_underlying = fields.Boolean(
    #     string="Sign: Swelling Attached to underlying structures")
    # general_sign_differential_warmth = fields.Boolean(string="Sign: Swelling Differential warmth")
    # general_sign_swelling_mobile = fields.Selection(
    #     [('free', 'Free'), ('partial', 'Partial'), ('not mobile', 'Not Mobile')
    #      ], 'Sign: Swelling Pedal edema')
    # general_sign_swelling_fluctuant = fields.Boolean(string="Sign: Swelling Fluctuant")
    # general_sign_swelling_pulsatile = fields.Boolean(string="Sign: Swelling Pulsatile")
    # general_sign_additional_findings = fields.Text(string="Sign: Swelling Additional findings")

    # # Central Nervous System
    # # symptom
    # cns_symptom_headache_nature = fields.Char(string="Headache Nature")
    # cns_symptom_headache_side = fields.Char(string="Headache Side")
    # cns_symptom_headache_radiation = fields.Char(string="Headache Radiation")
    # cns_symptom_headache_severity = fields.Char(string="Headache Severity")
    # cns_symptom_headache_associated_symptoms = fields.Char(string="Headache Associated symptoms")
    # cns_symptom_headache_aggravating_factors = fields.Char(string="Headache Aggravating factors")
    # cns_symptom_headache_relieving_factors = fields.Char(string="Headache Relieving factors")
    # cns_symptom_headache_aura = fields.Char(string="Headache Aura")

    # cns_symptom_limb_weakness = fields.Boolean(string="Limb weakness")
    # cns_symptom_limb_blurry_vision = fields.Boolean(string="Limb Blurry vision")
    # cns_symptom_limb_insomnia = fields.Boolean(string="Limb Insomnia")
    # cns_symptom_limb_convulsion = fields.Char(string="Limb Convulsion")
    # cns_symptom_limb_amnesia = fields.Boolean(string="Limb Amnesia")
    # cns_symptom_limb_sphincteric_disturbance = fields.Selection(
    #     [('hypoactive', 'Hypoactive'), ('Hyperactive', 'Partial')
    #      ], 'Sphincteric disturbance')
    # cns_symptom_limb_others = fields.Text(string="Limb Others")

    # # signs
    # cns_sign_conscious = fields.Boolean("CNS: Conscious")
    # cns_sign_unconscious = fields.Boolean("CNS: Unconscious")
    # cns_sign_orientation_oriented = fields.Selection([('time', 'Time'), ('place', 'Place'), ('person', 'Person')
    #                                                   ], 'CNS: Orientation')
    # cns_sign_orientation_not_oriented = fields.Boolean("CNS: Not oriented")
    # cns_glasgow_coma_score_eye_opening_score = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')],
    #                                                             'CNS: Eye opening score')
    # cns_glasgow_coma_score_motor_score = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
    #                                                       'CNS: Best motor response score')
    # cns_glasgow_coma_score_verbal_score = fields.Selection(
    #     [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6')], 'CNS: Best verbal response score')

    # cns_sign_cranial_nerve_deficits = fields.Boolean(string="Cranial nerve deficits")
    # cns_sign_fasciculations = fields.Boolean(string="Fasciculations")
    # cns_sign_right_upper_limb = fields.Selection(
    #     [('normal', 'normal'), ('weakness', 'weakness'), ('hypertonia', 'hypertonia'),
    #      ('hypotonia', 'hypotonia'), ('hyperreflexia', 'hyperreflexia'), ('hyporeflexia', 'hyporeflexia')],
    #     'Right upper limb')
    # cns_sign_right_lower_limb = fields.Selection(
    #     [('normal', 'normal'), ('weakness', 'weakness'), ('hypertonia', 'hypertonia'),
    #      ('hypotonia', 'hypotonia'), ('hyperreflexia', 'hyperreflexia'), ('hyporeflexia', 'hyporeflexia')],
    #     'Right lower limb')
    # cns_sign_left_upper_limb = fields.Selection(
    #     [('normal', 'normal'), ('weakness', 'weakness'), ('hypertonia', 'hypertonia'),
    #      ('hypotonia', 'hypotonia'), ('hyperreflexia', 'hyperreflexia'), ('hyporeflexia', 'hyporeflexia')],
    #     'Left upper limb')
    # cns_sign_left_lower_limb = fields.Selection(
    #     [('normal', 'normal'), ('weakness', 'weakness'), ('hypertonia', 'hypertonia'),
    #      ('hypotonia', 'hypotonia'), ('hyperreflexia', 'hyperreflexia'), ('hyporeflexia', 'hyporeflexia')],
    #     'Left lower limb')
    # cns_sign_babinski_reflex = fields.Boolean(string="Babinski reflex")
    # cns_sign_ankle_clonus = fields.Boolean(string="Ankle clonus")
    # cns_sign_loss_of_sensation = fields.Selection(
    #     [('fine touch', 'fine touch'), ('crude touch', 'crude touch'), ('pain', 'pain'),
    #      ('joint position', 'joint position'), ('vibration sense', 'vibration sense')], 'Loss of sensation')
    # cns_sign_gait = fields.Selection([('normal', 'normal'), ('antalgic', 'antalgic'), ('swaddling', 'swaddling'),
    #                                   ('hemiplegic', 'hemiplegic'), ('diplegic', 'diplegic'),
    #                                   ('choreiform', 'choreiform'),
    #                                   ('ataxia', 'ataxia'), ('Parkinsonian', 'Parkinsonian')], 'Gait')
    # cns_sign_dysdiadochokinesis = fields.Boolean(string="Dysdiadochokinesis")
    # cns_sign_intention_tremor = fields.Boolean(string="Intention tremor")
    # cns_sign_rebound_phenomena = fields.Boolean(string="Rebound phenomena")
    # cns_sign_dysmetria = fields.Boolean(string="Dysmetria")
    # cns_sign_nystagmus = fields.Boolean(string="CNS Sign: Nystagmus")
    # cns_sign_dysarthria = fields.Boolean(string="Dysarthria")
    # cns_sign_titubation = fields.Boolean(string="Titubation")
    # cns_sign_torticollis = fields.Boolean(string="Torticollis")
    # cns_sign_romberg_sign = fields.Selection([('positive', 'positive'), ('negative', 'negative')], 'Romberg sign')
    # cns_sign_others = fields.Text(string="CNS: Others")

    # # Musculoskeletal system
    # # symptoms
    # symptom_muscle_low_back_pains = fields.Boolean(string="Low back pains")
    # symptom_muscle_muscle_aches = fields.Boolean(string="Muscle aches")
    # symptom_muscle_bone_pains = fields.Boolean(string="Bone pains")
    # symptom_muscle_fractures = fields.Boolean(string="Symptom: Fractures")
    # symptom_muscle_dislocations = fields.Boolean(string="Symptom: Dislocations")
    # symptom_muscle_others = fields.Text(string="Symptom: Muscle Others")

    # # signs
    # sign_muscle_fractures = fields.Boolean(string="Sign: Fractures")
    # sign_muscle_dislocation = fields.Boolean(string="Sign: Dislocation")
    # sign_muscle_scoliosis = fields.Boolean(string="Scoliosis")
    # sign_muscle_lordosis = fields.Boolean(string="Lordosis")
    # sign_muscle_kyphosis = fields.Boolean(string="Kyphosis")
    # sign_muscle_genu_valga = fields.Boolean(string="Genu valga")
    # sign_muscle_genu_vara = fields.Boolean(string="Genu vara")
    # sign_muscle_windswept_deformity = fields.Boolean(string="Windswept deformity")
    # sign_muscle_clubfoot = fields.Boolean(string="Clubfoot")
    # sign_muscle_amputations = fields.Boolean(string="Amputations")
    # sign_muscle_others = fields.Text(string="Sign: Muscle Others")

    # # Respiratory system
    # # symptoms
    # symptom_respiratory_coryza = fields.Boolean(string="Coryza")
    # symptom_respiratory_cough = fields.Boolean(string="Respiratory: Cough")
    # symptom_respiratory_sore_throat = fields.Boolean(string="Respiratory: Sore throat")
    # symptom_respiratory_difficulty_with_breathing = fields.Boolean(string="Difficulty with breathing")
    # symptom_respiratory_breathlessness = fields.Boolean(string="Respiratory: Breathlessness")
    # symptom_respiratory_fast_breathing = fields.Boolean(string="Respiratory: Fast breathing")
    # symptom_respiratory_mouth_breathing = fields.Boolean(string="Respiratory: Mouth breathing")
    # symptom_respiratory_noisy_breathing = fields.Boolean(string="Respiratory: Noisy breathing")
    # symptom_respiratory_night_sweats = fields.Boolean(string="Respiratory: Night sweats")
    # symptom_respiratory_orthopnea = fields.Boolean(string="Respiratory Orthopnea")
    # symptom_respiratory_paroxysmal_nocturnal_dypsnea = fields.Boolean(string="Paroxysmal nocturnal dypsnea")
    # symptom_respiratory_haemoptysis = fields.Boolean(string="Haemoptysis")
    # symptom_respiratory_hoarseness = fields.Boolean(string="Respiratory Hoarseness")
    # symptom_respiratory_stridor = fields.Boolean(string="Stridor")
    # symptom_respiratory_snoring = fields.Boolean(string="Snoring")
    # symptom_respiratory_nasal_stuffiness = fields.Boolean(string="Symptom: Nasal stuffiness")
    # symptom_respiratory_others = fields.Text(string="Respiratory: Others")

    # # signs
    # sign_respiratory_respiratory_distress = fields.Boolean(string="Respiratory distress")
    # sign_respiratory_nasal_stuffiness = fields.Boolean(string="Nasal stuffiness")
    # sign_respiratory_pursed_lip = fields.Boolean(string="Pursed lip")
    # sign_respiratory_hepatic_fetor = fields.Boolean(string="Hepatic fetor")
    # sign_respiratory_barrel_chest = fields.Boolean(string="Barrel chest")
    # sign_respiratory_pigeon_chest = fields.Boolean(string="Pigeon chest (pectum carinatum)")
    # sign_respiratory_funnel_chest = fields.Boolean(string="Funnel chest (pectum excavatum)")
    # sign_respiratory_scarification_marks = fields.Boolean(string="Scarification marks")
    # sign_respiratory_rickety_rosary = fields.Boolean(string="Rickety rosary")
    # sign_respiratory_uniform_chest_expansion = fields.Boolean(string="Uniform chest expansion")

    # sign_respiratory_tracheal_deviation = fields.Selection([('normal', 'Normal'), ('left', 'Left'),
    #                                                         ('right', 'Right')], 'Tracheal deviation')
    # sign_respiratory_reduced_expansion = fields.Selection([('left', 'Left'), ('right', 'Right')
    #                                                        ], 'Reduced expansion')
    # sign_respiratory_resonant_percussion_note = fields.Selection([('left', 'Left'), ('right', 'Right')
    #                                                               ], 'Resonant percussion note')
    # sign_respiratory_hyperresonant_percussion_note = fields.Selection([('left', 'Left'), ('right', 'Right')
    #                                                                    ], 'Hyperresonant percussion note')
    # sign_respiratory_dull_percussion_note = fields.Selection([('left', 'Left'), ('right', 'Right')
    #                                                           ], 'Dull percussion note')
    # sign_respiratory_stony_dull_percussion_note = fields.Selection([('left', 'Left'), ('right', 'Right')
    #                                                                 ], 'Stony dull percussion note')
    # sign_respiratory_vesicular_breath_sounds = fields.Selection([('left', 'Left'), ('right', 'Right')
    #                                                              ], 'Vesicular breath sounds')
    # sign_respiratory_crepitations = fields.Selection([('left', 'Left'), ('right', 'Right')
    #                                                   ], 'Crepitations')
    # sign_respiratory_fine_crackles = fields.Selection([('left', 'Left'), ('right', 'Right')
    #                                                    ], 'Fine crackles')
    # sign_respiratory_coarse_crackles = fields.Selection([('left', 'Left'), ('right', 'Right')
    #                                                      ], 'Coarse crackles')
    # sign_respiratory_others = fields.Text(string="Sign: Respiratory Others")

    # # Cardiovascular system
    # # symptom
    # symptom_cardio_chest_pain_site = fields.Char(string="Chest Pain: Site")
    # symptom_cardio_chest_pain_onset = fields.Char(string="Chest Pain: Onset")
    # symptom_cardio_chest_pain_severity = fields.Char(string="Chest Pain: Severity")
    # symptom_cardio_chest_pain_nature = fields.Char(string="Chest Pain: Nature")
    # symptom_cardio_chest_pain_radiation = fields.Char(string="Chest Pain: Radiation")
    # symptom_cardio_chest_pain_duration = fields.Char(string="Chest Pain: Duration")
    # symptom_cardio_chest_pain_aggravating_factors = fields.Char(string="Chest Pain: Aggravating factors")
    # symptom_cardio_chest_pain_relieving_factors = fields.Char(string="Chest Pain: Relieving factors")
    # symptom_cardio_chest_pain_associated_symptoms = fields.Char(string="Chest Pain: Associated symptoms")
    # symptom_cardio_palpitations = fields.Boolean(string="Palpitations")
    # symptom_cardio_claudication = fields.Boolean(string="Claudication")
    # symptom_cardio_others = fields.Boolean(string="Symptom: Cardio Others")

    # # sign
    # sign_cardio_cold_extremities = fields.Boolean(string="Cold extremities")
    # sign_cardio_bruits = fields.Boolean(string="Bruits")
    # sign_cardio_splinter_hemorrhage = fields.Boolean(string="Splinter hemorrhage")
    # sign_cardio_osler_nodes = fields.Boolean(string="Osler nodes")
    # sign_cardio_janeway_nodes = fields.Boolean(string="Janeway nodes")
    # sign_cardio_rhythm = fields.Selection([('regular', 'regular'), ('irregularly irregular', 'irregularly irregular'),
    #                                        ('regularly irregular', 'regularly irregular')], 'Rhythm')
    # sign_cardio_synchronicity = fields.Selection([('synchronous', 'Synchronous'),
    #                                               ('radioradial delay', 'radioradial delay'),
    #                                               ('radiofemoral delay', 'radiofemoral delay')], 'Synchronicity')
    # sign_cardio_thickened_arterial_wall = fields.Boolean(string="Thickened arterial wall")
    # sign_cardio_locomotor_brachialis = fields.Boolean(string="Locomotor brachialis")
    # sign_cardio_jvp = fields.Selection([('normal', 'Normal'), ('raised', 'Raised')], 'JVP')
    # sign_cardio_apex_beat = fields.Selection([('normal', 'Normal'), ('displaced', 'displaced'), ('tapping', 'tapping'),
    #                                           ('diffuse', 'diffuse'), ('double impulse', 'double impulse'),
    #                                           ('heave', 'heave'),
    #                                           ('thrills', 'thrills')], 'Apex beat')
    # sign_cardio_heart_sounds = fields.Selection([('first', 'first'), ('second', 'second'), ('third', 'third'),
    #                                              ('fourth', 'fourth')], 'Heart sounds')
    # sign_cardio_heart_murmurs = fields.Selection(
    #     [('nil', 'nil'), ('pansystolic', 'pansystolic'), ('early diastolic', 'early diastolic'),
    #      ('mid-systolic', 'mid-systolic'), ('mid-diastolic', 'mid-diastolic'), ('continuous', 'continuous')], 'Murmurs')
    # sign_cardio_others = fields.Text(string="Sign: Cardio Others")

    # # Abdomen
    # symptom_abdomen_abdominal_site = fields.Char(string="Abdominal: Site")
    # symptom_abdomen_abdominal_onset = fields.Char(string="Abdominal: Onset")
    # symptom_abdomen_abdominal_nature = fields.Char(string="Abdominal: Nature")
    # symptom_abdomen_abdominal_duration = fields.Char(string="Abdominal: Duration")
    # symptom_abdomen_abdominal_relieving_factors = fields.Char(string="Abdominal: Relieving factors")
    # symptom_abdomen_abdominal_aggravating_factors = fields.Char(string="Abdominal: Aggravating factors")
    # symptom_abdomen_abdominal_severity = fields.Char(string="Abdominal: Severity")
    # symptom_abdomen_abdominal_radiation = fields.Char(string="Abdominal: Radiation")
    # symptom_abdomen_abdominal_associated_symptoms = fields.Text(string="Abdominal: Associated symptoms")
    # symptom_abdomen_distension = fields.Boolean(string="Abdominal: Distension")
    # symptom_abdomen_nausea = fields.Boolean(string="Abdominal: Nausea")
    # symptom_abdomen_vomitting_frequency = fields.Char(string="Vomitting Frequency")
    # symptom_abdomen_vomitting_colour = fields.Char(string="Vomitting Colour")
    # symptom_abdomen_vomitting_projectile = fields.Boolean(string="Vomitting Projectile")
    # symptom_abdomen_vomitting_bilious = fields.Boolean(string="Vomitting Bilious")
    # symptom_abdomen_vomitting_feculent = fields.Char(string="Feculent")
    # symptom_abdomen_haematemesis = fields.Boolean(string="Haematemesis")
    # symptom_abdomen_dysphagia = fields.Boolean(string="Abdomen Dysphagia")
    # symptom_abdomen_indigestion = fields.Boolean(string="Indigestion")
    # symptom_abdomen_dyspepsia = fields.Boolean(string="Dyspepsia")
    # symptom_abdomen_reflux = fields.Boolean(string="Reflux")

    # symptom_abdomen_diarrhea_frequency = fields.Char(string="Diarrhea: Frequency")
    # symptom_abdomen_diarrhea_Watery = fields.Boolean(string="Diarrhea: Watery")
    # symptom_abdomen_diarrhea_mucoid = fields.Boolean(string="Diarrhea: Mucoid")
    # symptom_abdomen_diarrhea_bloody = fields.Boolean(string="Diarrhea: Bloody")
    # symptom_abdomen_diarrhea_tarry = fields.Boolean(string="Diarrhea: Tarry")
    # symptom_abdomen_diarrhea_foul_smelling = fields.Boolean(string="Diarrhea: Foul smelling")

    # symptom_abdomen_constipation = fields.Boolean(string="Abdomen: Constipation")
    # symptom_abdomen_obstipation = fields.Boolean(string="Obstipation")
    # symptom_abdomen_alternating = fields.Boolean(string="Alternating constipation and diarrhea")
    # symptom_abdomen_tenesmus = fields.Boolean(string="Tenesmus")
    # symptom_abdomen_borborygmi = fields.Boolean(string="Borborygmi")
    # symptom_abdomen_haematochezia = fields.Boolean(string="Haematochezia")
    # symptom_abdomen_pale_bulky_stools = fields.Boolean(string="Pale bulky stools")
    # symptom_abdomen_appetite_gain = fields.Boolean(string="Appetite gain")
    # symptom_abdomen_appetite_loss = fields.Boolean(string="Appetite loss")
    # symptom_abdomen_early_satiety = fields.Boolean(string="Early satiety")
    # symptom_abdomen_jaundice = fields.Boolean(string="Abdomen: Jaundice")
    # symptom_abdomen_blood_in_stool = fields.Selection(
    #     [('before stool', 'before stool'), ('mixed with stool', 'mixed with stool'),
    #      ('after stool', 'after stool')], 'Blood in stool')
    # symptom_abdomen_others = fields.Text(string="Abdomen: Others")

    # sign_abdomen_flat = fields.Boolean(string="Flat")
    # sign_abdomen_scaphoid = fields.Boolean(string="Scaphoid")
    # sign_abdomen_full = fields.Boolean(string="Abdomen: Full")
    # sign_abdomen_distended = fields.Boolean(string="Distended")
    # sign_abdomen_scarification_marks = fields.Boolean(string="Abdomen Scarification marks")
    # sign_abdomen_umbilical_fullness = fields.Boolean(string="Umbilical fullness")
    # sign_abdomen_distended_veins = fields.Boolean(string="Distended veins")
    # sign_abdomen_surgical_scar = fields.Char(string="Surgical scar")
    # sign_abdomen_visible_bowel_movement = fields.Boolean(string="Visible bowel movement")
    # sign_abdomen_intact_hernial_orifices = fields.Boolean(string="Intact hernial orifices")
    # sign_abdomen_hernia = fields.Char(string="Hernia")
    # sign_abdomen_gravid_tenderness = fields.Selection([('LH', 'LH'), ('epigastric', 'epigastric'), ('RH', 'RH'),
    #                                                    ('RI', 'RI'), ('umbilical', 'umbilical'), ('LI', 'LI'),
    #                                                    ('LL', 'LL'), ('suprapubic', 'suprapubic'),
    #                                                    ('RL', 'RL')], 'Gravid Tenderness')
    # sign_abdomen_rebound_tenderness = fields.Boolean(string="Rebound Tenderness")
    # sign_abdomen_liver = fields.Selection([('Hepatomegaly', 'Hepatomegaly'), ('Tender liver', 'Tender liver'),
    #                                        ('Smooth liver', 'Smooth liver'), ('Rough liver', 'Rough liver')], 'Liver')
    # sign_abdomen_spleen = fields.Selection([('normal', 'normal'), ('tender', 'tender'), ('enlarged', 'enlarged')],
    #                                        'Spleen')
    # sign_abdomen_kidneys = fields.Selection([('normal', 'normal'), ('enlarged', 'enlarged')], 'Kidneys')
    # sign_abdomen_renal_angle = fields.Selection([('right ', 'right '), ('left', 'left')], 'Renal angle tenderness')
    # sign_abdomen_kidney_enlargement = fields.Selection([('right', 'right'), ('left', 'left')], 'Kidney enlargement')

    # sign_abdomen_abdominal_location = fields.Char(string="Abdominal Location")
    # sign_abdomen_abdominal_size = fields.Char(string="Abdominal Size")
    # sign_abdomen_abdominal_tenderness = fields.Selection([('Tender', 'Tender'), ('non-tender', 'non-tender')],
    #                                                      'Abdominal Tenderness')
    # sign_abdomen_abdominal_definition = fields.Selection([('Well-defined', 'Well-defined'), ('Attached', 'Attached')],
    #                                                      'Abdominal Definition')
    # sign_abdomen_abdominal_texture = fields.Selection([('Smooth', 'Smooth'), ('Irregular', 'Irregular')],
    #                                                   'Abdominal Texture')
    # sign_abdomen_abdominal_pulsatile = fields.Selection(
    #     [('Pulsatile', 'Pulsatile'), ('Non-pulsatile', 'Non-pulsatile')], 'Abdominal Pulsatile')

    # sign_abdomen_ascites = fields.Boolean(string="Abdomen Ascites")
    # sign_abdomen_bowel_sounds = fields.Selection([('normal', 'normal'), ('absent', 'absent'),
    #                                               ('hypoactive', 'hypoactive'), ('hyperactive', 'hyperactive')],
    #                                              'Bowel sounds')
    # sign_abdomen_perianal_hygiene = fields.Selection([('good', 'good'), ('fair', 'fair'), ('bad', 'bad')],
    #                                                  'Perianal hygiene')
    # sign_sphincteric_tone = fields.Selection([('good', 'good'), ('fair', 'fair'), ('bad', 'bad')], 'Sphincteric tone')
    # sign_abdomen_haemorrhoids = fields.Char(string="Haemorrhoids")
    # sign_abdomen_anal_fissure = fields.Char(string="Anal fissure")
    # sign_abdomen_fistula_in_ano = fields.Char(string="Fistula-in-ano")
    # sign_abdomen_prostate = fields.Selection([('normal', 'normal'), ('palpable', 'palpable'),
    #                                           ('enlarged', 'enlarged'), ('smooth', 'smooth'), ('rough', 'rough')],
    #                                          'Prostate')
    # sign_abdomen_rectal_mass_palpble = fields.Boolean(string="Rectal mass palpable")
    # sign_abdomen_inspissated_feces_palpable = fields.Boolean(string="Inspissated feces palpable")
    # sign_abdomen_examined_finger_stain = fields.Selection([('stools', 'stools'), ('blood', 'blood'),
    #                                                        ('mucus', 'mucus')], 'Examining finger stained with')
    # sign_abdomen_others = fields.Text(string="Sign: Abdomen Others")

    # # Ear, Nose & Throat
    # symptom_ent_ear_discharge = fields.Selection([('right', 'right'), ('left', 'left'), ('serous', 'serous'),
    #                                               ('purulent', 'purulent'), ('bloody', 'bloody')], 'Ear discharge')
    # symptom_ent_ear_pain = fields.Selection([('right', 'right'), ('left', 'left')], 'Ear pain')
    # symptom_ent_ear_hearing_loss = fields.Selection([('left', 'left'), ('right', 'right')], 'Hearing loss')
    # symptom_ent_ear_tinnitus = fields.Selection([('left', 'left'), ('right', 'right')], 'ENT: Tinnitus')
    # symptom_ent_vertigo = fields.Boolean(string="ENT: Vertigo")
    # symptom_ent_epistaxis = fields.Boolean(string="ENT: Epistaxis")
    # symptom_ent_neck_swelling = fields.Char(string="Neck swelling")
    # symptom_ent_neck_lump = fields.Boolean(string="Neck lump")
    # symptom_ent_choking = fields.Boolean(string="Choking")
    # symptom_ent_hoarseness = fields.Char(string="ENT: Hoarseness")
    # symptom_ent_others = fields.Text(string="Symptom: ENT Others")

    # sign_ent_auricular_lymph = fields.Char(string="Auricular lymphadenopathy")
    # sign_ent_ear_discharge = fields.Selection([('serous', 'serous'), ('bloody', 'bloody'),
    #                                            ('purulent', 'purulent')], 'ENT: Ear discharge')
    # sign_ent_tragal_tenderness = fields.Selection([('left', 'left'), ('right', 'right')], 'Tragal tenderness')
    # sign_ent_describe_tympanum = fields.Char(string="Describe tympanum")
    # sign_ent_rinne_test_left_ear = fields.Selection([('AC>BC', 'AC>BC'), ('BC>AC', 'BC>AC')], 'Left ear')
    # sign_ent_rinne_test_right_ear = fields.Selection([('AC>BC', 'AC>BC'), ('BC>AC', 'BC>AC')], 'Right ear')
    # sign_ent_weber_test = fields.Selection(
    #     [('Lateralizes to right', 'Lateralizes to right'), ('lateralizes to left', 'lateralizes to left')],
    #     'Weber test')
    # sign_ent_neck_mass_position = fields.Selection([('Anterior', 'Anterior'), ('Right', 'Right'), ('Left', 'Left')],
    #                                                'Neck Mass Position')
    # sign_ent_neck_mass_tender = fields.Selection([('Tender', 'Tender'), ('non-tender', 'non-tender')],
    #                                              'Neck Mass Tender')
    # sign_ent_neck_mass_temperature = fields.Selection([('Warm', 'Warm'), ('Normal', 'Normal'), ('Cold', 'Cold')],
    #                                                   'Neck Mass Temperature')
    # sign_ent_neck_mass_texture = fields.Selection([('Rough', 'Rough'), ('Smooth', 'Smooth')], 'Neck Mass Texture')
    # sign_ent_neck_mass_pulsatile = fields.Selection([('Pulsatile', 'Pulsatile'), ('Non-pulsatile', 'Non-pulsatile')],
    #                                                 'Neck Mass Pulsatile')
    # sign_ent_others = fields.Text(string="Sign: ENT Others")

    # # Genitourinary system
    # symptom_genitourinary_dysuria = fields.Boolean(string="Genito: Dysuria")
    # symptom_genitourinary_foul_smelling_urine = fields.Boolean(string="Foul-smelling urine")
    # symptom_genitourinary_increased_frequency = fields.Boolean(string="Increased frequency")
    # symptom_genitourinary_hesitancy = fields.Boolean(string="Hesitancy")
    # symptom_genitourinary_weak_stream = fields.Boolean(string="Weak stream")
    # symptom_genitourinary_intermittency = fields.Boolean(string="Intermittency")
    # symptom_genitourinary_terminal_dribbling = fields.Boolean(string="Terminal dribbling")
    # symptom_genitourinary_urgency = fields.Boolean(string="Urgency")
    # symptom_genitourinary_urge_incontinence = fields.Boolean(string="Urge incontinence")
    # symptom_genitourinary_straining = fields.Boolean(string="Straining")
    # symptom_genitourinary_nocturia = fields.Boolean(string="Genito: Nocturia")
    # symptom_genitourinary_haematuria = fields.Selection([('initial', 'initial'), ('total', 'total'),
    #                                                      ('terminal', 'terminal')], 'Haematuria')
    # symptom_genitourinary_splitting_urinary_stream = fields.Boolean(string="Splitting of urinary stream")
    # symptom_genitourinary_pyuria = fields.Boolean(string="Pyuria")
    # symptom_genitourinary_genital_discharge = fields.Selection([('white', 'white'), ('yellow', 'yellow'),
    #                                                             ('red', 'red'), ('foul smelling', 'foul smelling')],
    #                                                            'Genital discharge')
    # symptom_genitourinary_genital_itching = fields.Boolean(string="Genital itching")
    # symptom_genitourinary_bleeding = fields.Boolean(string="Genital bleeding")
    # symptom_genitourinary_others = fields.Text(string="Symptom: Genitourinary Others")

    # sign_genitourinary_normal_genitalia = fields.Boolean(string="Normal genitalia")
    # sign_genitourinary_inflammation = fields.Boolean(string="Inflammation")
    # sign_genitourinary_circumcision = fields.Selection(
    #     [('circumcised', 'circumcised'), ('uncircumcised', 'uncircumcised')], 'Circumcision')
    # sign_genitourinary_genital_cutting = fields.Boolean(string="Genital cutting")
    # sign_genitourinary_meatus = fields.Selection([('tip', 'tip'), ('ventral', 'ventral'), ('dorsal', 'dorsal')],
    #                                              'Meatus')
    # sign_genitourinary_urethral_induration = fields.Boolean(string="Urethral induration")
    # sign_genitourinary_chordee = fields.Selection([('ventral', 'ventral'), ('dorsal', 'dorsal')], 'Chordee')
    # sign_genitourinary_perineal_rashes = fields.Boolean(string="Perineal rashes")
    # sign_genitourinary_genital_sores = fields.Boolean(string="Genital sores")
    # sign_genitourinary_ambiguous_genitalia = fields.Boolean(string="Ambiguous genitalia")
    # sign_genitourinary_scrotum = fields.Selection([('Normal', 'Normal'), ('Swollen', 'Swollen')], 'Scrotum')
    # sign_genitourinary_cervical_excitatory_tenderness = fields.Boolean(string="Cervical excitatory tenderness")
    # sign_genitourinary_palpable_testes = fields.Selection([('right', 'right'), ('left', 'left')], 'Palpable testes')
    # sign_genitourinary_hydrocele = fields.Boolean(string="Hydrocele")
    # sign_genitourinary_varicocele = fields.Boolean(string="Varicocele")
    # sign_genitourinary_others = fields.Text(string="Sign: Genitourinary Others")

    # # Psychiatry
    # symptom_psychiatry_low_mood = fields.Boolean(string="Low mood")
    # symptom_psychiatry_mania = fields.Boolean(string="Mania")
    # symptom_psychiatry_mood_swings = fields.Boolean(string="Mood swings")
    # symptom_psychiatry_hallucinations = fields.Selection(
    #     [('visual', 'visual'), ('auditory', 'auditory'), ('sensory', 'sensory')], 'Hallucinations')
    # symptom_psychiatry_delusions = fields.Selection(
    #     [('love', 'love'), ('grandiosity', 'grandiosity'), ('persecutory', 'persecutory')], 'Delusions')
    # symptom_psychiatry_delusions_others = fields.Text(string="Delusion: others")
    # symptom_psychiatry_anhedonia = fields.Boolean(string="Anhedonia")
    # symptom_psychiatry_insomnia_duration = fields.Char(string="Insomnia Duration")
    # symptom_psychiatry_insomnia_quality = fields.Char(string="Insomnia Quality")
    # symptom_psychiatry_hypersomnolence = fields.Boolean(string="Hypersomnolence")
    # symptom_psychiatry_anxiety = fields.Boolean(string="Anxiety")
    # symptom_psychiatry_phobia = fields.Char(string="Phobia")
    # symptom_psychiatry_suicidal_ideations = fields.Boolean(string="Suicidal ideations")
    # symptom_psychiatry_obsessions = fields.Boolean(string="Obsessions")
    # symptom_psychiatry_compulsions = fields.Boolean(string="Compulsions")
    # symptom_psychiatry_anorexia = fields.Boolean(string="Psychiatry: Anorexia")
    # symptom_psychiatry_bulimia = fields.Boolean(string="Bulimia")
    # symptom_psychiatry_thoughts = fields.Selection(
    #     [('insertion', 'insertion'), ('broadcast', 'broadcast'), ('deletion', 'deletion')], 'Thoughts')
    # symptom_psychiatry_libido = fields.Selection([('same', 'same'), ('increased', 'increased'), ('reduced', 'reduced')],
    #                                              'Libido')
    # symptom_psychiatry_guilt = fields.Boolean(string="Guilt")
    # symptom_psychiatry_others = fields.Boolean(string="Psychiatry Others")

    # sign_psychiatry_oriented = fields.Boolean(string="Oriented")
    # sign_psychiatry_abnormal_behaviour = fields.Boolean(string="Abnormal behaviour")
    # sign_psychiatry_mood = fields.Selection([('depressed', 'depressed'), ('manic', 'manic')], 'Psychiatry: Mood')
    # sign_psychiatry_short_term_memory = fields.Char(string="Short term memory")
    # sign_psychiatry_long_term_memory = fields.Char(string="Long term memory")
    # sign_psychiatry_concentration = fields.Char(string="Concentration")
    # sign_psychiatry_thought = fields.Selection([('pressure', 'pressure'), ('poverty', 'poverty'),
    #                                             ('tangential thinking', 'tangential thinking'),
    #                                             ('flight of ideas', 'flight of ideas'), ('titubation', 'titubation')],
    #                                            'Thought')
    # sign_psychiatry_tics = fields.Boolean(string="Tics")
    # sign_psychiatry_others = fields.Text(string="Sign Psychiatry: Others")

    # # Past medical history
    # past_medical_history_sickle_cell = fields.Boolean(string="Sickle cell")
    # past_medical_history_diabetes = fields.Boolean(string="Diabetes")
    # past_medical_history_hypertension = fields.Boolean(string="Hypertension")
    # past_medical_history_epilepsy = fields.Boolean(string="Epilepsy")
    # past_medical_history_dyslipidemia = fields.Boolean(string="Dyslipidemia")
    # past_medical_history_tia = fields.Boolean(string="TIA")
    # past_medical_history_stroke = fields.Boolean(string="Stroke")
    # past_medical_history_myocardial_infarction = fields.Boolean(string="Myocardial Infarction")
    # past_medical_history_dvt = fields.Boolean(string="DVT")
    # past_medical_history_surgeries = fields.Text(string="Surgeries")
    # past_medical_history_asthma = fields.Boolean(string="Asthma")
    # past_medical_history_copd = fields.Boolean(string="COPD")
    # past_medical_history_immunization = fields.Selection([('fully', 'fully'), ('not up-to-date', 'not up-to-date'),
    #                                                       ('unimmunized', 'unimmunized')], 'Immunization')
    # past_medical_history_developmental_milestones = fields.Selection([('normal', 'normal'), ('delayed', 'delayed')],
    #                                                                  'Developmental milestones')
    # past_medical_history_others = fields.Text(string="past medical history: Others")

    # # Lifestyle
    # lifestyle_alcohol = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Alcohol')
    # lifestyle_alcohol_yes = fields.Char(string="Alchohol: If Yes")
    # lifestyle_tobacco = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Tobacco')
    # lifestyle_tobacco_yes = fields.Char(string="Tobacco: If Yes")
    # lifestyle_recreational_drugs = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Recreational drugs')
    # lifestyle_recreational_drugs_yes = fields.Char(string="drugs: If Yes")
    # lifestyle_sex = fields.Selection([('safe', 'safe'), ('unsafe', 'unsafe')], 'lifestyle: Sex')
    # lifestyle_coffee = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Coffee')
    # lifestyle_coffee_yes = fields.Char(string="Coffee: If Yes")
    # lifestyle_other_risky_behaviour = fields.Text(string="Other risky behaviours")
    # lifestyle_strict_vegetarian = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Strict vegetarian')
    # lifestyle_exercise = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Exercise')
    # lifestyle_exercise_yes = fields.Char(string="Exercise: If Yes")

    # # Medication history
    # # medication_history_current_medications = fields.One2many('oeha.currentmedication', 'evaluation_id',
    # #                                                          string="Medical History: Current Medications")
    # medication_history_drug_allergies = fields.Text(string="Drug allergies")

    # # Gynaecological history
    # gynaecology_last_menses = fields.Date(string="Last menses")
    # gynaecology_amenorrhea = fields.Selection([('primary', 'primary'), ('secondary', 'secondary')],
    #                                           'Gynaecology: Amenorrhea')
    # gynaecology_dysmenorrhea = fields.Boolean(string="Gynaecology: Dysmenorrhea")
    # gynaecology_menorrhagia = fields.Boolean(string="Gynaecology: Menorrhagia")
    # gynaecology_metromenorrhagia = fields.Boolean(string="Metromenorrhagia")
    # gynaecology_infertility = fields.Selection([('primary', 'primary'), ('secondary', 'secondary')], 'Infertility')
    # gynaecology_subfertility = fields.Boolean(string="Subfertility")

    
    # Nursing Assessment

    # nurse_assess_system_nutrition_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
    #                                                     domain=[('system_type', '=', 'Nutrition')],
    #                                                     string="Nutrition Line")

    # nurse_assess_system_skin_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
    #                                                domain=[('system_type', '=', 'Skin')], string="Skin Line")

    # nurse_assess_system_neuro_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
    #                                                 domain=[('system_type', '=', 'Neuro')], string="Neuro Line")

    # nurse_assess_system_pain_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
    #                                                domain=[('system_type', '=', 'Pain')], string="Pain/Discomfort Line")

    # nurse_assess_system_respiration_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
    #                                                       domain=[('system_type', '=', 'Respiration')],
    #                                                       string="Respiration Line")

    # nurse_assess_system_cardiovascular_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
    #                                                          domain=[('system_type', '=', 'Cardiovascular')],
    #                                                          string="Cardiovascular Line")

    # nurse_assess_system_gastro_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
    #                                                  domain=[('system_type', '=', 'Gastrointestinal')],
    #                                                  string="Gastro Intestinal Line")

    # nurse_assess_system_genitourinary_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
    #                                                         domain=[('system_type', '=', 'Genitourinary')],
    #                                                         string="Genitourinary Line")

    # nurse_assess_system_musculoskeletal_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
    #                                                           domain=[('system_type', '=', 'Musculoskeletal')],
    #                                                           string="Musculoskeletal Line")

    # nurse_assess_system_system_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
    #                                                  domain=[('system_type', '=', 'Sensory')], string="Sensory Line")

    # nurse_assess_system_note_ids = fields.One2many('oeha.nurse.assessment', 'evaluation_id',
    #
    
    # indication_discharge = fields.Many2many(comodel_name='oeh.medical.pathology',
    #                                         relation="med_eval_indication_discharge",
    #                                         column1="evaluation_id",
    #                                         column2="discharge_id",
    #                                         string="Diagnosis")
    # procedures_performed_discharge = fields.One2many(related='procedures_performed',
    #                                                  string="Treatment/Procedures Performed", readonly=1)
    # treatments_administered_discharge = fields.One2many(related='treatments_administered',
    #                                                     string="Administered medications", readonly=1)
    # last_vital_signs = fields.One2many('oeha.last_vitalsigns', 'evaluation_id', string='Vital signs')
    # todays_labtests = fields.One2many('oeh.medical.lab.test', 'evaluation_id', string='Lab Tests')
    # prescribed_medication = fields.One2many('oeh.medical.prescription', 'evaluation_id', string="Prescribed medication")
    # prescribed_medication_lines = fields.One2many('oeh.medical.prescription.line', 'evaluation_id',
    #                                               string="Prescribed medication lines")

    ########## new field to decide whether patient is NEW patient or existing #########
    
    #  compute=_compute_patient_status)
    # chart_review = fields.One2many('oeha.chart.review', 'evaluation_id', string='Chart Review By')

    ######### new current medication fields #######
    # allergies_new = fields.Selection(ALLERGIES_SELECTION, 'Allergies?')
    # medication_allergies_ids = fields.One2many('oeha.evaluation.medication.allergies', 'evaluation_id',
    #                                            string='Medical/Allergies List')
    # patient_last_evaluation_id = fields.Many2one('patient.medical.evaluation', string='Last Evaluation ID')
    # latest_medication_allergies_ids = fields.One2many('oeha.evaluation.medication.allergies',
    #                                                   related='patient_last_evaluation_id.medication_allergies_ids',
    #                                                   string="Medical/Allergies")
    # latest_currentmedications = fields.One2many('oeha.currentmedication',
    #                                             related='patient_last_evaluation_id.currentmedications',
    #                                             string="Current Medication")
    # latest_other_medications = fields.Text(string="List of Other medications",
    #                                        related='patient_last_evaluation_id.other_medications')
    ########################FLUID BALANCE################################
    # fluid_input_ids = fields.One2many(
    #     'oeha.fluidbalance',
    #     'evaluation_id',
    #     'Fluid Input Balance',
    #     domain=[('input_output_type', '=', 'input')]
    # )
    # fluid_output_ids = fields.One2many(
    #     'oeha.fluidbalance',
    #     'evaluation_id',
    #     'Fluid Output Balance',
    #     domain=[('input_output_type', '=', 'output')]
    # )
    # fluid_output_amount = fields.Float(
    #     "Fluid Output Amount",
    #     store=True,
    #     compute="compute_input_output_total"
    # )
    # fluid_input_amount = fields.Float(
    #     "Fluid Input Amount",
    #     store=True,
    #     compute="compute_input_output_total"
    # )
    # balance_amount = fields.Float(
    #     "Balance Amount",
    #     store=True,
    #     compute="compute_balance_total"
    # )

    