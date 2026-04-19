# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime, date, time
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payslip_threshold_date = fields.Date(string='Payslip Threshold Date', compute="_compute_threshold_start_date", inverse="_inverse_threshold_start_date_str")
    payslip_threshold_date_str = fields.Char(string='Payslip Threshold Date in String', config_parameter='payroll_extension.payslip_threshold_date')
    
    @api.depends('payslip_threshold_date_str')
    def _compute_threshold_start_date(self):
        """ As config_parameters does not accept Date field,
            we get the date back from the Char config field, to ease the configuration in config panel """
        for setting in self:
            setting.payslip_threshold_date = fields.Date.to_date(setting.payslip_threshold_date_str)

    def _inverse_threshold_start_date_str(self):
        """ As config_parameters does not accept Date field,
            we store the date formated string into a Char config field """
        for setting in self:
            if setting.payslip_threshold_date:
                setting.payslip_threshold_date_str = fields.Date.to_string(setting.payslip_threshold_date)
