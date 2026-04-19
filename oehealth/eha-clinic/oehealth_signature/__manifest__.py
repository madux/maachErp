# -*- coding: utf-8 -*-
{
    'name': "EHA Sign Extension",

    'summary': """
        EHA Signature module modification""",

    'description': """
        Modifying Signature module to add feature in sign functionality
    """,

    'author': "EHA Clinics",
    'website': "https://www.eha.ng",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sign',
    'version': '0.1',
    'sequence': 4,

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'sign'],

    # always loaded
    'data': [
        'security/hr_security.xml',
        'security/ir.rule.xml',
        'views/sign_request_view.xml',
        # 'views/sign_template_share_view.xml',
        'views/sign_template_view.xml',
        'views/assets.xml',
        'views/res_partner_views.xml',
    ],
    # only loaded in demonstration mode

    'Application': False,
    'sequence': 3
}
