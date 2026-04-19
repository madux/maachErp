# -*- coding: utf-8 -*-
{
    'name': "EHA Telehealth",
    'summary': """
        Telehealth Implementation.""",
    'description': """
        Telehealth Implementation.
    """,
    'author': "EHA Clinics Ltd.",
    'website': "https://www.eha.ng",
    'category': 'Website',
    'version': '16.0.1',
    'depends': [
        'base_setup',
        'website',
        'website_sale',
        'payment',
        'google_calendar',
        'odoo_appointment_booking',
        'eha_website',
        'eha_website_sale',
        'eha_insurance',
        'eha_service',
    ],
    'license': 'LGPL-3',
    'assets': {'web.assets_frontend': [
        'eha_telehealth/static/src/js/book_service.js',
        'eha_telehealth/static/src/js/telehealth_booking.js',
        'eha_telehealth/static/src/js/prescription_booking.js',
        'eha_telehealth/static/src/css/main.css',
    ]},
    'data': [
        'data/email_data.xml',
        'views/assets.xml',
        'views/templates.xml',
        'views/book_service_template.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_view.xml',
        'views/calendar_event_view.xml',
        # 'views/website_templates.xml',
    ],
    'qweb': ['/static/xml/modals.xml'],
}
