# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    lab_test_account = fields.Many2one('account.account', string='LabTest Account', config_parameter='oeh.default_lab_test_account')
