from datetime import datetime, timedelta
import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)

class oehMedicalBloodPressureDiary(models.Model):
	_name = "oeh.medical.blood.pressure.diary"
	_description = "Oeh Medical blood pressure diary"
	_rec_name = "patient_id"

	patient_id = fields.Many2one('oeh.medical.patient', string="Patient ID") # 
	systolic_pressure = fields.Integer(string='Systolic Pressure', store=True)
	diastolic_pressure = fields.Integer(string='Diastolic Pressure', store=True)
	reference = fields.Char(string='Reference')
	date_of_reading = fields.Datetime('Date of Reading')


	