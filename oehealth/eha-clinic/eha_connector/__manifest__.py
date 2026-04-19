# -*- coding: utf-8 -*-
{
    'name': "eha_connector",

    'summary': """
        connector for moving data to/fro odoo to external services""",

    'description': """
        Consists of RESTFul APIs and schema transformers that transforms odoo models and pushes
        same to aether endpoints
    """,

    'author': "EHA Clinics Ltd",
    'website': "https://www.eha.ng",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'API',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','eha_auth', 'oehealth'], #, 'eha_cron_extension', 'oehealth_extension', 'oehealth', 'eha_auth'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'data/ir_config_param.xml',
        'views/aether_sync_log.xml',
        'views/ncdc_push_log.xml',
        'views/panabios_log_view.xml',
        'views/product_category_view.xml'
    ],
    'sequence': 2,
    'installable': True,
    'license': 'LGPL-3',
}
