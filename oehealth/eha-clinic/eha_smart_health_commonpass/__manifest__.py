# -*- coding: utf-8 -*-
{
    'name': "Commonpass Implementation",

    'summary': """
       Commonpass Implementation""",

    'description': """
        Long description of module's purpose
    """,

    'author': "EHA Clinics",
    'website': "http://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base', 'oehealth', 'eha_smart_health'], #, 'eha_website'],

    'external_dependencies': {
        "python": [
            'certifi',
            'cffi',
            'charset-normalizer',
            'cryptography',
            'Deprecated',
            'ecdsa',
            'idna',
            'jwcrypto',
            'Pillow',
            'pyasn1',
            'pycparser',
            'python-jose',
            'qrcode',
            'pyotp',
            'requests',
            'rsa',
            'six',
            'urllib3',
        ]
    },

    'data': [
        'security/ir.model.access.csv',
        'data/provider.xml',
        'data/ir_config_param.xml',
        'data/loinc_code.xml',
        'views/lab_test_views.xml',
        'views/loinc_code_views.xml',
        'report/commonpass_test_card.xml',
        'views/website_templates.xml',
    ],
}
