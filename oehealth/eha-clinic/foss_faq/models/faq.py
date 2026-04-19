# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from urllib.parse import urlencode


class FaqFaq(models.Model):
    _name = "faq.faq"
    _description = "Frequently Asked Questions"
    _order = 'sequence,id'

    sequence = fields.Integer(
        help="The order in which the FAQ will display on the website")
    active = fields.Boolean(string="Active", default=True)
    name = fields.Text(string="Questions")
    solution = fields.Html(string="Solution")
    attachment = fields.Binary(string="Attachment", store=True)
    filename = fields.Char(string="Filename")
    tag_ids = fields.Many2many('faq.tag', string='Tags')
    category_id = fields.Many2one('faq.category', string='Category')
    video = fields.Char()

    def _get_faq_image_url(self):
        for record in self:
            image_url = ""
            if not record.attachment:
                return image_url
            base_url = self.env["ir.config_parameter"].sudo(
            ).get_param("web.base.url")
            parameters = {
                "id": record.id,
                "field": "attachment",
                "model": self._name
            }
            image_url = f"{base_url}/web/image?{urlencode(parameters)}"
            return image_url
