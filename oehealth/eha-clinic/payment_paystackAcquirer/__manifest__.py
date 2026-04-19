# -*- coding: utf-8 -*-

{
    'name': 'Paystack Payment Acquirer',
    'category': 'eCommerce',
    'summary': 'Payment Acquirer:Paystack Implementation',
    'version': '1',
    'license': 'OPL-1',
    'author': 'Ewetoye, Ibrahim',
    'website': 'https://EwetoyeIbrahim.github.io',
    'description': """Paystack Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_paystack_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_paystackAcquirer/static/src/js/payment_form.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'price': '150.00',
    'currency': 'USD',
}
