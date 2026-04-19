# -*- coding: utf-8 -*-

from odoo import models, fields, _

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    print_lot = fields.Boolean(string='Print Lot')