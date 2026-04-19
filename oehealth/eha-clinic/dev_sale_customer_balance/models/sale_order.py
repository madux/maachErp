# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import fields, models


class Sale(models.Model):
    _inherit = 'sale.order'

    # partner_balance_amount = fields.Monetary(related='partner_id.credit', readonly=True, string='Balance')
    partner_balance_amount = fields.Monetary(related='partner_invoice_id.credit', readonly=True, string='Balance')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: