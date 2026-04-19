# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# Additional Model 11/09/19
class FaqCategory(models.Model):
    _name = "faq.category"
    _description = "Frequently Asked Question's Category"
    _sql_constraints = [
        (
            'uniq_category_name_foss_faq', 
            'unique (name)',
            'The category name must be unique!'
        )
    ]

    name = fields.Char(required=False)
    question_ids = fields.One2many(
        'faq.faq', 'category_id', string='Questions')
    category_field = fields.Selection([
        ('covid_19', 'Covid 19'),
        ('help_centre', 'Help Centre'),
    ], string='Field')

    @api.model
    def create(self, vals):
        vals['name'] = vals['name'].upper()
        return super(FaqCategory, self).create(vals)

    def write(self, vals):
        if vals.get("name"):
            if self.name != vals['name']:
                if self.search([('name', '=', vals['name'].upper())]):
                    raise ValidationError(
                        "Category with name %s Exists" % vals['name'])
        return super(FaqCategory, self).write(vals)
