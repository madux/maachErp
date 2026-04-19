# -*- coding: utf-8 -*-

from odoo import models, fields, _

class EHAProductCreation(models.Model):
    _name = 'eha.asana.links'
    _description = 'EHA Asana Links'

    name = fields.Char(string='Product Name', required=False)
    url = fields.Char(string='URL', required=False)