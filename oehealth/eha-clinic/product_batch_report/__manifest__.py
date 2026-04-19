# -*- coding: utf-8 -*-

{
    'name': 'Lot and Serial Number Expiry Report',
    'version': '13.0.1.0.0',
    'summary': 'Generates a detailed Lot and Serial Number Expiry based on their expiry details.',
    'description': """ This module helps you to print a report about tracking products (lot/serial) based on their expiry date. You can filter 		your report based on different criteria.""",
    'category': 'Warehouse',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'depends': ['base', 'stock'],
    'website': 'https://www.cybrosys.com',
    'data': [
        'reports/product_batch_report.xml',
        'reports/product_batch_template.xml',
        'wizard/wizard_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'price': 4.99,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    'application': False,
}
