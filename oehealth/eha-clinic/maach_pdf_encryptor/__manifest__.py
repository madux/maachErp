##############################################################################
#    Copyright (C) 2018 oeHealth. All Rights Reserved
#    EHA Clinic Extensions to oeHealth, Hospital Management Solutions


{
    'name': 'Maach PDF Report Encryptor',
    'version': '1.5',
    'author': "Maduka Chris Sopulu",
    'category': '/Mail',
    'summary': 'Maach PDF Report encryptor',
    'depends': ['base'],
    'license': 'AGPL-3',
    
    'description': "Encrpyt pdf reports based on password configuration",
    "data": [
            'views/ir_actions_report.xml',
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
