##############################################################################
#    Copyright (C) 2018 oeHealth. All Rights Reserved
#    EHA Clinic Extensions to Accounting Module
{
    'name': 'EHA Clinc Employee Extension',
    'version': '1.1',
    'author': "Ehealth Africa / Braincrew Apps(Migrated to Odoo 12)",
    'category': 'Generic Modules/Medical',
    'summary': 'Ehealth Africa extensions to Odoo 12 Employee Module',
    'depends': ['base', 'hr'],
    'description': "EHA Clinic extensions to the Odoo 12 Employee Module",
    "website": "https://www.eha.ng",
    'license': 'LGPL-3',
    "data": [
        'security/ir.model.access.csv',
        'views/hr_employee.xml',
        'sequence/sequence.xml',
    ],
}
