# -*- coding: utf-8 -*-
{
    'name': "EHA Website Meta-Keywords",

    'summary': """
       Add meta keywords to EHA Website""",

    'description': """
        Add meta keywords to EHA Website becuase we have exhausted maximum of 10 from odoo website interface.
    """,

    'author': "EHA Clinics Ltd.",
    'website': "http://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': ['base', 'website'],

    'data': [
        'data/website_data.xml',
    ],
}
