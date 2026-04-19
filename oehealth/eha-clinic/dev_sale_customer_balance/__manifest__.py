# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

{
    'name': 'Customer Balance in Sale Order',
    'version': '13.0.1.0',
    'sequence': 1,
    'license': 'LGPL-3',
    'category': 'Sales',
    'description':
        """

        This Module add below functionality into odoo

        1.Shows customer's balance on sale order\n

odoo customer balance 
odoo balance sale order 
odoo sale balance sale order
odoo app to show Customer Balance in Sale Order, sale customer balance, customer balance, balance sale order, customer balance on sale, sale partner balance, sale client balance, sale customer credit balance, customer balance


    """,
    'summary': 'odoo app to show Customer Balance in Sale Order, sale customer balance, customer balance, balance sale order, customer balance on sale, sale partner balance, sale client balance, sale customer credit balance, customer balance',
    'depends': ['sale_management'],
    'data': [
            'views/sale_view.xml',
        ],
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    
    # author and support Details =============#
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'website': 'http://www.devintellecs.com',    
    'maintainer': 'DevIntelle Consulting Service Pvt.Ltd', 
    'support': 'devintelle@gmail.com',
    'price':8.0,
    'currency':'EUR',
    #'live_test_url':'https://youtu.be/A5kEBboAh_k',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
