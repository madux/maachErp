# -*- coding: utf-8 -*-
{
    'name': "EHA Asana Links Module",

    'summary': """
        EHA Asana Links module.""",

    'description': """
        This module is designed to handle the Asana Links feature
    """,
    'license': 'LGPL-3',

    'author': "EHA Clinics Ltd",
    'website': "https://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
    ],

    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'views/asana_link_views.xml',
    ],
}