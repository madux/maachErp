# -*- coding: utf-8 -*-
{
    'name': " EHA Clinic's Lot and Serial Number Report Extension",

    'summary': """
        Modifications to the Lot and Serial Number Report to enhance barcode printing""",

    'description': """
        
    """,

    'author': "EHA Clinics Ltd",
    'website': "https://www.eha.ng",
    'license': 'LGPL-3',
    # Categories can be used to filter modules in modules listing
    'category': 'Warehouse',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock'],

    # always loaded
    'data': [
        'views/stock_views.xml',
        'reports/report_lot_barcode.xml',
        'reports/stock_report_views.xml',
        'reports/picking_templates.xml',
    ],
}
