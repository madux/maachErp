# -*- coding: utf-8 -*-
{
    'name': "My DHL Shipping",
    'description': "Send your shippings through My DHL Account and track them online",
    'author': "Ohia George",
    'category': 'Warehouse',
    'version': '1.0',
    'license': 'LGPL-3',
    'depends': ['delivery', 'delivery_dhl', 'mail'],
    'data': [
        'views/delivery_mydhl_view.xml',
        'data/delivery_mydhl_data.xml',
        # 'views/res_config_settings_views.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
}
