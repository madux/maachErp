# -*- coding: utf-8 -*-
{
    'name': "EHA Purchase Agreements Extension Module",

    'summary': """
        EHA Purchase Agreements Extension module.""",

    'description': """
        This module is designed allows you to manage your Purchase Agreements
    """,

    'author': "EHA Clinics Ltd",
    'website': "https://www.eha.ng",
    'license': 'LGPL-3',
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
        'purchase',
        'purchase_requisition',
    ],

    'data': [
        'views/purchase_requisition_views.xml',
        'views/purchase_views.xml',
    ],
}