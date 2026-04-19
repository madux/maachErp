# -*- coding: utf-8 -*-
{
    'name': "EHA UoM Module",

    'summary': """
        EHA Product UoM module.""",

    'description': """
        This module is designed to handle the UoM creation & update feature
    """,

    'author': "EHA Clinic Ltd",
    'website': "https://www.eha.ng",
    'license': 'LGPL-3',
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
        'purchase',
        # 'stock',
        # 'mrp',
        # 'sales_team',
        'sale',
        # 'hr_expense',
        # 'point_of_sale',
    ],

    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
    ],
}