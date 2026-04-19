# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.http_routing.models.ir_http import slug


# Additional Model 11/09/19
class FaqTag(models.Model):
    _name = "faq.tag"
    _description = "Frequently Asked Question's Tag"

    name = fields.Char(required=False)
    color = fields.Integer("Color Index")
    url_slug = fields.Char('Slug', compute="_compute_slug", store=True)

    @api.model
    def create(self, vals):
        vals['name'] = vals['name'].upper()
        return super(FaqTag, self).create(vals)

    def write(self, vals):
        if 'name' in vals and self.name != vals['name']:
            if self.search([('name', '=', vals['name'].upper())]):
                raise ValidationError("Tag with name %s Exists" % vals['name'])
        return super(FaqTag, self).write(vals)

    _sql_constraints = [
        ('uniq_tag_name_foss_faq', 'unique (name)', 'The tag name must be unique!')
    ]
    
    def _compute_slug(self):
        for record in self:
            record.url_slug = slug(record)
            
    def action_generate_slug(self):
        for record in self:
            return record._compute_slug()
