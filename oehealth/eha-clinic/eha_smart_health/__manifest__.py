# -*- coding: utf-8 -*-
{
    'name': "Smart Health Card Implementation",

    'summary': """
       Smart Health Card Implementation""",

    'description': """
        Long description of module's purpose
    """,

    'author': "EHA Clinics",
    'website': "http://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base', 'oehealth'],

    'data': [
        'security/access_groups.xml',
        'security/ir.model.access.csv',
        'views/provider_view.xml',
    ],
}
