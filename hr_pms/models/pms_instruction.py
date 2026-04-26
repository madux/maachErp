from odoo import models, fields, api, _
from datetime import datetime, date 


class PmsInstruction(models.Model):
    _name = "pms.instruction"
    _description = "PMS instruction: table to hold manuals andd instructions"

    name = fields.Text(
        string="Instruction", 
        required=True)
    description = fields.Text(
        string="description", 
        required=True)
    