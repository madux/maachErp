# -*- coding: utf-8 -*-
{
    'name': "EHA Clinics Website",

    'summary': """
        EHA Clinics website.""",

    'description': """
        EHA Clinics website. Has features such as for online purchase of Direct Care Membership Subscription,
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
    'depends': [
        'base',
        'website_sale',
        'phone_validation',
        'mass_mailing', 
        'website_hr_recruitment',
        # 'website_helpdesk_form',
        'sale_subscription',
        # 'sale_coupon',
        'oehealth',
        'mail',
        'helpdesk_extension'
        
    ],
    'license': 'LGPL-3',
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/gazelle_templates.xml',
        'views/booking_templates.xml',
        'views/website_templates.xml',
        'views/careers_templates.xml',
        'views/campaigns_templates.xml',
        'views/res_partner.xml',
        'views/webclient_templates.xml',
        'mass_mailing_extension/views/templates.xml',
        'mass_mailing_extension/data/cron.xml',
        'data/data.xml',
        'data/config_data.xml',
        'views/assets.xml',
        'views/hr_recruitment_inherited_view.xml',
        'data/menu.xml',
        'data/ir_config_param.xml',
        'covid19/views/templates.xml',
        'covid19/views/buytest-start.xml',
        'covid19/views/buytest-step2.xml',
        'covid19/views/buytest-step1.xml',
        'covid19/views/buytest-step1-summary.xml',
        'covid19/views/buytest-step3.xml',
        'covid19/views/buytest-confirmation.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'application': True,
    'sequence': 2,
    'assets': {'website.assets_frontend': [
        '/eha_website/static/src/img/favicon.ico',
        '/eha_website/static/src/lib/build/css/jquery.timepicker.1.3.5.min.css',
        'https://use.fontawesome.com/releases/v5.0.13/css/all.css',
        '/eha_website/static/src/fontello/css/ehaclinics.css',
        '/eha_website/static/src/scss/eha_global.scss',
        '/eha_website/static/src/scss/eha_website2.scss',
        '/eha_website/static/src/lib/build/js/jquery.timepicker.1.3.5.min.js',
        '/eha_website/static/src/js/utils.js',
        '/eha_website/static/src/js/script.js',
        '/eha_website/static/src/js/covid19/covid19_start_page.js',
        '/eha_website/static/src/js/covid19/covid19_test_patients.js',
        '/eha_website/static/src/js/covid19/booking.js',
        '/eha_website/static/src/js/covid_booking.js',
        '/eha_website/static/src/js/incident_management.js',
        '/eha_website/static/src/js/json-rpc.js',
        '/eha_website/static/src/js/recruitment_form_validation.js',
    ]}
}