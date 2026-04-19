##############################################################################
#    Copyright (C) 2022. MAACH MEDIA. All Rights Reserved
#    EHA Clinic Extensions to Inventory Module
{
    'name': 'EHA Clinic Inventory Extension',
    'version': '1.0',
    'author': "Maach Media (Migrated to Odoo 16)",
    'category': 'Generic Modules/Inventory',
    'summary': 'Ehealth Africa extensions to Odoo 16 Inventory',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'helpdesk',
        'product',
        'stock',
        'oehealth',
        # 'oehealth_extension',
        'account',
        # 'account_analytic_default',
        'purchase',
        'product_expiry',
        'point_of_sale',
        # 'account_voucher'
    ],

    'description': "EHA Clinic extensions to the Odoo 12 inventory Module. Consignment Report to generated vendor bill is also integrated on this module",
    "website": "https://www.eha.ng",
    "data": [
        'views/product_template.xml',
        'views/consignment_sales_report.xml',
        'views/stock_views.xml',
        'security/ir.model.access.csv',
        'data/ir_config.xml'
    ],

}
