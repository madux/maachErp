from odoo import models, fields, api, _
from datetime import datetime, date 
from odoo.exceptions import ValidationError


class PMS_Kba_description(models.Model):
    _name = "kba.descriptions"

    name = fields.Text(
        string="KBA", 
        required=True)

    section_line_id = fields.Many2one(
        'pms.section.line', 
        string="Section Line ID"
        )
    
    pms_section_line_id = fields.Many2one(
        'pms.department.section.line', 
        string="PMS Section Line ID"
        )


class PMS_SectionLine(models.Model):
    _name = "pms.section.line"
    _description= "Section lines"

    name = fields.Char(
        string="Title", 
        required=True)
    description = fields.Char(
        string="KBA Description", 
        required=False)
    is_required = fields.Boolean(
        string="Is required", 
        default=False
        )

    section_id = fields.Many2one(
        'pms.section', 
        string="Section ID"
        )
    
    kba_description_ids = fields.One2many(
        'kba.descriptions',
        'section_line_id',
        string="KBA Description",)
      