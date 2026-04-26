# -*- coding: utf-8 -*-
{
    'name': 'CRM Portal',
    'version': '17.0.1.0.0',
    'category': 'CRM',
    'summary': 'Custom CRM Portal with Dashboard, Leads, Opportunities and Sales',
    'description': """
        CRM Portal Module for Odoo 17
        - Dashboard with charts and KPIs
        - Leads and Opportunities management
        - Sales quotation creation and confirmation
        - Pipeline view
    """,
    'author': 'Custom',
    'depends': ['crm', 'sale_crm', 'sale_management', 'account', 'web'],
    'data': [
        'views/menu_views.xml',
        'data/data.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
