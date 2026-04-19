# -*- coding: utf-8 -*-
{
    'name': "EHA Product Restriction & Creation Module",

    'summary': """
        EHA Product restriction & creation module.""",

    'description': """
        This module is designed to handle the product creation & update feature
    """,

    'author': "EHA Clinics Ltd",
    'website': "https://www.eha.ng",
    'license': 'LGPL-3',
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
        'purchase',
        'stock',
        'mrp',
        'sale',
        'hr_expense',
        'material_request',
        # 'eha_website_sale', MIGRATIONTODO: UNCOMMENT AFTER eha_website_sale is install, also add the security rights after sale_subscription is done, ensure it exists
        #sale_subscription.access_product_template_sale_subscription_manager,product.template.sale.subscription.manager,product.model_product_template,sale_subscription_extension.group_sale_subscription_manager,1,0,0,0
#sale_subscription.access_product_product_sale_subscription_manager,product.product.sale.subscription.manager,product.model_product_product,sale_subscription_extension.group_sale_subscription_manager,1,0,0,0

        'point_of_sale',
        'sale_subscription',
    ],

    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'wizard/product_approval_rejection_reason.xml',
        'views/views.xml',
        'views/product_template_views.xml',
    ],
}