# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = "pos.config"

    allow_expiry_warning = fields.Boolean(string="Allow Lot Expiry Warning")
    restrict_creating_lot = fields.Boolean(string="Restrict User from Creating New Lot")
