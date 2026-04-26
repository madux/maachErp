from odoo import models, fields, api, _
from datetime import datetime, date 
from odoo.exceptions import ValidationError


class PMS_Year(models.Model):
    _name = "pms.year"
    _description= "Holds the period of the Appraisal"

    name = fields.Char(
        string="Name", 
        required=True)
    date_from = fields.Date(
        string="Date From", 
        required=True, 
        readonly=False, 
        store=True)
    date_end = fields.Date(
        string="Date End", 
        readonly=False
        )
    
    @api.constrains('date_end')
    def _check_lines(self):
        if self.date_from and self.date_end:
            if self.date_end < self.date_from:
                raise ValidationError(
                    'End date must be greater than start date'
                    )

         