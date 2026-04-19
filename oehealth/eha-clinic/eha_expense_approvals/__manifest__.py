# -*- coding: utf-8 -*-
{
    'name': "EHA Approvals Expense Ext Module",

    'summary': """
        EHA Approvals Expense Extension module.""",

    'description': """
        This module is designed to handle the creation of expenses from approvals
    """,

    'author': "EHA Clinics Ltd",
    'website': "https://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'approvals',
        'hr_expense',
    ],

    'data': [
        'views/approval_request_views.xml',
    ],
}