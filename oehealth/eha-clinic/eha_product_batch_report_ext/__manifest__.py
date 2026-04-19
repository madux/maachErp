# -*- coding: utf-8 -*-
{
    'name': " EHA Clinic's Lot and Serial Number Expiry Report Estension",

    'summary': """
        Modifications to the Expiry Report""",

    'description': """
        
    """,

    'author': "Steve Olise",
    'website': "https://www.eha.ng",
    'license': 'LGPL-3',
    # Categories can be used to filter modules in modules listing
    'category': 'Warehouse',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product_batch_report', 'report_xlsx'],

    # always loaded
    'data': [
        'reports/product_batch_template.xml',
        'reports/reports.xml',
        'wizard/wizard_view.xml',
        'security/ir.model.access.csv',

    ],
}
