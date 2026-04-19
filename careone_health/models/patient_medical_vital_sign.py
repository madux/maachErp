# models/res_patient_pharmacy_history.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class VitalSigns(models.Model):
    _name = 'patient.vitalsigns'
    _description = 'Vital Signs'
 
    time = fields.Datetime(string="Time", default=fields.Datetime.now)
    temp = fields.Float(string="Temp")
    systolic = fields.Integer(string="Systolic")
    diastolic = fields.Integer(string="Diastolic")
    heart_rate = fields.Integer(string="Heart Rate")
    respiratory = fields.Integer(string="Respiratory")
    oxy_saturate = fields.Integer(string="Oxygen Saturation")
    evaluation_id = fields.Many2one('patient.medical.evaluation', string="Evaluation", ondelete='cascade')
