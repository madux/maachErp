# models/res_patient_pharmacy_history.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

# models/pharmacy_allergy.py
class PatientMedicalHistory(models.Model):
    _name = 'patient.medical.history'
    _description = 'Patient History'
    
    name = fields.Char(string='Allergy', required=True)
    severity = fields.Selection([
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ], string='Severity')
    description = fields.Text(string='Description')
    evaluation_ids = fields.Many2many("patient.medical.evaluation", string="Medical Evaluation")
    patient_id = fields.Many2one("res.partner", string="Patient ID")
 