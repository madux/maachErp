# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
import logging

#Get the logger
_logger = logging.getLogger(__name__)


class ServerActions(models.Model):
    """ Add sms option in server actions. """
    _name = 'ir.actions.server'
    _description = 'Server Action'
    _inherit = ['ir.actions.server']

    state = fields.Selection(selection_add=[('sms', 'Send SMS')])
    # Template
    sms_message = fields.Text('SMS Meesage')
