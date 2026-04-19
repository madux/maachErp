from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)



class OehMedicalAdmission(models.Model):
    _name = 'oeh.medical.admission'
    _description = 'Admissions'
    _order = "id desc"

    def _get_physicians(self):
        """Return users that are in physician role"""
        grp_physician = self.env.ref('oehealth.group_oeh_medical_physician')
        physicians = self.env['res.groups'].search([
            ('id', '=', grp_physician.id),
        ]).mapped('users')
        domains = [('id', '=', physicians.ids)]
        return domains

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
        'oeh.medical.patient', 
        string='Patient',
        required=False, 
        readonly=True, 
        states={'draft': [('readonly', False)]}
    )
    age = fields.Char(related="patient_id.age")
    sex =  fields.Selection(related='patient_id.sex')
    admittedby = fields.Many2one(
        'res.users',
        'Care Provider',
        required=False, 
        readonly=True, 
        states={'draft': [('readonly', False)]},
        domain=lambda self: self._get_physicians(),
        help= 'Care Provider who admitted the patient'
    )
    dischargedby = fields.Many2one(
        'res.users',
        'Discharged By',
        readonly=True, 
        states={'inpatient': [('readonly', False)]},
        domain=lambda self: self._get_physicians(),
        help= 'Care Provider who discharged the patient'
    )
    admission_type = fields.Selection(
        ADMISSION_TYPE, 
        'Admission Type',
        store=True,
        readonly=True,
        default='Elective',
        states={'draft': [('readonly', False)]}
    )
    admission_reason = fields.Many2one(
        'oeh.medical.pathology', 
        string='Reason for Admission',
        readonly=True,
        required=False,
        states={'draft': [('readonly', False)]}
    )
    admission_condition = fields.Text(
        string='Condition before Admission', 
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    admission_date = fields.Datetime(
        string='Admission Date', 
        readonly=True, 
        states={'draft': [('readonly', False)]}, 
        default=fields.Datetime.now()
    )
    discharge_date = fields.Datetime(
        'Discharge Date', 
        readonly=False, 
        states={'outpatient': [('readonly', True)]}
    )
    nursing_plan = fields.Text(
        'Nursing Plan', 
        readonly=False,
        states={'outpatient': [('readonly', True)]}
    )
    discharge_plan = fields.Text(
        'Discharge Plan', 
        readonly=False,
        states={'outpatient': [('readonly', True)]}
    )
    additional_info = fields.Text(
        'Additional Info', 
        readonly=False, 
        states={'outpatient': [('readonly', True)]}
    )
    room_id = fields.Many2one(
        'helpdesk.team', 
        string='Room', 
        required=False, 
        readonly=True, 
        store=True,
        domain=[ 
            ('room_type', 'in', ('Exam Room','Admission Room')),
            ('is_admittable', '=', True),
            ('status','in',('clean',)),
        ],
        help="Ensure all admission rooms are clean",
        states={'draft': [('readonly', False)]}
    )
    state = fields.Selection(
        INPATIENT_STATES, 
        'State', 
        default=lambda *a: 'draft'
    )
    evaluation_ids = fields.One2many(
        'oeh.medical.evaluation', 
        'admission_id',
        'Doctor Evaluations',
        domain=[('purpose','=','doctor_evaluation')],
    )

    nurse_assessment_ids = fields.One2many(
        'oeh.medical.evaluation', 
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
        self.patient_id.write({'state':'outpatient'})
        self.room_id.sudo().write({'status':'dirty'})

    def action_evaluation(self):
        views = self.env.ref("oehealth.oeh_medical_evaluation_view").id
        return { 
            "name": "Patient's Evaluation",
            "type": "ir.actions.act_window",
            "res_model": "oeh.medical.evaluation",
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
        views = self.env.ref("oehealth.oeh_medical_evaluation_view").id
        res_id = self.nurse_assessment_ids[0].id if self.nurse_assessment_ids else False
        return { 
            "name": "Patient's Evaluation",
            "type": "ir.actions.act_window",
            "res_model": "oeh.medical.evaluation",
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

    @api.model
    def create(self, vals):
        #check if patient is already admitted
        patient = self.env['oeh.medical.patient'].browse([int(vals.get('patient_id',0))])
        physician = self.env['res.users'].browse([int(vals.get('admittedby',0))])
        if self.search([
            ('patient_id','=', patient.id),
            ('state','in',('inpatient',))]).exists():
            raise ValidationError(
                'Patient [%s] has an active admission record.' 
                'Please discharge the patient before creating a new admission' % patient.name
            )
        #update room status 
        if 'room_id' in vals:
            room = self.env['helpdesk.team'].sudo().browse([int(vals['room_id'])])
            if room:
                room.sudo().write({'status': 'occupied'})
                self.create_or_update_ticket(patient, room, physician)
        patient.write({'state':'inpatient'})
        vals['state'] = 'inpatient'
        sequence = self.env['ir.sequence'].next_by_code('admission.no')
        vals['name'] = sequence or '/'
        return super(OehMedicalAdmission, self).create(vals)

    def write(self, vals):
        if 'room_id' in vals and self.room_id.id != vals.get('room_id',0):
        # if the room is updated, set the new room as occupied
        # if self.room_id.id != vals.get('room_id',0):
            room = self.env['helpdesk.team'].sudo().browse([int(vals['room_id'])])
            if room:
                room.sudo().write({'status': 'occupied'})
                self.create_or_update_ticket(self.patient_id.id, room, self.admittedby)      
        return super(OehMedicalAdmission, self).write(vals)
        
    
    def create_or_update_ticket(self, patient_ref, roomid, physician):
        helpdesk_obj = self.env['helpdesk.ticket']
        helpdesk_type_obj = self.env['helpdesk.ticket.type'].search(
            [('name', '=', 'Patient-centered')], limit=1)
        new_dt = fields.Datetime.now().strftime('%Y-%m-%d')
        ticketId = helpdesk_obj.search([
            ('partner_id', '=', patient_ref.partner_id.id),('create_date', '>=', new_dt)], limit=1)
        stage_id = self.env.ref('helpdesk_extension.helpdesk_stage_observation').id
        helpdesk_val = {
            'name': 'Admission Ticket for {0}'.format(patient_ref.name),
            'partner_id': patient_ref.partner_id.id,
            'email': patient_ref.email,
            'team_id': roomid.id,
            'ticket_type_id': helpdesk_type_obj.id,
            'ticket_type_categ': 'patient',
            'phone': patient_ref.phone,
            'user_id': physician.id,
            'stage_id': stage_id,
            'branch_id': self.env.user.branch_id.id,
            'description': 'Ticket for {}'.format(patient_ref.name)
        }
        helpdesk_obj.sudo().create(helpdesk_val) if not ticketId else ticketId.sudo().update({
            'team_id': roomid.id,
            'user_id': physician.id,
            'stage_id': stage_id
        })

