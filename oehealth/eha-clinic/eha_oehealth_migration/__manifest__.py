# -*- coding: utf-8 -*-
{
    'name': "EHA oEHealth Migration",

    'summary': """
        Migration module for oehealth to EMR""",

    'description': """
        Migration module for oehealth to EMR
    """,

    'author': "EHA Clinics Ltd.",
    'website': "http://www.eha.ng",

    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'eha_emr_connector',
        'oehealth',
        'oehealth_extension'
    ],

    'data': [
        'security/eha_oehealth_migration_groups.xml',
        'data/eha_oehealth_migration_data.xml',
        'views/patient_views.xml',
        'views/evaluation_views.xml',
        'views/prescription_views.xml',
    ],
}
