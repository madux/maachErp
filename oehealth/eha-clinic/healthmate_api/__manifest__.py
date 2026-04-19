# -*- coding: utf-8 -*-
{
    'name': "healthmate_api",

    'summary': """
        RESTFul Api for EHA HealthMate Mobile App""",

    'description': """
        RESTFul APIs developed using odoo RPC for usage by the EHA HealthMate App
    """,

    'author': "EHA Clinics Ltd",
    'website': "https://www.eha.ng",

    'category': 'API',
    'version': '0.1',
    'license': 'LGPL-3',

    'depends': ['base', 'oehealth_extension', "eha_auth", "eha_website_hr_recruitment", "eha_base_extension"], #'eha_connector',

    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'data/ir_config_param.xml',
        'views/product_pricelist.xml'
    ],
}