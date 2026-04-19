# -*- coding: utf-8 -*-
{
    'name': "EHA Payroll Accounting Ext Module",

    'summary': """
        EHA Payroll Accounting Extension module.""",

    'description': """
        This module is designed to handle the Extension of the Payroll Accounting
    """,

    'author': "EHA Clinics Ltd",
    'license': 'LGPL-3',
    'website': "https://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
        'hr_payroll_account',
    ],

    'data': [
        'views/hr_payroll_account_views.xml',
    ],
}