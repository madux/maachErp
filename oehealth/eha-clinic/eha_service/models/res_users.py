# -*- coding: utf-8 -*-

from odoo import models, fields


class resUsers(models.Model):
    _inherit = 'res.users'

    simplybook_performer_id = fields.Char(string="Simplybook Performer ID")
     