# -*- coding: utf-8 -*-
{
    'name': "EHA EMR Connector",

    'summary': """
        This module provides the handshake necessary with the EMR application""",

    'description': """
        This module provides the handshake necessary with the EMR application. The module provides among other things, the authentication with EMR and a
        standardization of calls to the endpoints exposed by the EMR
    """,

    'author': "EHA Clinics Ltd.",
    'website': "http://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'LGPL-3',

    'depends': ['base', 'base_setup', 'oehealth'],

    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/error_log_views.xml',
    ],
}
