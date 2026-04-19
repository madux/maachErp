{
    'name': 'Odoo Salesman API *',
    'version': '1.0',
    'category': 'Sales',
    'sequence': 5,
    'summary': 'API for creating and retrieving different odoo business operations',
    'description': 'This module provides an API for creating and retrieving sales orders, payment, etc',
    'depends': ['base', 'sale_management', 'stock'],
    "data": [
        'views/res_user.xml',
        'views/res_partner.xml',
        'views/sale_order.xml',
        'views/stock.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}
