# -*- coding: utf-8 -*-

# I had to change technical name because:
# 1. https://gitlab.openminds.be/mirror/odoo/commit/5439e72a4ebd7716b813c7ec24fd59058151568f#075e6a8a08e3d13cd3291eca8f376670dad599ca_199_248
# 2. There is already a module with name payment_paystack

{
    'name': 'Paystack Payment Acquirer',
    'category': 'eCommerce',
    'summary': 'Payment Acquirer:Paystack Implementation',
    'version': '2.0',
    'license': 'AGPL-3',
    'author': 'Ewetoye Ibrahim',
    'website': 'https://EwetoyeIbrahim.github.io',
    'description': """Paystack Payment Acquirer""",
    'depends': ['payment', 'website'],
    # 'data': [
    #     'views/payment_views.xml',
    #     'views/payment_paystack_templates.xml',
    #     'data/payment_acquirer_data.xml',
    # ],
    'images': ['static/description/icon.png'],
    'installable': True,
    # 'post_init_hook': 'create_missing_journal_for_acquirers',
    'price': '211.00',
    'currency': 'USD',
}
