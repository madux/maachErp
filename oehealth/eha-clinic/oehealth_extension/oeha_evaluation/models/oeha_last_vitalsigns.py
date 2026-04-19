from odoo import api, fields, models, _
from odoo.exceptions import UserError

class LastVitalSignsinVisitSummary(models.Model):
    _name = 'oeha.last_vitalsigns'
    _description = 'Display Last Vital Signs in Visit Summary Tab'

    time = fields.Datetime(string="Time", default=fields.Datetime.now)
    temp = fields.Float(string="Temp")
    systolic = fields.Integer(string="Systolic")
    diastolic = fields.Integer(string="Diastolic")
    heart_rate = fields.Integer(string="Heart Rate")
    respiratory = fields.Integer(string="Respiratory")
    oxy_saturate = fields.Integer(string="Oxygen Saturation")
    evaluation_id = fields.Many2one('oeh.medical.evaluation', string="Evaluation", ondelete='cascade')