# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Mattobell (<http://www.mattobell.com>)
#    Copyright (C) 2010-Today OpenERP SA (<http://www.odoo.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
{
    'name' : 'Improvements on Assets Management',
    'version' : '1.0',
    'depends' : ['account_asset', 'purchase', 'account', 'om_account_asset'],
    'author' : 'Mattobell',
    'website' : 'http://www.mattobell.com',
    'description': '''
More Asset Management Features
==============================
This module is developed for asset management in terms of Additions, Maintenance, Disposals, Repairs management for assets.

    ''',
    'category' : 'Accounting & Finance',
    'sequence': 70,
    'license': 'AGPL-3',
    'data' : [
        # 'security/account_asset_security.xml',
        'security/ir.model.access.csv',
        'report/disposal_report_reg.xml',
        'report/disposal_report_view.xml',
        'wizard/invoice_disposal_view.xml',
        'wizard/ng_disposal_report_wiz_view.xml',
        'views/ng_account_asset_view.xml',
        'views/ng_account_asset_disposal_view.xml',
        'views/ng_account_asset_maintanance_view.xml',
        'views/account_asset_po_view.xml',
    ],
    'auto_install': False,
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: