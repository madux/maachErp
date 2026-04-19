# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Maach Subscription License",
    'version': '2.0',
    'category': '',
    "sequence":-1,
    'summary': 'License application to manage subscriptions',
    'depends': ['base','web', 'website', 'website_mass_mailing'],#, 'home_menu_overlay'],
    'author': 'Chris Maduka [MAACH SOFTWARE]',
    'data': [ 
        # 'data/account_view.xml',
        'views/subscription_model_view.xml',
        'views/subscription_request_view.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron.xml',
        # 'security/security.xml',
        'security/ir.model.access.csv',
        # 'views/portal_templates.xml',
        'static/template/landing_page_templates.xml',
        'static/template/expired_templates.xml',
        'static/template/register_templates.xml',
        'static/template/login.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'license/static/src/css/portal.css',
            'license/static/src/js/portal.js',
        ],
        'web.assets_backend': [
            'https://cdn.jsdelivr.net/npm/chart.js',
            'license/static/src/css/style.css',
            # JS
            # 'quality_managment/static/src/components/dashboard_chart.js',
            # XML templates
            # 'quality_managment/static/src/components/dashboard_chart.xml',
        ],
    },

    'installable': True,
    'auto_install': True,
    'application': False,
    'license': 'LGPL-3',
}
