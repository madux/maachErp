{
    'name': 'Odoo Online Appointment booking',
    'version': '13.0.0',
    'author': 'EHA Clinics Ltd',
    'description':"""Module manages booking of appointments using Odoo calendar against simply book""",
    'depends': [
        'calendar', 
        'oehealth', 
        'eha_multi_branch',
        'eha_website',
        'oehealth_extension',
    ],
    'license': 'LGPL-3',
    'data': [
        'sequence/sequence.xml',
        'security/ir.model.access.csv',
        'views/calendar_event_views.xml',
        'views/assets.xml',
        'views/appointment_booking.xml',
        'views/eha_branch_views.xml',
        'data/mail_template.xml',
        'data/cron.xml',
        'views/oehealth_extension_view.xml',
        'views/covid_booking_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_frontend': ['odoo_appointment_booking/static/src/js/appointment_booking.js']
    },
    'sequence': 3,
    'installable': True,
    'application': True,
    'auto_install': False,
}