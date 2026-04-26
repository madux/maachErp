from odoo import models, fields, api


class AssessmentDescription(models.Model):
    _name = "assessment.description"
    _description= "Used to store config assessment lines"

    name = fields.Char(
        string='name', 
        )
    desc = fields.Char(
        string='Description', 
        )
    type = fields.Selection([
        ('current', 'Current'),
        ('potential', 'Potential'),
        ('Other', 'Other'),
        ], string="type", default = "", required=True)
    