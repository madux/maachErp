# -*- coding: utf-8 -*-
{
    'name': "EHA Website Sale Extension",

    'summary': """
        EHA Clinics website.""",

    'description': """
        EHA website Sale has features such as for online purchase of Direct Care Membership Subscription,
        Online payment etc
    """,

    'author': "EHA Clinic Ltd",
    'website': "https://www.eha.ng",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'website',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'portal', 'website_sale', 'website_sale_stock', 'eha_website', 'phone_validation', 'oehealth', 'sale_subscription_extension'],# 'eha_connector'],
    # always loaded
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/templates.xml',
        'views/booking_templates.xml',
        'views/healthTopics.xml',
        'views/product_template.xml',
        'views/view_sale_order.xml',
        'data/data_plan_features.xml',
        # 'views/pharmacy_changes.xml',
        # 'views/prescription.xml',
        'wizard/view_wizard_message.xml',
        'views/res_config_settings_view.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'assets': {'website.assets_frontend': [
        '/eha_website_sale/static/js/membership_subscription.js',
        
    ]},
    'application': True,
    'sequence': 3,
}
