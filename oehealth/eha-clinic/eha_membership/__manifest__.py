# -*- coding: utf-8 -*-
{
    'name': "EHA Membership Module",

    'summary': """
        EHA Membership Module.""",

    'description': """
        This module is designed to handle EHA's Membership features
    """,

    'author': "EHA Clinics Ltd",
    'website': "https://www.eha.ng",
    'license': 'LGPL-3',
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
        'product',
        'contacts',
        'sale',
        'sale_subscription',
        'sale_subscription_extension'
    ],

    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/membership_data.xml',
        'views/main_menuitems.xml',
        'views/membership_views.xml',
        'views/membership_plan_views.xml',
        'views/membership_category_view.xml',
        'views/res_partner_views.xml',
        'views/membership_beneficiaries_views.xml',
        'views/beneficiaries_dependents_views.xml',
    ],
}
