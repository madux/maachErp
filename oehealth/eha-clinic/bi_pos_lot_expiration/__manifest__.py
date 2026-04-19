# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


{
    'name': 'POS Lot Expiry Warning - Validation',
    'version': '13.0.0.0',
    'category': 'Point of Sale',
    'summary': 'POS lot warning pos lot expiry warning pos serial expiry warning pos lot expiry validation point of sale lot warning point of sale lot expiry warning point of sale serial expiry warning point of sale lot expiry validation point of sales lot expiry warning',
    'description': """
        This odoo app show warning to point of sale user while selling product with expired lot or serial number and also warn user if lot/serial number not exist for selected product, User also have option to restrict creating new lot/serial number for product if expired or not exist. 
    """,
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.in',
    "price": 4,
    "currency": 'EUR',
    'depends': ['point_of_sale'],
    'license': 'LGPL-3',
    'data': [
        'views/point_of_sale.xml',
        'views/pos_assets_common.xml',
    ],
    'qweb': [
        'static/src/xml/pos.xml',
    ],
    'assets': {'point_of_sale.assets': [
        '/bi_pos_lot_expiration/static/src/js/models.js',
        '/bi_pos_lot_expiration/static/src/js/popups.js',
        '/bi_pos_lot_expiration/static/src/js/screen.js',
	]},
    'installable': True,
    'auto_install': False,
    'live_test_url': 'https://youtu.be/1AlZSSUMTeE',
    "images": ['static/description/Banner.png'],
}
