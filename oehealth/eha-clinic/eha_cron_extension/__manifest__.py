# -*- coding: utf-8 -*-
{
    'name': "CRON Extension",

    'summary': """
        Extension for ir.cron model""",

    'description': """
        Extension for ir.cron model. This module adds features like description of what a cron does to the CRON view.
    """,

    'author': "EHA Clinics",
    'website': "http://www.eha.ng",

    'category': 'Base',
    'version': '0.1',

    'depends': ['base'],

    'data': [
        'views/ir_cron_views.xml',
    ],
}
