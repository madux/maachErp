# -*- coding: utf-8 -*-
{
    'name': "eha maintenance",
    'summary': """Extension to Maintenance Module""",
    'description': """Add extra features to Maintenance Module""",
    'author': "Maduka Sopulu",
    'website': "http://www.eha.ng",
    'category': 'Uncategorized',
    'version': '0.1',
    'data': [
        'views/maintenance_view.xml',
        'data/migration.xml',
    ],
    'depends': ['maintenance', 'eha_multi_branch'],
    'active' : True,
    'auto-install':'False',
    'installable': True,
}