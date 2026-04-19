##############################################################################
#    Copyright (C) 2021 oeHealth. All Rights Reserved
#    EHA Clinic Extensions to Sms module


{
    'name': 'SMS Extension',
    'version': '1.0',
    'author': "EHA Clinics",
    'category': 'sms',
    'license': 'AGPL-3',
    'summary': 'EHA Clinics Extension to Odoo 12 Sms',
    'description': "EHA Clinics Extension to Odoo 12 Sms",
    "website": "https://www.eha.ng",
    'depends': ['base', 'sms'],
    "data": [
        'security/ir.model.access.csv',
        'views/sms_log_views.xml',
        'data/data.xml'
    ],
}
