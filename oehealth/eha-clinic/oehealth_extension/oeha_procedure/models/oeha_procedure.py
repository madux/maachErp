from odoo import api, fields, models, _


class OeHealthMedicalProcedure(models.Model):
    _name = 'oeh.medical.procedure'
    _description='Medical Procedures'    

    code = fields.Char(string='Code', required=False, size=128)
    name = fields.Text(string='Procedure')