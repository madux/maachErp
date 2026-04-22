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
    ],
    # 'assets': {'web.assets_backend': [
    #     '/eha_website_sale/static/js/membership_subscription.js',
        
    # ]},
}
