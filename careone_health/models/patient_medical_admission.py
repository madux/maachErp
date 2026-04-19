# models/res_patient_pharmacy_history.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

# models/pharmacy_allergy.py
class PatientMedicalAdmission(models.Model):
    _name = 'patient.medical.admission'
    _description = 'Patient admission'
    
    ADMISSION_TYPE = [
        ('Elective', 'Elective'),
        ('Urgent', 'Urgent'),
        ('Emergency', 'Emergency'),
        ('Other', 'Other'),
    ]

    INPATIENT_STATES = [
        ('draft', 'Draft'),
        ('inpatient', 'In Patient'),
        ('outpatient', 'Out Patient')
    ]

    name = fields.Char(
        'Admission #', 
        size=128, 
        readonly=True, 
        default=lambda *a: '/'
    )
    patient_id = fields.Many2one(
        'res.partner', 
        string='Patient',
        required=False, 
        readonly=True,
        domain="[('is_patient', '=', True)]",
        
    )
    age = fields.Char(related="patient_id.age")
    sex =  fields.Selection(related='patient_id.gender')
    admittedby = fields.Many2one(
        'res.users',
        'Care Provider',
        required=False, 
        readonly=True, 
        # domain=lambda self: self._get_physicians(),
        help= 'Care Provider who admitted the patient'
    )
    dischargedby = fields.Many2one(
        'res.users',
        'Discharged By',
        readonly=True, 
        # domain=lambda self: self._get_physicians(),
        help= 'Care Provider who discharged the patient'
    )
    admission_type = fields.Selection(
        ADMISSION_TYPE, 
        'Admission Type',
        store=True,
        readonly=True,
        default='Elective',
        
    ) 
    admission_reason = fields.Text(
        string='Reason for Admission',
        readonly=False,
        required=False,
        
    )
    admission_condition = fields.Text(
        string='Condition before Admission', 
        readonly=False,
        
    )
    admission_date = fields.Datetime(
        string='Admission Date', 
        readonly=True, 
        default=fields.Datetime.now()
    )
    discharge_date = fields.Datetime(
        'Discharge Date', 
        readonly=False, 
        
    )
    nursing_plan = fields.Text(
        'Nursing Plan', 
        readonly=False,
        
    )
    discharge_plan = fields.Text(
        'Discharge Plan', 
        readonly=False,
        
    )
    additional_info = fields.Text(
        'Additional Info', 
        readonly=False, 
        
    )
    # room_id = fields.Many2one(
    #     'helpdesk.team', 
    #     string='Room', 
    #     required=False, 
    #     readonly=True, 
    #     store=True,
    #     domain=[ 
    #         ('room_type', 'in', ('Exam Room','Admission Room')),
    #         ('is_admittable', '=', True),
    #         ('status','in',('clean',)),
    #     ],
    #     help="Ensure all admission rooms are clean",
    #     
    # )
    room_id = fields.Char(
        string='Room', 
        required=True, 
        readonly=False, 
        store=True,
        help="Ensure all admission rooms are clean",
        
    )
    state = fields.Selection(
        INPATIENT_STATES, 
        'State', 
        default=lambda *a: 'draft'
    )
    evaluation_ids = fields.One2many(
        'patient.medical.evaluation', 
        'admission_id',
        'Doctor Evaluations',
        domain=[('purpose','=','doctor_evaluation')],
    )

    nurse_assessment_ids = fields.One2many(
        'patient.medical.evaluation', 
        'admission_id',
        'Nurse Assessments',
        domain=[('purpose','=','nurse_assessment')],
    )

    def action_discharge(self):
        '''Discharge a patient.
        Discharging a patient should set the room to dirty.
        '''
        discharge_date = self.discharge_date or fields.datetime.now()
        self.write(
            {'state':'outpatient','discharge_date': discharge_date}
        )
        # self.patient_id.write({'state':'outpatient'})
        # self.room_id.sudo().write({'status':'dirty'})

    def action_evaluation(self):
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
                "default_admission_id": self.id,
                "default_patient": self.patient_id.id,
                "default_evaluation_type": "New Complaint",
                "default_purpose": "doctor_evaluation",
                "default_vitalsigns": [
                (0,0,
                    {
                        'time': v.time,
                        'temp': v.temp,
                        'systolic': v.systolic,
                        'diastolic': v.diastolic,
                        'heart_rate': v.heart_rate,
                        'respiratory': v.respiratory,
                        'oxy_saturate': v.oxy_saturate,
                    }
                ) for v in self.nurse_assessment_ids[0].mapped('vitalsigns')] if self.nurse_assessment_ids else False
            }
        }

    def action_nurse_assessment(self):
        views = self.env.ref("careone_health.view_patient_medical_evaluation_form").id
        res_id = self.nurse_assessment_ids[0].id if self.nurse_assessment_ids else False
        return { 
            "name": "Patient's Evaluation",
            "type": "ir.actions.act_window",
            "res_model": "patient.medical.evaluation",
            "view_type": "form",
            "view_form": "form",
            "views": [(views, 'form')],
            "target": "new",
            "res_id": res_id,
            "context": {
                "default_admission_id": self.id,
                "default_patient": self.patient_id.id,
                "default_evaluation_type": "New Complaint",
                "default_purpose": "nurse_assessment",
            }
        }