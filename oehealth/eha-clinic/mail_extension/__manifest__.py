##############################################################################
#    Copyright (C) 2018 oeHealth. All Rights Reserved
#    EHA Clinic Extensions to oeHealth, Hospital Management Solutions


{
    'name': 'Mail Template Extension',
    'version': '1.5',
    'author': "Ehealth Africa / Maduka Chris Sopulu",
    'category': '/Mail',
    'summary': 'Ehealth Africa extensions to Odoo 12 Mail Template',
    'depends': ['base', 'mail', 'mass_mailing'],
    'license': 'AGPL-3',
    
    'description': "EHA Clinic extensions to the Mail Template Module",
    "website": "https://eha.ng",
    "data": [
            'security/ir.model.access.csv',
            'data/ir_config_params.xml',
            'data/cron.xml',
            'views/mass_mailing_inherit.xml',
        ],
    
    'css': [],
    'js': [

    ],
    'qweb': [

    ],
    "active": False,
    'application': True,
    "sequence": 3
}
