# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "CareOne Health Application",
    'version': '2.0',
    'category': '',
    "sequence":-1,
    'summary': 'Application developed for careone integration with EMR',
    'depends': ['base', 'mail', 'product', 'account','account_payment', 'stock', 
                'purchase', 'sale', 'sale_management', 'ik_multi_branch',
                'odoo_apis', 
                'calendar', 'home_menu_overlay_module'],
    'author': 'Chris Maduka [MAACH SOFTWARE]',
    'data': [ 
        # 'data/account_view.xml',
        'views/res_patient_pharmacy_history_views.xml',
        'views/res_partner_patient_views.xml',
        'views/patient_view.xml',
        'views/patient_evaluation_form_view.xml',
        'views/patient_admission_view.xml',
        'views/patient_evaluation.xml',
        'views/pharmacy_config_stage_views.xml',
        'views/pharmacy_stock_batch_views.xml',
        'views/product_product_views.xml',
        'data/ir_sequence_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml'
    ],
    
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
