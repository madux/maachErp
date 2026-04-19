from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    appointment_feedback_form_link = fields.Char(
        string="Feedback Form Link", config_parameter="odoo_appointment_booking.appointment_feedback_form_link")
