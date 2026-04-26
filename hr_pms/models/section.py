from odoo import models, fields, api, _
from datetime import datetime, date 
from odoo.exceptions import ValidationError


class PmsSection(models.Model):
    _name = "pms.section"
    _order = "create_date desc"
    _description = "PMS section"

    """A configuration is made on the section config side. 
    I.e create a section, assign the sections to a specific 
    job category. e.g SNR MGT, MID MGT, JR MGT"""

    name = fields.Char(
        string="Section Name", 
        required=True)

    min_line_number = fields.Integer(
        string="Minimum Number of Input",
        default=5
        )
    max_line_number = fields.Integer(
        string="Maximum Number of Input",
        default=7
        )
     
    type_of_section = fields.Selection([
        ('KRA', 'KRA'),
        ('LC', 'Leadership Competence'),
        ('FC', 'Functional Competence'),
        ], string="Type of Section", 
        default = "", 
        readonly=False,
        required=False,
        )
    pms_category_id = fields.Many2one(
        'pms.category',
        string="Category"
    ) 
    section_avg_scale = fields.Integer(
        string='Section Scale', 
        required=True,
        help="Used to set default scale",
        store=True,
        )
    input_weightage = fields.Float(
        string='Weightage (100%)', 
        default=100,
        help="Used to set default weight for appraisee",
        store=True,
        compute="compute_section_weight"
        )
        
    section_line_ids = fields.One2many(
        "pms.section.line",
        "section_id",
        string="Section Lines"
    )
    # consider removing or make invisible N/B not to be used
    weighted_score = fields.Integer(
        string='Section Weighted', 
        required=False,
        )
    
    # @api.constrains('section_line_ids')
    # def _check_lines(self):
    #     """Checks if no section line is added and max line is less than 1"""
    #     if not self.mapped('section_line_ids') and self.max_line_number < 1:
    #         raise ValidationError(
    #             'You must provide the lines or set the maximum number to above 0'
    #             )
    #     if self.weighted_score < 1:
    #         raise ValidationError(
    #             """Section weight must be set above 0%""")
    
    @api.onchange('min_line_number', 'max_line_number')
    def onchange_min_max_limit(self):
        if self.min_line_number > self.max_line_number:
            self.max_line_number = 7
            self.min_line_number = 5
            message = {
                'title': 'Invalid',
                'message': 'Minimum limit must not be greater than Maximum limit'
            }
            return {'warning': message}
    
    @api.depends('section_line_ids')
    def compute_section_weight(self):
        """
        If section_line_ids, the system should determine 
        and divide 100% by the number of lines added
        """
        if self.section_line_ids:
            numb_of_lines = len(self.section_line_ids) # eg 4
            self.input_weightage = 100 / numb_of_lines if numb_of_lines > 0 else 100 # safe eva
        else:
            self.input_weightage = 100

    