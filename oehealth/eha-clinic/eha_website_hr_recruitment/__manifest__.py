# -*- coding: utf-8 -*-
{
    'name': "EHA HR Recruitment",

    'summary': """
        Extend the default hr recruitment module from Odoo with EHA specific requirements""",

    'description': """
        Extend the default hr recruitment module from Odoo with EHA specific requirements
    """,

    'author': "EHA Clinics Ltd.",
    'website': "http://www.eha.ng",
    'license': 'LGPL-3',
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
        'hr_recruitment',
        'website_hr_recruitment',
    ],

    'data': [
        'views/hr_job_views.xml',
        'views/hr_applicant_view.xml',
        'views/preloader.xml',
        'views/templates.xml',
        'data/config_data.xml',
    ],
}
