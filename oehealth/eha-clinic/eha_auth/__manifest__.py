# -*- coding: utf-8 -*-
{
    'name': "EHA Authentication",

    'summary': """
        API authentication""",

    'description': """
        Module implements authentication especially for API's. You can use decorators like @validate_token 
    """,
    'license': 'LGPL-3',

    'author': "EHA Clinics",
    'website': "http://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base'],

    'data': [
        'security/access_groups.xml',
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
    ],
}
