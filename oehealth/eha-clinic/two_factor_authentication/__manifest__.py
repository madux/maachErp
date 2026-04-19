# -*- coding: utf-8 -*-


{
    'name': 'Two Factor Authentication',
    'category': 'system',
    'version': '1.0',
    'author': 'Alpesh Valaki',
    'website': 'sorrysemicolon.com',
    'summary': "Provide extra layer of security using Google Time Based OTP (TOTP)",
    'license': 'OPL-1',
    'description':
        """
Provide extra layer of security using Google Time Based OTP (TOTP). Two Step Authentication

- This module required external_dependencies: python library 'qrcode' installed
========================

        """,
    'depends': ['web', 'mail', 'auth_oauth'],
    'auto_install': False,
    'data': [
            'views/res_users_view_inherit.xml',
            'views/template.xml',
            'data/email_template.xml',
            ],
    'external_dependencies': {
        'python' : ['qrcode'],
    },
    "images":['static/description/Banner.png'],
	    

    'currency': 'EUR',
    'price': 30.00,



}
