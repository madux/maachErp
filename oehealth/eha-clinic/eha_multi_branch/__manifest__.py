# -*- coding: utf-8 -*-
{
    'name': "eha_multi_branch",

    'summary': """EHA Clinic Multi Branch""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Eha Clinics Ltd",
    'website': "http://www.eha.ng",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base', 
        'helpdesk', 
        'website_payment',
        # 'helpdesk_extension', 
        'sale', 
        'product', 
        'stock', 
        'oehealth', 
        # 'oehealth_extension',
        'account',
        'account_reports',
        # 'account_analytic_default',
        'purchase',
        # 'account_voucher', 
        # 'sale_subscription_extension',
        'inventory_extension',
        'sale_stock', 
        'eha_product_restriction', 

    ],
    'license': 'LGPL-3',
    'data': [
        'branch/data/branch.xml',
        'branch/security/ir.model.access.csv',
        'branch/views/eha_branch_view.xml',
        'branch/views/base_view.xml',
        'stock/views/stock_view.xml',
        'stock/views/delivery_order_report.xml',
        # 'oehealth/views/oehealth_view.xml',
        'oehealth/security/ir.rule.xml',
        'purchase/views/purchase_view.xml',
        'sales/views/sale_view.xml',
        'sales/views/account_payment_views.xml',
        # 'auth/views/assets.xml',
        'auth/data/ir_config_parameter_data.xml',
        # 'account/views/search_template_view.xml',
        'account/views/account_view.xml',
        'account/data/data.xml',
        # 'account/data/account_financial_report_data.xml',
        'account/data/data.xml',
        'account/data/mail_template_data.xml',
        'account/views/search_template_view.xml',
        'helpdesk/security/helpdesk_security.xml',
        'helpdesk/views/helpdesk_view.xml',
        # 'covid_consumables/oeha_covid_consumables_views.xml',
        'pricelist/product_pricelist_views.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #     '/eha_multi_branch/static/src/js/account_reports.js',
    # ]},
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}