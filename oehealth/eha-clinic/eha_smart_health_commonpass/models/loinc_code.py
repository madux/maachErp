# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class LoincCode(models.Model):
    _name = 'loinc.code'
    _description = "LOINC Code"

    name = fields.Char(string="Code")
    description = fields.Char(string="Description")
    eha_test_type_ids = fields.Many2many(comodel_name="oeh.medical.labtest.types", string="EHA Test Types")
