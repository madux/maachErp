# -*- coding: utf-8 -*-
{
    'name': "EHA Helpdesk Extension",

    'summary': """
        EHA Extension to Odoo 12 Helpdesk""",

    'description': """
        EHA Extension to Odoo 12 Helpdesk with extra features such as realtime dashboard, patient transitioning workflow
    """,

    'author': "EHA Clinics",
    'website': "https://www.eha.ng",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Helpdesk',
    'version': '0.1',
    'sequence': 4,
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'helpdesk', 'oehealth_extension'], #,'eha_connector'],
    # new method of declaring assets in v16
    'assets': {
        'website.assets_frontend': [
            '/helpdesk_extension/static/src/js/eha_helpdesk_dashboard.js',
            '/helpdesk_extension/static/src/css/eha_helpdesk_dashboard.scss',
            'https://use.fontawesome.com/releases/v5.0.13/css/all.css'
        ]
    },

    # always loaded
    'data': [
        'security/helpdesk_security.xml',
        'views/helpdesk_ticket.xml',
        'data/helpdesk_team.xml',
        'data/helpdesk_ticket_type.xml',
        'data/helpdesk_channel.xml',
        'views/helpdesk_tickets_dashboard.xml',
        'views/hr_department_inherit.xml',
        'views/helpdesk_team_views.xml',
        'views/helpdesk_channel.xml',
        'oeha_extension/views/oeh_eval_helpdesk_wizard.xml',
        'oeha_extension/views/oeha_appointment_view.xml',
        'oeha_extension/views/oeh_pharmacy_views.xml',
        'oeha_extension/views/oeha_medical_lab_view.xml',
        'oeha_extension/views/oeha_medical_prescription_view.xml',
        'oeha_extension/views/oeha_medical_views.xml',
        'security/ir.model.access.csv',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'Application': True,
    'sequence': 3
}