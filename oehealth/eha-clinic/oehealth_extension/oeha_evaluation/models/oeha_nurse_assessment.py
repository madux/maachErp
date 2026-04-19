from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


 # NURSE_ASSESSMENT    
class OehaNurseAssessment(models.Model):
    _name = "oeha.nurse.assessment"
    _description = "ona"

    RESPIRATION_TYPE = [
        ('unlabored', 'Unlabored'),
        ('labored', 'Labored'),
        ('Regular', 'Regular'),
        ('Irregular', 'Irregular'),
          
    ]
    # Nursing Assessment
    # system type field is used to determine the systems to display
    # system_type = fields.Char('System Type', default="Nutrition")
    evaluation_id = fields.Many2one(
        'oeh.medical.evaluation', 
        'Evaluation', 
        ondelete='cascade', 
        index=True
    )
    system_type = fields.Selection(
        [('Nutrition','Nutrition'), ('output','Output'),
        ('Skin','Skin'), ('Neuro','Neuro'),
        ('Pain','Pain'), ('output','Output'),
        ('Respiration','Respiration'), ('Gastrointestinal','Gastrointestinal'),
        ('Cardiovascular','Cardiovascular'), ('Genitourinary','Genitourinary'),
        ('Sensory','Sensory'), ('Musculoskeletal','Musculoskeletal'),
        ('Notes','Notes'), ('Notes','Notes'),
        ],
        'Nurse Assessment Type',
    )

    # Nutrition
    diet = fields.Selection([('regular', 'Regular'), ('soft', 'Soft'),('pureed', 'Pureed')], 'Diet')
    recent_weight_change = fields.Selection([('no', 'No'),('yes', 'Yes')],default="no", string="Recent weight Change")
    conditions_affecting_ecs = fields.Selection([('no', 'No'),('yes', 'Yes')], default="no",string="Condition affecting eating, chewing and swallowing")
    mucous_membranes = fields.Selection( [('moist', 'Moist'), ('dry', 'Dry')],'Mucous Membranes')    

    # skin
    skin = fields.Selection( [('normal', 'Normal'), ('pale', 'Pale'),('red', 'Red'),
    ('rash', 'Rash'),('bruise','Bruise'),('breakdown','Skinbreakdown')],'Skin')
    skin_intact = fields.Selection( [('no', 'No'), ('yes', 'Yes')],default="no", string="Skin intact")
    special_care = fields.Boolean(string="Special care required")
    wound_assessment = fields.Text(string='Wound Assessment', required=False)

    # neuro Seizure /Tremors /Fainting
    level_of_consciousness = fields.Selection( [
        ('alert', 'Alert'), ('altered', 'Altered'),
        ('Seizure', 'Seizure'), ('Tremors', 'Tremors'),
        ('Fainting', 'Fainting'), ('Fainting', 'Fainting')],
        'Level of consciousness')
        
    difficulty_in_orientation = fields.Selection([('no', 'No'), ('yes', 'Yes')],
    default="no",string="Difficulty in orientation")
    difficulty_in_orientation_other = fields.Text(string='Explain: ')

    impaired_decision_making = fields.Selection([('no', 'No'), ('yes', 'Yes')],
    default="no", string="Impaired decision making")
    sleep_aids = fields.Selection([('no', 'No'), ('yes', 'Yes')],
    default="no", string="Sleep aids")


    sensation = fields.Selection( [('intact', 'Intact'), ('diminished', 'Diminished'), ('absent', 'Absent')],'Intact / Diminished / Absent')
    memory_deficit = fields.Boolean(string="Memory Deficit")

    # pain / discomfort
    pain = fields.Selection([('no', 'No'), ('yes', 'Yes')], default="no",
    string="Discomfort/Pain")
    pain_score = fields.Selection(
        [
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
        ],string= 'Pain Score', default=0)
    location = fields.Char(string='Pain/Discomfort Location')
    frequency = fields.Char(string='Pain/Discomfort Frequency')
    duration = fields.Char(string='Pain/Discomfort Duration')
    treatment = fields.Text(string='Treatment (if any)')

    # respiration
    respirations = fields.Selection(RESPIRATION_TYPE,'Respirations')
    breath_sounds = fields.Selection( [('clear', 'Clear'), ('wheezes', 'Wheezes'),('crackles','Crackles')],'Breath sounds')
    shortness_of_breath = fields.Selection([('no', 'No'), ('yes', 'Yes')],
    default="no", string="Shortness of breath")  
    shortness_of_breath_trigger = fields.Text('Trigger')
    cough = fields.Selection([('no', 'No'), ('yes', 'Yes')], default="no", string="Cough")
    cough_type = fields.Selection( [('productive', 'Productive'), ('non_productive', 'Non Productive')],
    'Productive / Non Productive') 

    respiratory_treatment = fields.Selection( [('none', 'None'), ('oxygen', 'Oxygen'),
    ('nebulizer','Nebulizer'),('cpap','CPAP'),('bipap','BIPAP')],'Respiratory Treatments')
 
    history = fields.Selection( [('normal', 'Normal'), ('arrhythmia', 'Arrhythmia'), ('hypertension','Hypertension'),
    ('hypotension','Hypotension'),('dizziness','Dizziness')],'History')
    pulse = fields.Selection( [('regular', 'Regular'), ('irregular', 'Irregular')],'Pulse')
    edema = fields.Selection([('no', 'No'), ('yes', 'Yes')],default="no", string="Edema")
    pitting = fields.Selection([('no', 'No'), ('yes', 'Yes')], default="no",string="Pitting") 
    pitting_location = fields.Text('Please Specify Location')  
    explain_edema = fields.Text('Explain edema if any')
    chest_pain = fields.Boolean(string="Chest pain")
    explain_chest_pain = fields.Text('Explain chest pain if any')

    # gastro intestinal
    gastrointestinal_bleeding = fields.Selection([('no', 'No'), ('yes', 'Yes')], default="no",string="Bleeding")

    gastrointestinal_diarrhea = fields.Selection([('no', 'No'), ('yes', 'Yes')], default="no",string="Gastro: Diarrhea")
    gastrointestinal_constipation = fields.Selection([('no', 'No'), ('yes', 'Yes')], default="no",string="Gastro: Constipation")

    gastrointestinal_vomiting = fields.Selection([('no', 'No'), ('yes', 'Yes')], default="no",string="Gastro: Vomiting")

    gastrointestinal_nausea = fields.Selection([('no', 'No'), ('yes', 'Yes')], default="no",string="Gastro: Nausea")
    gastrointestinal_gastrostomy = fields.Selection([('no', 'No'), ('yes', 'Yes')], default="no",string="Gastro: Gastrostomy")

    gastrointestinal_enteral_tube = fields.Selection([('no', 'No'), ('yes', 'Yes')],default="no", string="Enteral tube")
    gastrointestinal_abdominal_pain = fields.Selection([('no', 'No'), ('yes', 'Yes')], default="no",string="Abdominal Pain")


    change_in_appetite = fields.Selection( [('no', 'No'), ('yes', 'Yes')],'Change in appetite')
    explain_change_in_appetite = fields.Text('Explain change in appetite')# visible on change_in_appetite,placeholder Increased or Descreased
    bowel_sounds = fields.Selection([('no', 'No'), ('yes', 'Yes')], default="no",string="Gastro: Bowel sounds")
    bowel_movement = fields.Selection( [('no', 'No'), ('yes', 'Yes')],default="no",string='Bowel movement')


    # genitourinary
    bladder_control = fields.Selection( [('full_control', 'Full Control'),
     ('incontinence', 'Incontinence')],'Bladder Control')
    bladder_frequency = fields.Char(string='Frequency')
    blood_in_urine = fields.Selection( [('no', 'No'), ('yes', 'Yes')],default="no",string='Blood in urine')
    difficulty_urinating = fields.Selection( [('no', 'No'), ('yes', 'Yes')],default="no",string="Difficulty urinating")

    nocturnia = fields.Selection( [('no', 'No'), ('yes', 'Yes')],default="no", string="Nocturnia")
    indwelling_catheter = fields.Selection( [('no', 'No'), ('yes', 'Yes')],default="no",string="Indwelling catheter")


    # musculoskeletal
    mobility = fields.Selection([('normal', 'Normal'), ('impaired', 'Impaired')], string='Mobility')
    # assistive_devices = fields.Selection(
    #     [('walking_stick', 'Walking Stick'), ('wheelchair', 'Wheel Chair'), ('stretcher', 'Stretcher')],
    #     string="Corrective Devices")
    assistive_devices = fields.Selection( [('no', 'No'), ('yes', 'Yes')],default="no", string="Assistive Device")
    range_of_motion = fields.Selection( [('full', 'Full'), ('limited', 'Limited')],string='Range of motion')
    activities_of_daily = fields.Selection( [('self', 'Self'), ('assist', 'Assist'),
    ('total','Total')],'Activities of daily living')

    # related to activities of daily(Visible if selected)
    eating_activities = fields.Char('Eating')
    bathing_activities = fields.Char('Bathing')
    dressing_activities = fields.Char('Dressing')

    # sensory
    vision = fields.Selection( [('normal', 'Normal'), ('impaired', 'Impaired')],default="normal",string='Vision')
    corrective_device = fields.Char('Corrective device')
    hearing = fields.Selection( [('normal', 'Normal'), ('impaired', 'Impaired')],default="normal",string='Hearing')
    hearing_aid = fields.Selection( [('no', 'No'), ('yes', 'Yes')],string='Hearing Aid')  

    # nursing assessment notes

    nursing_assessment_notes = fields.Text(string="Notes")
    state = fields.Selection([('draft', 'Draft'), ('Completed', 'Completed')],default="draft", string='Status')
    user_id = fields.Many2one('res.users', string="Completed By", states={'Completed': [('invisible', False)]})  
    position = fields.Char(string="Position", compute="get_related_position")

    patient = fields.Many2one('oeh.medical.patient', 'Patient', readonly=False, store=True)  
    completed_date = fields.Datetime(string='Date Completed')
    assessment_date = fields.Datetime(string='Assessment Date',default=fields.Datetime.now, required=False)
    patient_id = fields.Char(string='Patient ID', related='patient.identification_code')
    sequence = fields.Integer(string='No:')

    
    @api.depends('user_id')
    def get_related_position(self):
        user_emp_record = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        for rec in self:
            if rec.user_id:
                rec.position = user_emp_record.job_id.name if user_emp_record.job_id else []
            else:
                rec.position = False
    
    def complete_Assessment(self):
        self.write({
            'user_id': self.env.user.id,
            'state': 'Completed',
            # 'position': self.get_related_position(),
            'completed_date': datetime.now()
            })

    def set_draft(self):
        self.state = "draft" 

    @api.model
    def create(self,vals):
         
        vals['user_id'] = self.env.user.id,
        vals['state'] = 'Completed'
        vals['patient'] = vals.get('patient')
        vals['completed_date'] = datetime.now()
        res = super(OehaNurseAssessment, self).create(vals)
        return res

    
    def unlink(self):
        for record in self.filtered(lambda record: record.state not in ['draft']):
            '''
            Only system admin can delete this record from the DB once create.
            Go to oehealth--> Nurse Assessment Menu (Visible to only users with admin right)
            '''

            if not (self.env['res.users'].browse([self.env.uid]).has_group('base.group_system')) and (self.state == "Completed"):
                raise ValidationError(_('You can not delete an assessment which is not in "Draft" state !!'))
        return super(OehaNurseAssessment, self).unlink()