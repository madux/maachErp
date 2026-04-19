# -*- coding: utf-8 -*-
{
    'name': "EHA Sale Order Lot Selection & Barcode Scanning",

    'summary': """
        EHA Sale Order Lot Selection & Barcode Scanning.""",

    'description': """
        This module is designed to handle the scanning of lots/serial numbers into sale orders and using that to create the delivery
    """,

    'author': "EHA Clinics Ltd",
    'website': "https://www.eha.ng",
    'license': 'LGPL-3',
    "category": "Sales Management",
    'version': '0.2',

    'depends': ['sale_stock'],

    'data': [
        'views/sale_view.xml',
    ],
}