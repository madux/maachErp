from odoo import fields, models


class ResumeLine(models.Model):
    _name = 'hr.applicant.resume.line'
    _description = "Resumé line of an applicant"
    _order = "line_type_id, date_end desc, date_start desc"

    hr_applicant_id = fields.Many2one('hr.applicant', required=False, ondelete='cascade')
    name = fields.Char(required=False)
    date_start = fields.Date(required=False)
    date_end = fields.Date()
    description = fields.Text(string="Description")
    line_type_id = fields.Many2one('hr.resume.line.type', string="Type")

    # Used to apply specific template on a line
    display_type = fields.Selection([('classic', 'Classic')], string="Display Type", default='classic')

    _sql_constraints = [
        ('date_check', 'CHECK (date_start <= date_end)', "The start date must be anterior to the end date."),
    ]
