# -*- coding: utf-8 -*-

from odoo import models, fields, _

class MembershipCategory(models.Model):
    _name = 'eha.membership.category'
    _description = 'Membership Category'

    name = fields.Char(string='Name', required=False)
    categ_code = fields.Char(string='Code')
    has_discount = fields.Boolean(string='Has Discount')
    discount_qty = fields.Float(string='Discount Quantity')