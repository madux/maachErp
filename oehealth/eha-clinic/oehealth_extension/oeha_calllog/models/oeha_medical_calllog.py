# extension to oehealth

from odoo import api, fields, models, _
import time
import datetime

class CallLog(models.Model):
    _name = 'oeha.medical.calllog'
    _description = 'Call Logs'

    name = fields.Many2one('oeh.medical.patient', string='Patient', required=False, help="Patient Name")
    patient_id = fields.Char(string="Patient ID",related="name.identification_code",readonly=True)
    person_in_charge = fields.Many2one('res.users','Completed By', default=lambda self: self.env.user)
    call_type = fields.Selection( [('phone', 'Phone'), ('email', 'Email'),('sms','SMS'),('other','Other')],'Call Type')
    date = fields.Datetime(string="Date / Time")
    log = fields.Text(string="Call Log")