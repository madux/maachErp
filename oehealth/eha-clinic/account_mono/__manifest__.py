# -*- coding: utf-8 -*-
{
    'name': "Account Mono Sync",
    'summary': """Mono Sync Data""",
    'description': """
        Long description of module's purpose
    """,
    'author': "EHA Clinics",
    'website': "http://www.eha.ng",
    'category': 'account',
    'version': '16.0.1',
    'license': 'LGPL-3',
    'depends': ['base', 'account'], #, 'account_online_sync'],
    'data': [
        'data/data.xml',
        # 'views/assets.xml',
        'views/res_company.xml',
    ],
    'assets': {
        'web.assets_backend': [
        'https://connect.withmono.com/connect.js',
        'account_mono/static/src/js/mono_widget.js'
                    ]},
}
