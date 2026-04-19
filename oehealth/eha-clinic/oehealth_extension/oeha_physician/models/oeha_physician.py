from odoo import api, fields, models, _


class OeHealthPhysicianExtension(models.Model):
    _name = "oeh.medical.physician"
    _description = "Information about the doctor"
    _inherit = ['oeh.medical.physician', 'mail.thread']
