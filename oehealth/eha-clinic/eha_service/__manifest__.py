# -*- coding: utf-8 -*-
{
    'name': "Clinical Services",

    'summary': """
        Clinical Services""",

    'description': """
        This module manages all the services that we provide at the clinic
    """,

    'author': "EHA Clinics Ltd.",
    'website': "http://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
        'product',
        'sale',
        'sale_management',
    ],

    'data': [
        'security/access_groups.xml',
        'security/ir.model.access.csv',
        'views/service_views.xml',
        # 'views/templates.xml',
    ],
    'demo': [
        # 'demo/demo.xml',
    ],
}
