# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api, _


class account_xls_output_wiz(models.TransientModel):
    _name = 'account.xls.output.wiz'
    _description = 'Wizard to store the Excel output'

    xls_output = fields.Binary(string='Excel Output')
    name = fields.Char(string='File Name', help='Save report as .xls format', default='Payroll_Register.xls')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
