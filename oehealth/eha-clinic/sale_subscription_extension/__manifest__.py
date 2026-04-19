##############################################################################
#    Copyright (C) 2019 oeHealth. All Rights Reserved
#    EHA Clinic Extensions to Subscription Module


{
    'name': 'EHA Clinc Subscription Extension',
    'version': '16.0.1',
    'author': "Ehealth Africa",
    'category': 'Generic Modules/Subscription',
    'summary': 'Ehealth Africa extensions to Odoo 13 Subscription',
    'depends': ['base', 'web', 'website','sale_subscription', 'oehealth', 'eha_base_extension', 'eha_website_hr_recruitment'],
 

    'description': "EHA Clinic extensions to the Odoo 13 Subscription Module",
    "website": "https://www.eha.ng",
    'license': 'AGPL-3',
    "data": [
        'security/ir.model.access.csv',
        'security/security_view.xml',
        'views/product_template_views.xml',
        'wizard/import_wizard_view.xml',
        'views/sale_subscription_template_view.xml',
        'views/sale_subscription_view.xml',
        'views/sale_beneficiary_view.xml',
        'views/patient_view.xml',
        # 'views/assets.xml',
        'views/view_partner_inherit.xml',
        'views/website_adding_beneficiary_view.xml',
        'views/website_adding_family_member.xml',
        'views/website_billing_thanks_page_view.xml',
        'views/website_price_calculator_view.xml',
        'views/sale_views.xml',
        'views/subscription_plan_view.xml',
        'data/automated_action.xml',
        'data/mail_template.xml',
        'data/family_membership.xml',
        'data/corporate_template.xml',
        'data/ir_config_parameter.xml',
        'data/subscription_roles.xml',
        'wizard/migrate_beneficiary_view.xml',
    ],
    "images": [],
    "assets": {'web.assets_backend': [
        '/sale_subscription_extension/static/src/lib/jquery.serialize.js',
        '/sale_subscription_extension/static/src/js/membership.js',
        '/sale_subscription_extension/static/src/js/family_members.js',
        '/sale_subscription_extension/static/src/css/style.css'
    ]},
    'qweb': ['static/*.xml'],
}
