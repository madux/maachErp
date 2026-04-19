# oeha_sample_type

from odoo import api, exceptions, fields, models
from odoo.tools.translate import _


class OehaSample(models.Model): 
    _name = "oeha.sample.type" 
    _description = "Model for Sample type" 

    name = fields.Char(string="Sample") 
    related_test_type = fields.Many2many('oeh.medical.labtest.types', string='Related Lab test') 
