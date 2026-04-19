# -*- coding: utf-8 -*-
{
    'name': "Slack Service",

    'summary': """
        Slack API Service""",

    'description': """
        Slack API Service
    """,

    'author': "EHA Clinics Ltd.", # Written by Olalekan Babawale
    'website': "https://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/config_param.xml',
    ],
}
