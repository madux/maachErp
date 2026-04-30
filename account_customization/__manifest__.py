{
    'name': 'Account Customization Apps',
    'version': '16.0.1',
    'author': "Maduka Sopulu",
    'category': 'ERP',
    'summary': 'ODOO Base Extension to customize base modules',
    'depends': ['account'],
    'description': "ODOO Base Extension to customize base modules ",
    "data": [
        # 'security/ir.model.access.csv',
        'views/account_payment.xml',
        'views/account_move.xml',
        'views/account_journal.xml',
        'data/account_tax.xml',
        'data/account_charts.xml',
        'data/account_journal.xml',
        'data/ir_property.xml',
    ],
    # 'assets': {'web.assets_backend': [
    #     '/eha_website_sale/static/js/membership_subscription.js',
    # ]},
}
