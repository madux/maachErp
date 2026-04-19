# -*- coding: utf-8 -*-
{
    'name': "Fedex Nigeria Shipping",
    'description': "Send your shippings through Fedex Account and track them online",
    'author': "Ohia George",
    'category': 'Warehouse',
    'version': '1.0',
    'license': 'LGPL-3',
    'depends': ['delivery', 'delivery_fedex', 'mail'],
    'data': [
        'views/delivery_ng_fedex_view.xml',
        'wizard/view_wizard_tracking.xml',
        'data/delivery_ng_fedex_data.xml',
    ],
}
