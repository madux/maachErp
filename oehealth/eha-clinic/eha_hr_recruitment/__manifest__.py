# -*- coding: utf-8 -*-
{
    'name': "EHA Recruitment Extension",

    'summary': """
     Extension to Recruitment Module
    """,

    'description': """
        Extension to Recruitment Module
    """,
    'license': 'LGPL-3',

    'author': "EHA Clinics Ltd",
    'website': "https://www.eha.ng/",

    'version': '1.0',
    'depends': ['hr_recruitment'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/move_hr_applicant_views.xml',
    ],
}