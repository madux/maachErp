from odoo import models, fields, api


class OTPLog(models.Model):
    _name = 'otp.log'
    _description = 'OTP Log'

    otp = fields.Char(string="otp", required=False)
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone Number")
    timestamp = fields.Datetime(string="OTP timestamp", default=lambda self: fields.Datetime.now())
