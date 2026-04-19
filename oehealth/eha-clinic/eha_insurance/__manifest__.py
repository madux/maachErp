# -*- coding: utf-8 -*-
{
    'name': "Eha Medical insurance",
    'summary': """Medical insurance Module""",
    'description': """Medical insurance""",
    'author': "Maduka Sopulu",
    'website': "http://www.eha.ng",
    'category': 'Uncategorized',
    'version': '0.1',
    'data': [
        'security/ir.model.access.csv',
        'views/eha_medical_insurance_view.xml',
        'views/res_partner_views.xml',
        'data/migration.xml',
    ],
    'license': 'LGPL-3',
    'depends': ['base'],
    'active' : True,
    'auto-install': True,
    'installable': True,
}