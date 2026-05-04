# -*- coding: utf-8 -*-
{
    'name': 'Financial Report Portal',
    'version': '16.0.1.0.0',
    'summary': 'Standalone HTML financial report portal with GL, P&L, Balance Sheet, Trial Balance, Tax, Consolidated, Monthly Expense + Dashboard',
    'category': 'Accounting/Reporting',
    'depends': ['account', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
