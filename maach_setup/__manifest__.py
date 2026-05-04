# -*- coding: utf-8 -*-
{
    'name': 'MAACH ERP SETUP',
    'version': '17.0.1.0.0',
    'category': 'CRM',
    'summary': 'MAACH ERP SETUP IS USED TO CUSTOMIZE APPLICATIONS READILY AVAILABLE FOR EMPLOYEES',
    'description': """
        MAACH ERP SETUP IS USED TO CUSTOMIZE APPLICATIONS READILY AVAILABLE FOR EMPLOYEES
    """,
    'author': 'Custom',
    'depends': ['company_memo', 'account_customization', 'crm_portal', 'eedc_role_manager', 'odoo_apis', 'pms_portal', 'portal_request', 'report_portal'],
    'data': [
        # 'views/menu_views.xml',
        # 'data/data.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
