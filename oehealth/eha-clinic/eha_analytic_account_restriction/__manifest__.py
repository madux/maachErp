# -*- coding: utf-8 -*-
{
    'name': "EHA Analytic Account Module",

    'summary': """
        EHA Product Analytic Account module.""",

    'description': """
        This module is designed to handle the Analytic Account and Analytic Tag creation & update feature
    """,
    'license': 'LGPL-3',

    'author': "EHA Clinic Ltd",
    'website': "https://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
        'analytic',
        'stock',
        'mrp',
        'sales_team',
        'hr_expense',
        'point_of_sale',
    ],

    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
    ],
}